from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import javalang
from javalang.tokenizer import LexerError
from javalang.tree import (
    ClassCreator,
    ClassDeclaration,
    MemberReference,
)

from backend.schemas.activity import ActivityDocument, ActivityEdge, ActivityNode, ActivityNodeType
from backend.schemas.uml import (
    Attribute,
    Method,
    Multiplicity,
    Parameter,
    Position,
    Relationship,
    RelationshipType,
    Size,
    UmlClass,
    UmlDocument,
    Visibility,
)

_BOX_WIDTH = 200.0
_BOX_HEIGHT = 140.0
_H_GAP = 60.0
_V_GAP = 60.0
_GRID_COLUMNS = 4

# Java spelling -> the language-neutral vocabulary the rest of the system uses
# (see backend/generator/language_maps/java.py's TYPE_MAP, which maps most of
# these same neutral names straight back to Java on the forward/codegen side).
# Only "boolean" needs translating; every other Java spelling (String, int,
# long, float, double, Integer, Object, List, Map, Set, ...) already matches
# the neutral vocabulary and passes through unchanged rather than being
# guessed.
_SCALAR_NEUTRAL_MAP = {"boolean": "bool"}

# Outer (neutral) container names treated as "many" for multiplicity inference.
_MANY_CONTAINERS = {"List", "Set", "ArrayList", "HashSet"}


@dataclass
class _RelEdge:
    source_id: str
    dest_id: str
    type: RelationshipType
    many: bool


@dataclass
class _AttrRelInfo:
    """Bookkeeping linking an already-built Attribute to a relationship edge;
    never surfaces in the emitted schema objects."""

    target_class: str
    origin: str  # "instantiation" | "param-passthrough" | "annotated-only"
    many: bool


def parse(source: str) -> UmlDocument:
    """Reverse-engineer Java source into a Unified UML JSON document."""
    try:
        tree = javalang.parse.parse(source)
    except (javalang.parser.JavaParserBaseException, LexerError) as exc:
        raise ValueError(f"Invalid Java source: {exc}") from exc

    # Only top-level classes -- interfaces/enums/annotations have no UML
    # equivalent in this schema and are discarded cleanly, and nested classes
    # (declared inside another type's body) are not visited since we only walk
    # tree.types, the compilation unit's direct children.
    class_defs = [t for t in tree.types if isinstance(t, ClassDeclaration)]
    class_ids = {node.name: f"class_{i}" for i, node in enumerate(class_defs, start=1)}
    known_classes = set(class_ids)

    classes: list[UmlClass] = []
    edges: list[_RelEdge] = []
    for index, node in enumerate(class_defs):
        uml_class, class_edges = _build_class(node, class_ids[node.name], index, known_classes, class_ids)
        classes.append(uml_class)
        edges.extend(class_edges)

    return UmlDocument(classes=classes, relationships=_dedupe_and_number(edges))


# ---------------------------------------------------------------------------
# Class assembly
# ---------------------------------------------------------------------------


def _build_class(
    node: ClassDeclaration,
    class_id: str,
    index: int,
    known_classes: set[str],
    class_ids: dict[str, str],
) -> tuple[UmlClass, list[_RelEdge]]:
    attrs, rel_info = _fields(node, known_classes)
    _upgrade_composition(node, rel_info)

    edges: list[_RelEdge] = []
    owned_targets: set[str] = set()
    for info in rel_info.values():
        if info.target_class == node.name:
            continue  # self-reference, not a UML relationship
        owned_targets.add(info.target_class)
        rel_type = RelationshipType.COMPOSITION if info.origin == "instantiation" else RelationshipType.AGGREGATION
        edges.append(_RelEdge(class_id, class_ids[info.target_class], rel_type, info.many))

    methods: list[Method] = []
    for m in node.methods:
        methods.append(_build_method(m))
        edges.extend(_association_edges(m, class_id, node.name, known_classes, class_ids, owned_targets))

    if node.extends is not None and node.extends.name in known_classes and node.extends.name != node.name:
        edges.append(_RelEdge(class_id, class_ids[node.extends.name], RelationshipType.INHERITANCE, many=False))

    position, size = _layout(index)
    uml_class = UmlClass(
        id=class_id,
        name=node.name,
        attributes=attrs,
        methods=methods,
        position=position,
        size=size,
    )
    return uml_class, edges


