from __future__ import annotations

import ast
from dataclasses import dataclass

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

# Python spelling -> the language-neutral vocabulary the rest of the system
# uses (see backend/generator/language_maps/python.py's TYPE_MAP, which maps
# these same neutral names back to Python on the forward/codegen side). Types
# with no listed entry (e.g. "int", "bool", already-neutral spellings, or any
# type this map doesn't recognize) pass through unchanged rather than guessed.
_SCALAR_NEUTRAL_MAP = {"str": "String", "object": "Object", "None": "void"}
_CONTAINER_NEUTRAL_MAP = {
    "list": "List", "List": "List",
    "set": "Set", "Set": "Set", "frozenset": "Set",
    "tuple": "List", "Tuple": "List",
    "dict": "Map", "Dict": "Map",
}

# Outer (neutral) container names treated as "many" for multiplicity inference.
_MANY_CONTAINERS = {"List", "Set"}

_PRIMITIVE_TYPES: dict[type, str] = {
    bool: "bool",
    int: "int",
    float: "float",
    str: "String",
}


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
    """Reverse-engineer Python source into a Unified UML JSON document."""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise ValueError(f"Invalid Python source: {exc}") from exc

    # Two passes: collect every top-level class's id first so relationship
    # inference can resolve forward references (a class used in an earlier
    # class's body but declared later in the file).
    class_defs = [n for n in tree.body if isinstance(n, ast.ClassDef)]
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
    node: ast.ClassDef,
    class_id: str,
    index: int,
    known_classes: set[str],
    class_ids: dict[str, str],
) -> tuple[UmlClass, list[_RelEdge]]:
    static_attrs, static_rel_info = _static_attributes(node, known_classes)
    init_node = _find_init(node)
    instance_attrs, instance_rel_info = (
        _instance_attributes(init_node, known_classes) if init_node is not None else ([], [])
    )
    all_rel_info = static_rel_info + instance_rel_info

    edges: list[_RelEdge] = []
    owned_targets: set[str] = set()
    for info in all_rel_info:
        if info.target_class == node.name:
            continue  # self-reference, not a UML relationship
        owned_targets.add(info.target_class)
        rel_type = RelationshipType.COMPOSITION if info.origin == "instantiation" else RelationshipType.AGGREGATION
        edges.append(_RelEdge(class_id, class_ids[info.target_class], rel_type, info.many))

    methods: list[Method] = []
    for stmt in node.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)) and stmt.name != "__init__":
            methods.append(_build_method(stmt))
            edges.extend(_association_edges(stmt, class_id, node.name, known_classes, class_ids, owned_targets))

    for base in node.bases:
        if isinstance(base, ast.Name) and base.id in known_classes and base.id != node.name:
            edges.append(_RelEdge(class_id, class_ids[base.id], RelationshipType.INHERITANCE, many=False))

    position, size = _layout(index)
    uml_class = UmlClass(
        id=class_id,
        name=node.name,
        attributes=static_attrs + instance_attrs,
        methods=methods,
        position=position,
        size=size,
    )
    return uml_class, edges


def _find_init(node: ast.ClassDef) -> ast.FunctionDef | None:
    for stmt in node.body:
        if isinstance(stmt, ast.FunctionDef) and stmt.name == "__init__":
            return stmt
    return None


# ---------------------------------------------------------------------------
# Attributes
# ---------------------------------------------------------------------------


def _static_attributes(
    node: ast.ClassDef, known_classes: set[str]
) -> tuple[list[Attribute], list[_AttrRelInfo]]:
    attrs: list[Attribute] = []
    rel_info: list[_AttrRelInfo] = []

    for stmt in node.body:
        if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            name = stmt.target.id
            is_final, inner = _unwrap_final(stmt.annotation)
            datatype = _annotation_to_str(inner) if inner is not None else "object"
            attrs.append(
                Attribute(
                    name=name,
                    datatype=datatype,
                    visibility=_visibility_from_name(name),
                    default_value=_literal_to_str(stmt.value),
                    static=True,
                    final=is_final,
                )
            )
            if inner is not None:
                refs = _extract_class_refs(inner, known_classes)
                if len(refs) == 1:
                    (target,) = refs
                    rel_info.append(_AttrRelInfo(target, "annotated-only", _is_many(datatype)))

        elif (
            isinstance(stmt, ast.Assign)
            and len(stmt.targets) == 1
            and isinstance(stmt.targets[0], ast.Name)
            and isinstance(stmt.value, ast.Constant)
        ):
            name = stmt.targets[0].id
            attrs.append(
                Attribute(
                    name=name,
                    datatype=_literal_datatype(stmt.value.value),
                    visibility=_visibility_from_name(name),
                    default_value=repr(stmt.value.value),
                    static=True,
                    final=False,
                )
            )
        # Anything else at class-body level (methods, docstrings, non-literal
        # assignments) can't be proven from the AST without guessing — skipped.

    return attrs, rel_info