# ---------------------------------------------------------------------------
# Attributes
# ---------------------------------------------------------------------------


def _fields(
    node: ClassDeclaration, known_classes: set[str]
) -> tuple[list[Attribute], dict[str, _AttrRelInfo]]:
    """Java requires every instance field to be declared at the class level
    (unlike Python, there's no implicit `self.x = ...` field creation), so
    every attribute -- and its relationship-inference baseline -- comes from
    field declarations alone. A field whose declared type is a single known
    class is provisionally AGGREGATION; `_upgrade_composition` below promotes
    it to COMPOSITION when a constructor demonstrably instantiates it."""
    attrs: list[Attribute] = []
    rel_info: dict[str, _AttrRelInfo] = {}

    for field in node.fields:
        datatype = _type_to_str(field.type)
        modifiers = field.modifiers
        for declarator in field.declarators:
            attrs.append(
                Attribute(
                    name=declarator.name,
                    datatype=datatype,
                    visibility=_visibility_from_modifiers(modifiers),
                    default_value=_literal_to_str(declarator.initializer),
                    static="static" in modifiers,
                    final="final" in modifiers,
                )
            )
            refs = _extract_class_refs(field.type, known_classes)
            if len(refs) == 1:
                (target,) = refs
                rel_info[declarator.name] = _AttrRelInfo(target, "annotated-only", _is_many(datatype))

    return attrs, rel_info


def _upgrade_composition(node: ClassDeclaration, rel_info: dict[str, _AttrRelInfo]) -> None:
    """Scans the first constructor's top-level body for `this.field = new X()`
    and promotes that field's relationship from the annotation-only aggregation
    baseline to composition. Only looks at statements directly in the
    constructor body -- not one level into if/for/while/try the way the Python
    parser does -- to keep the Java parser's scope simple."""
    if not node.constructors:
        return
    for stmt in node.constructors[0].body or []:
        name, value = _this_assignment_parts(stmt)
        if name is None or name not in rel_info or not isinstance(value, ClassCreator):
            continue
        info = rel_info[name]
        if value.type.name == info.target_class:
            rel_info[name] = _AttrRelInfo(info.target_class, "instantiation", info.many)


def _this_assignment_parts(stmt: Any) -> tuple[str | None, Any]:
    """(field name, RHS value node) for a `this.field = ...` statement, else
    (None, None)."""
    expr: Any = getattr(stmt, "expression", None)
    if type(expr).__name__ != "Assignment":
        return None, None
    target: Any = expr.expressionl
    if type(target).__name__ != "This" or not target.selectors:
        return None, None
    selector = target.selectors[0]
    if not isinstance(selector, MemberReference):
        return None, None
    return selector.member, expr.value


def _literal_to_str(node: Any) -> str | None:
    if type(node).__name__ == "Literal":
        return str(node.value)
    return None  # non-literal RHS -- a provable type may still exist, but not a provable default


# ---------------------------------------------------------------------------
# Methods
# ---------------------------------------------------------------------------


def _build_method(node: Any) -> Method:
    modifiers = node.modifiers
    params = [Parameter(name=p.name, datatype=_type_to_str(p.type)) for p in node.parameters]
    return_type = _type_to_str(node.return_type) if node.return_type is not None else "void"

    return Method(
        name=node.name,
        visibility=_visibility_from_modifiers(modifiers),
        parameters=params,
        return_type=return_type,
        static="static" in modifiers,
        abstract="abstract" in modifiers or node.body is None,
    )


# ---------------------------------------------------------------------------
# Relationships -- inheritance and aggregation/composition are attached in
# _build_class; association below.
# ---------------------------------------------------------------------------