def _instance_attributes(
    init_node: ast.FunctionDef, known_classes: set[str]
) -> tuple[list[Attribute], list[_AttrRelInfo]]:
    param_annotations = _init_param_annotations(init_node)
    attrs: list[Attribute] = []
    rel_info: list[_AttrRelInfo] = []
    seen_names: set[str] = set()

    for stmt in _statements_one_level(init_node.body):
        name, annotation, value = _self_assignment_parts(stmt)
        if name is None or name in seen_names:
            continue  # first occurrence of a given self.x wins; no fabricated merge
        seen_names.add(name)

        target_class: str | None = None
        origin: str | None = None
        many = False

        if annotation is not None:
            is_final, inner = _unwrap_final(annotation)
            datatype = _annotation_to_str(inner) if inner is not None else "object"
            if inner is not None:
                refs = _extract_class_refs(inner, known_classes)
                if len(refs) == 1:
                    (target_class,) = refs
                    origin = "annotated-only"
                    many = _is_many(datatype)
        else:
            is_final = False
            datatype, origin, target_class, many = _infer_from_value(value, param_annotations, known_classes)

        attrs.append(
            Attribute(
                name=name,
                datatype=datatype,
                visibility=_visibility_from_name(name),
                default_value=_literal_to_str(value),
                static=False,
                final=is_final,
            )
        )
        if target_class is not None and origin is not None:
            rel_info.append(_AttrRelInfo(target_class, origin, many))

    return attrs, rel_info


def _init_param_annotations(init_node: ast.FunctionDef) -> dict[str, ast.expr]:
    return {a.arg: a.annotation for a in init_node.args.args[1:] if a.annotation is not None}


def _statements_one_level(body: list[ast.stmt]) -> list[ast.stmt]:
    """Top-level statements plus one level into if/for/while/try/with blocks;
    never descends into nested function/class/lambda bodies, since assignments
    inside a closure aren't unconditionally-executed instance state."""
    result: list[ast.stmt] = []
    for stmt in body:
        result.append(stmt)
        if isinstance(stmt, (ast.If, ast.For, ast.AsyncFor, ast.While)):
            result.extend(stmt.body)
            result.extend(stmt.orelse)
        elif isinstance(stmt, ast.Try):
            result.extend(stmt.body)
            for handler in stmt.handlers:
                result.extend(handler.body)
            result.extend(stmt.orelse)
            result.extend(stmt.finalbody)
        elif isinstance(stmt, (ast.With, ast.AsyncWith)):
            result.extend(stmt.body)
    return result


def _self_assignment_parts(stmt: ast.stmt) -> tuple[str | None, ast.expr | None, ast.expr | None]:
    """(attribute name, annotation, value) for a `self.x = ...` / `self.x: T = ...`
    statement, else (None, None, None)."""
    target: ast.expr
    if isinstance(stmt, ast.AnnAssign) and _is_self_attribute(stmt.target):
        target = stmt.target
        assert isinstance(target, ast.Attribute)
        return target.attr, stmt.annotation, stmt.value
    if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and _is_self_attribute(stmt.targets[0]):
        target = stmt.targets[0]
        assert isinstance(target, ast.Attribute)
        return target.attr, None, stmt.value
    return None, None, None


def _is_self_attribute(node: ast.expr) -> bool:
    return isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "self"


def _infer_from_value(
    value: ast.expr | None, param_annotations: dict[str, ast.expr], known_classes: set[str]
) -> tuple[str, str | None, str | None, bool]:
    """(datatype, origin, target_class, many) inferred from an unannotated `self.x = <value>`."""
    if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id in known_classes:
        return value.func.id, "instantiation", value.func.id, False

    if isinstance(value, ast.Name) and value.id in param_annotations:
        annotation = param_annotations[value.id]
        refs = _extract_class_refs(annotation, known_classes)
        if len(refs) == 1:
            (target,) = refs
            datatype = _annotation_to_str(annotation)
            return datatype, "param-passthrough", target, _is_many(datatype)

    if isinstance(value, ast.Constant):
        return _literal_datatype(value.value), None, None, False

    return "object", None, None, False


def _literal_datatype(value: object) -> str:
    if value is None:
        return "object"
    return _PRIMITIVE_TYPES.get(type(value), "object")


def _literal_to_str(node: ast.expr | None) -> str | None:
    if isinstance(node, ast.Constant):
        return repr(node.value)
    return None  # non-literal RHS — a provable type may still exist, but not a provable default


def _unwrap_final(annotation: ast.expr) -> tuple[bool, ast.expr | None]:
    """(is_final, inner_annotation) for a possibly Final[...]/Final annotation.
    Bare `Final` with no subscript can't be resolved to a real type — inner is None."""
    if isinstance(annotation, ast.Subscript) and _name_of(annotation.value) == "Final":
        return True, annotation.slice
    if _name_of(annotation) == "Final":
        return True, None
    return False, annotation