def _association_edges(
    node: Any,
    class_id: str,
    class_name: str,
    known_classes: set[str],
    class_ids: dict[str, str],
    owned_targets: set[str],
) -> list[_RelEdge]:
    referenced: set[str] = set()
    for p in node.parameters:
        referenced |= _extract_class_refs(p.type, known_classes)
    if node.return_type is not None:
        referenced |= _extract_class_refs(node.return_type, known_classes)
    referenced.discard(class_name)
    referenced -= owned_targets  # "uses but doesn't own" -- complement of aggregation/composition

    return [
        _RelEdge(class_id, class_ids[target], RelationshipType.ASSOCIATION, many=False)
        for target in sorted(referenced)
    ]


def _dedupe_and_number(edges: list[_RelEdge]) -> list[Relationship]:
    seen: dict[tuple[str, str, RelationshipType], bool] = {}
    ordered_keys: list[tuple[str, str, RelationshipType]] = []
    for e in edges:
        key = (e.source_id, e.dest_id, e.type)
        if key not in seen:
            seen[key] = e.many
            ordered_keys.append(key)
        else:
            seen[key] = seen[key] or e.many

    relationships: list[Relationship] = []
    for i, (source_id, dest_id, rel_type) in enumerate(ordered_keys, start=1):
        relationships.append(
            Relationship(
                id=f"rel_{i}",
                source=source_id,
                destination=dest_id,
                type=rel_type,
                multiplicity=Multiplicity(source="1", destination="*" if seen[(source_id, dest_id, rel_type)] else "1"),
                label="",
            )
        )
    return relationships


# ---------------------------------------------------------------------------
# Shared: type strings, visibility, layout
# ---------------------------------------------------------------------------


def _type_to_str(node: Any) -> str:
    outer = node.name
    is_array = bool(getattr(node, "dimensions", None))
    arguments = getattr(node, "arguments", None)

    if arguments:
        inner_types = [_type_to_str(arg.type) for arg in arguments if arg.type is not None]
        outer_name = _SCALAR_NEUTRAL_MAP.get(outer, outer)
        return f"{outer_name}[{', '.join(inner_types)}]"

    neutral = _SCALAR_NEUTRAL_MAP.get(outer, outer)
    return f"List[{neutral}]" if is_array else neutral


def _extract_class_refs(node: Any | None, known_classes: set[str]) -> set[str]:
    """Names of known local classes referenced by a type node, including one
    level of generic arguments (List<X>, Map<K, X>)."""
    if node is None:
        return set()
    refs: set[str] = set()
    if node.name in known_classes:
        refs.add(node.name)
    for arg in getattr(node, "arguments", None) or []:
        if arg.type is not None and arg.type.name in known_classes:
            refs.add(arg.type.name)
    return refs


def _is_many(datatype: str) -> bool:
    outer = datatype.split("[", 1)[0].strip()
    return outer in _MANY_CONTAINERS


def _visibility_from_modifiers(modifiers: set[str]) -> Visibility:
    if "private" in modifiers:
        return Visibility.PRIVATE
    if "protected" in modifiers:
        return Visibility.PROTECTED
    if "public" in modifiers:
        return Visibility.PUBLIC
    return Visibility.PACKAGE  # no access modifier -- Java's default "package-private"


def _layout(index: int) -> tuple[Position, Size]:
    col, row = index % _GRID_COLUMNS, index // _GRID_COLUMNS
    return (
        Position(x=col * (_BOX_WIDTH + _H_GAP), y=row * (_BOX_HEIGHT + _V_GAP)),
        Size(width=_BOX_WIDTH, height=_BOX_HEIGHT),
    )


# ---------------------------------------------------------------------------
# Control-flow extraction (Milestone 6) -- mirrors the Python parser's
# extract_control_flow file-for-file (same node/edge/tail-tracking algorithm);
# only the AST access shifts to javalang's node shapes. See that file's
# module comment for the full scope note (if/while/for modeled; try/switch/
# synchronized recorded as one opaque action; break/continue unmodeled).
# javalang has no `ast.unparse` equivalent, so `_expr_to_str` below is a
# small bounded stringifier for common expression shapes -- anything it
# doesn't recognize renders as its node type name rather than a guess.
# ---------------------------------------------------------------------------

_ACTION_LABEL_MAX = 60
_NODE_WIDTH = 160.0
_NODE_HEIGHT = 80.0
_NODE_V_GAP = 40.0

_OpenTails = list[tuple[str, str]]


class _CfgBuilder:
    def __init__(self) -> None:
        self.nodes: list[ActivityNode] = []
        self.edges: list[ActivityEdge] = []
        self._node_count = 0
        self._edge_count = 0

    def add_node(self, node_type: ActivityNodeType, label: str = "") -> str:
        self._node_count += 1
        node_id = f"n{self._node_count}"
        y = (self._node_count - 1) * (_NODE_HEIGHT + _NODE_V_GAP)
        self.nodes.append(
            ActivityNode(
                id=node_id,
                type=node_type,
                label=label,
                position=Position(x=0.0, y=y),
                size=Size(width=_NODE_WIDTH, height=_NODE_HEIGHT),
            )
        )
        return node_id

    def add_edge(self, source: str, target: str, label: str = "") -> None:
        self._edge_count += 1
        self.edges.append(ActivityEdge(id=f"e{self._edge_count}", source=source, target=target, label=label))


def extract_control_flow(source: str, class_name: str, method_name: str) -> ActivityDocument:
    """Reverse-engineer one method's control flow into an ActivityDocument."""
    try:
        tree = javalang.parse.parse(source)
    except (javalang.parser.JavaParserBaseException, LexerError) as exc:
        raise ValueError(f"Invalid Java source: {exc}") from exc

    class_node = next(
        (t for t in tree.types if isinstance(t, ClassDeclaration) and t.name == class_name), None
    )
    if class_node is None:
        raise ValueError(f"Class '{class_name}' not found")

    method_node = next((m for m in class_node.methods if m.name == method_name), None)
    if method_node is None or method_node.body is None:
        raise ValueError(f"Method '{method_name}' not found (or abstract) on class '{class_name}'")

    builder = _CfgBuilder()
    start_id = builder.add_node(ActivityNodeType.START)
    end_id = builder.add_node(ActivityNodeType.END)

    tails = _walk_block(method_node.body, [(start_id, "")], builder, end_id)
    for tail_id, label in tails:
        builder.add_edge(tail_id, end_id, label)

    return ActivityDocument(nodes=builder.nodes, edges=builder.edges)


def _walk_block(stmts: list[Any], entry: _OpenTails, builder: _CfgBuilder, end_id: str) -> _OpenTails:
    current = entry
    buffer: list[str] = []

    def flush() -> None:
        nonlocal current, buffer
        if not buffer:
            return
        node_id = builder.add_node(ActivityNodeType.ACTION, _truncate("; ".join(buffer)))
        for src_id, edge_label in current:
            builder.add_edge(src_id, node_id, edge_label)
        current = [(node_id, "")]
        buffer = []

    for stmt in stmts:
        if not current:
            break  # everything from here on is unreachable dead code
        type_name = type(stmt).__name__

        if type_name == "IfStatement":
            flush()
            cond_id = builder.add_node(ActivityNodeType.DECISION, _truncate(_expr_to_str(stmt.condition)))
            for src_id, edge_label in current:
                builder.add_edge(src_id, cond_id, edge_label)
            yes_tails = _walk_block(_as_stmt_list(stmt.then_statement), [(cond_id, "yes")], builder, end_id)
            no_tails = (
                _walk_block(_as_stmt_list(stmt.else_statement), [(cond_id, "no")], builder, end_id)
                if stmt.else_statement is not None
                else [(cond_id, "no")]
            )
            current = yes_tails + no_tails

        elif type_name in ("WhileStatement", "DoStatement"):
            # DoStatement (do/while) is approximated as a pre-test loop here --
            # same decision-node-with-back-edge shape, just not guaranteeing a
            # first unconditional iteration. Documented v1 simplification.
            flush()
            cond_id = builder.add_node(ActivityNodeType.DECISION, _truncate(_expr_to_str(stmt.condition)))
            for src_id, edge_label in current:
                builder.add_edge(src_id, cond_id, edge_label)
            body_tails = _walk_block(_as_stmt_list(stmt.body), [(cond_id, "yes")], builder, end_id)
            for tail_id, edge_label in body_tails:
                builder.add_edge(tail_id, cond_id, edge_label)
            current = [(cond_id, "no")]

        elif type_name == "ForStatement":
            flush()
            cond_id = builder.add_node(ActivityNodeType.DECISION, _truncate(_for_label(stmt.control)))
            for src_id, edge_label in current:
                builder.add_edge(src_id, cond_id, edge_label)
            body_tails = _walk_block(_as_stmt_list(stmt.body), [(cond_id, "yes")], builder, end_id)
            for tail_id, edge_label in body_tails:
                builder.add_edge(tail_id, cond_id, edge_label)
            current = [(cond_id, "no")]

        elif type_name in ("ReturnStatement", "ThrowStatement"):
            keyword = "return" if type_name == "ReturnStatement" else "throw"
            expr = stmt.expression
            buffer.append(f"{keyword} {_expr_to_str(expr)}" if expr is not None else keyword)
            flush()
            for src_id, edge_label in current:
                builder.add_edge(src_id, end_id, edge_label)
            current = []

        elif type_name == "BlockStatement":
            flush()
            current = _walk_block(stmt.statements, current, builder, end_id)

        else:
            buffer.append(_stmt_label(stmt))

    flush()
    return current