def _name_of(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


# ---------------------------------------------------------------------------
# Methods
# ---------------------------------------------------------------------------


def _build_method(node: ast.FunctionDef | ast.AsyncFunctionDef) -> Method:
    decorator_names = {_name_of(d) for d in node.decorator_list}
    is_static = _is_static_decorator(node) or "classmethod" in decorator_names
    is_abstract = "abstractmethod" in decorator_names or _raises_not_implemented(node)

    params = [
        Parameter(name=a.arg, datatype=_annotation_to_str(a.annotation) if a.annotation is not None else "object")
        for a in _explicit_params(node)
    ]
    return_type = _annotation_to_str(node.returns) if node.returns is not None else "void"

    return Method(
        name=node.name,
        visibility=_visibility_from_name(node.name),
        parameters=params,
        return_type=return_type,
        static=is_static,
        abstract=is_abstract,
    )


def _is_static_decorator(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return any(_name_of(d) == "staticmethod" for d in node.decorator_list)


def _explicit_params(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.arg]:
    """Positional params excluding an implicit self/cls (a staticmethod has neither)."""
    return list(node.args.args) if _is_static_decorator(node) else node.args.args[1:]


def _raises_not_implemented(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    body = node.body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(
        body[0].value.value, str
    ):
        body = body[1:]  # skip a leading docstring
    if len(body) != 1 or not isinstance(body[0], ast.Raise):
        return False  # a `pass`/`...` stub is not a reliable abstract-method signal
    exc = body[0].exc
    if isinstance(exc, ast.Call):
        exc = exc.func
    return isinstance(exc, ast.Name) and exc.id == "NotImplementedError"


# ---------------------------------------------------------------------------
# Relationships — inheritance (in _build_class) + aggregation/composition
# (from attribute rel_info, in _build_class) + association (below)
# ---------------------------------------------------------------------------


def _association_edges(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    class_id: str,
    class_name: str,
    known_classes: set[str],
    class_ids: dict[str, str],
    owned_targets: set[str],
) -> list[_RelEdge]:
    referenced: set[str] = set()
    for a in _explicit_params(node):
        if a.annotation is not None:
            referenced |= _extract_class_refs(a.annotation, known_classes)
    if node.returns is not None:
        referenced |= _extract_class_refs(node.returns, known_classes)
    referenced.discard(class_name)
    referenced -= owned_targets  # "uses but doesn't own" — complement of aggregation/composition

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
# Shared: type-annotation strings, visibility, layout
# ---------------------------------------------------------------------------


def _annotation_to_str(node: ast.expr) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return _to_neutral_type(node.value)  # forward-ref string, e.g. 'OtherClass' — keep unquoted
    return _to_neutral_type(ast.unparse(node))


def _to_neutral_type(raw: str) -> str:
    if "[" in raw and raw.endswith("]"):
        outer, _, inner = raw.partition("[")
        outer = outer.strip()
        inner = inner[:-1]
        mapped_inner = ", ".join(_to_neutral_type(part.strip()) for part in inner.split(","))
        return f"{_CONTAINER_NEUTRAL_MAP.get(outer, outer)}[{mapped_inner}]"
    return _SCALAR_NEUTRAL_MAP.get(raw, raw)


def _extract_class_refs(node: ast.expr, known_classes: set[str]) -> set[str]:
    """Names of known local classes referenced anywhere inside an annotation
    expression, including nested generics (list[X], dict[str, X])."""
    target: ast.AST = node
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        try:
            target = ast.parse(node.value, mode="eval").body
        except SyntaxError:
            return set()
    return {n.id for n in ast.walk(target) if isinstance(n, ast.Name) and n.id in known_classes}


def _is_many(datatype: str) -> bool:
    outer = datatype.split("[", 1)[0].strip()
    return outer in _MANY_CONTAINERS


def _visibility_from_name(name: str) -> Visibility:
    if name.startswith("__") and name.endswith("__"):
        return Visibility.PUBLIC  # dunder — Python's public special-method protocol
    if name.startswith("__"):
        return Visibility.PRIVATE  # name-mangled
    if name.startswith("_"):
        return Visibility.PROTECTED
    return Visibility.PUBLIC


def _layout(index: int) -> tuple[Position, Size]:
    col, row = index % _GRID_COLUMNS, index // _GRID_COLUMNS
    return (
        Position(x=col * (_BOX_WIDTH + _H_GAP), y=row * (_BOX_HEIGHT + _V_GAP)),
        Size(width=_BOX_WIDTH, height=_BOX_HEIGHT),
    )


# ---------------------------------------------------------------------------
# Control-flow extraction (Milestone 6) -- a second, optional extraction path
# through this same module: walks one method's body (not the whole file) and
# reduces sequence/branch/loop into an ActivityDocument. Independent of
# `parse` above -- callers name the class/method they want, since a
# whole-file control-flow graph has no single entry point the way a class
# structure does. Scope: if/elif/else and while/for loops (loops render as a
# DECISION node with a back edge, matching the structuring algorithm's own
# "back edge into a decision" convention). try/except, match, and nested
# def/class bodies are recorded as a single opaque action rather than
# modeled in detail; break/continue are recorded as plain action text without
# their jump semantics -- documented v1 limitations, not fabricated detail.
# ---------------------------------------------------------------------------

_ACTION_LABEL_MAX = 60
_NODE_WIDTH = 160.0
_NODE_HEIGHT = 80.0
_NODE_V_GAP = 40.0

_OPAQUE_COMPOUND_TYPES = (ast.Try, ast.Match, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)

# (node_id, edge_label) pairs: open edges waiting to be drawn into whichever
# node comes next.
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
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise ValueError(f"Invalid Python source: {exc}") from exc

    class_node = next(
        (n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name), None
    )
    if class_node is None:
        raise ValueError(f"Class '{class_name}' not found")

    method_node = next(
        (
            n
            for n in class_node.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == method_name
        ),
        None,
    )
    if method_node is None:
        raise ValueError(f"Method '{method_name}' not found on class '{class_name}'")

    builder = _CfgBuilder()
    start_id = builder.add_node(ActivityNodeType.START)
    end_id = builder.add_node(ActivityNodeType.END)

    tails = _walk_block(method_node.body, [(start_id, "")], builder, end_id)
    for tail_id, label in tails:
        builder.add_edge(tail_id, end_id, label)

    return ActivityDocument(nodes=builder.nodes, edges=builder.edges)


def _walk_block(
    stmts: list[ast.stmt], entry: _OpenTails, builder: _CfgBuilder, end_id: str
) -> _OpenTails:
    """Process a straight-line list of statements. `entry` is the open-tail
    set an edge should be drawn from into the first node this block creates.
    Returns the same shape: open tails after the last statement, for the
    caller to wire into whatever follows (or END)."""
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
        if _is_docstring(stmt):
            continue

        if isinstance(stmt, ast.If):
            flush()
            cond_id = builder.add_node(ActivityNodeType.DECISION, _truncate(ast.unparse(stmt.test)))
            for src_id, edge_label in current:
                builder.add_edge(src_id, cond_id, edge_label)
            yes_tails = _walk_block(stmt.body, [(cond_id, "yes")], builder, end_id)
            no_tails = (
                _walk_block(stmt.orelse, [(cond_id, "no")], builder, end_id)
                if stmt.orelse
                else [(cond_id, "no")]
            )
            current = yes_tails + no_tails

        elif isinstance(stmt, (ast.While, ast.For, ast.AsyncFor)):
            flush()
            label = ast.unparse(stmt.test) if isinstance(stmt, ast.While) else _for_label(stmt)
            cond_id = builder.add_node(ActivityNodeType.DECISION, _truncate(label))
            for src_id, edge_label in current:
                builder.add_edge(src_id, cond_id, edge_label)
            body_tails = _walk_block(stmt.body, [(cond_id, "yes")], builder, end_id)
            for tail_id, edge_label in body_tails:
                builder.add_edge(tail_id, cond_id, edge_label)  # back edge
            current = [(cond_id, "no")]

        elif isinstance(stmt, ast.Return):
            buffer.append(f"return {ast.unparse(stmt.value)}" if stmt.value is not None else "return")
            flush()
            for src_id, edge_label in current:
                builder.add_edge(src_id, end_id, edge_label)
            current = []

        elif isinstance(stmt, (ast.With, ast.AsyncWith)):
            buffer.append(_truncate(f"with {', '.join(ast.unparse(item) for item in stmt.items)}"))
            flush()
            current = _walk_block(stmt.body, current, builder, end_id)

        elif isinstance(stmt, _OPAQUE_COMPOUND_TYPES):
            buffer.append(type(stmt).__name__.lower())

        else:
            buffer.append(ast.unparse(stmt))

    flush()
    return current


def _for_label(stmt: ast.For | ast.AsyncFor) -> str:
    keyword = "async for" if isinstance(stmt, ast.AsyncFor) else "for"
    return f"{keyword} {ast.unparse(stmt.target)} in {ast.unparse(stmt.iter)}"


def _is_docstring(stmt: ast.stmt) -> bool:
    return (
        isinstance(stmt, ast.Expr)
        and isinstance(stmt.value, ast.Constant)
        and isinstance(stmt.value.value, str)
    )


def _truncate(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= _ACTION_LABEL_MAX else text[: _ACTION_LABEL_MAX - 1] + "…"