def _as_stmt_list(node: Any) -> list[Any]:
    if node is None:
        return []
    if type(node).__name__ == "BlockStatement":
        return list(node.statements)
    return [node]


def _for_label(control: Any) -> str:
    if type(control).__name__ == "EnhancedForControl":
        var = control.var
        name = var.declarators[0].name if getattr(var, "declarators", None) else "item"
        return f"for {name} : {_expr_to_str(control.iterable)}"
    condition = _expr_to_str(control.condition) if control.condition is not None else ""
    return f"for(; {condition}; )"


def _stmt_label(stmt: Any) -> str:
    """Best-effort short label for a statement this walker doesn't model
    structurally -- never guesses semantics, falls back to the node's own
    type name when it can't render source-accurate text."""
    type_name = type(stmt).__name__
    if type_name == "StatementExpression":
        return _truncate(_expr_to_str(stmt.expression))
    if type_name == "LocalVariableDeclaration":
        decls = ", ".join(_declarator_to_str(d, stmt.type) for d in stmt.declarators)
        return _truncate(decls)
    if type_name == "AssertStatement":
        return _truncate(f"assert {_expr_to_str(stmt.condition)}")
    if type_name.endswith("Statement"):
        return type_name[: -len("Statement")].lower() or type_name.lower()
    return type_name.lower()


def _declarator_to_str(declarator: Any, type_node: Any) -> str:
    name = f"{_type_to_str(type_node)} {declarator.name}"
    if declarator.initializer is not None:
        return f"{name} = {_expr_to_str(declarator.initializer)}"
    return name


def _expr_to_str(node: Any) -> str:
    """Small bounded stringifier for javalang expression nodes -- javalang
    has no `ast.unparse` equivalent. Anything unrecognized renders as its
    node type name rather than a guessed reconstruction."""
    if node is None:
        return ""
    type_name = type(node).__name__
    if type_name == "Literal":
        return str(node.value)
    if type_name == "MemberReference":
        base = f"{node.qualifier}." if node.qualifier else ""
        return f"{base}{node.member}"
    if type_name == "This":
        return "this"
    if type_name == "BinaryOperation":
        return f"{_expr_to_str(node.operandl)} {node.operator} {_expr_to_str(node.operandr)}"
    if type_name == "Assignment":
        return f"{_expr_to_str(node.expressionl)} {node.type} {_expr_to_str(node.value)}"
    if type_name == "MethodInvocation":
        qualifier = f"{node.qualifier}." if node.qualifier else ""
        args = ", ".join(_expr_to_str(a) for a in node.arguments or [])
        return f"{qualifier}{node.member}({args})"
    if type_name == "ClassCreator":
        args = ", ".join(_expr_to_str(a) for a in node.arguments or [])
        return f"new {node.type.name}({args})"
    if type_name == "Cast":
        return _expr_to_str(node.expression)
    return f"<{type_name}>"


def _truncate(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= _ACTION_LABEL_MAX else text[: _ACTION_LABEL_MAX - 1] + "…"
