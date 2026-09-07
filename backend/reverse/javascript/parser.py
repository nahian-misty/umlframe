from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import esprima
from esprima.error_handler import Error as EsprimaError

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

# JavaScript is untyped and esprima (this port only supports ES5/early-ES6
# grammar -- no class fields, no TypeScript) exposes no type annotations at
# all, so unlike the Python and Java parsers there is no language-neutral
# type-mapping table here: every attribute/parameter/return type that can't
# be proven is recorded as "any" rather than guessed.
_UNKNOWN_TYPE = "any"


@dataclass
class _RelEdge:
    source_id: str
    dest_id: str
    type: RelationshipType


def parse(source: str) -> UmlDocument:
    """Reverse-engineer JavaScript source into a Unified UML JSON document."""
    try:
        tree = esprima.parseScript(source)
    except EsprimaError as exc:
        raise ValueError(f"Invalid JavaScript source: {exc}") from exc

    # Only top-level `class Foo {}` declarations -- classes assigned via an
    # expression (`const Foo = class {}`) and nested/local classes aren't
    # visited, matching the Python/Java parsers' "top-level named class only"
    # scope.
    class_defs = [n for n in tree.body if n.type == "ClassDeclaration"]
    class_ids = {node.id.name: f"class_{i}" for i, node in enumerate(class_defs, start=1)}
    known_classes = set(class_ids)

    classes: list[UmlClass] = []
    edges: list[_RelEdge] = []
    for index, node in enumerate(class_defs):
        uml_class, class_edges = _build_class(node, class_ids[node.id.name], index, known_classes, class_ids)
        classes.append(uml_class)
        edges.extend(class_edges)

    return UmlDocument(classes=classes, relationships=_dedupe_and_number(edges))


# ---------------------------------------------------------------------------
# Class assembly
# ---------------------------------------------------------------------------


def _build_class(
    node: Any,
    class_id: str,
    index: int,
    known_classes: set[str],
    class_ids: dict[str, str],
) -> tuple[UmlClass, list[_RelEdge]]:
    attrs, edges = _constructor_attributes(node, class_id, known_classes, class_ids)

    methods: list[Method] = []
    for member in node.body.body:
        if member.type != "MethodDefinition" or member.kind == "constructor":
            continue
        methods.append(_build_method(member))

    super_class = node.superClass
    if super_class is not None and super_class.type == "Identifier" and super_class.name in known_classes:
        edges.append(_RelEdge(class_id, class_ids[super_class.name], RelationshipType.INHERITANCE))

    position, size = _layout(index)
    uml_class = UmlClass(
        id=class_id,
        name=node.id.name,
        attributes=attrs,
        methods=methods,
        position=position,
        size=size,
    )
    return uml_class, edges


# ---------------------------------------------------------------------------
# Attributes -- instance state assigned in the constructor. JS has no field
# declaration syntax this parser recognizes (see _UNKNOWN_TYPE note above), so
# unlike Python/Java there is no separate static-attribute pass.
# ---------------------------------------------------------------------------


def _constructor_attributes(
    node: Any, class_id: str, known_classes: set[str], class_ids: dict[str, str]
) -> tuple[list[Attribute], list[_RelEdge]]:
    ctor = next(
        (m for m in node.body.body if m.type == "MethodDefinition" and m.kind == "constructor"),
        None,
    )
    if ctor is None:
        return [], []

    attrs: list[Attribute] = []
    edges: list[_RelEdge] = []
    seen_names: set[str] = set()

    for stmt in ctor.value.body.body:
        name, value = _this_assignment_parts(stmt)
        if name is None or name in seen_names:
            continue  # first occurrence of a given this.x wins; no fabricated merge
        seen_names.add(name)

        datatype = _UNKNOWN_TYPE
        target_class: str | None = None
        if value is not None and value.type == "NewExpression" and value.callee.type == "Identifier":
            callee_name = value.callee.name
            if callee_name in known_classes:
                datatype = callee_name
                target_class = callee_name

        attrs.append(
            Attribute(
                name=name,
                datatype=datatype,
                visibility=_visibility_from_name(name),
                default_value=_literal_to_str(value),
                static=False,
                final=False,
            )
        )
        if target_class is not None and target_class != node.id.name:
            edges.append(_RelEdge(class_id, class_ids[target_class], RelationshipType.COMPOSITION))

    return attrs, edges


def _this_assignment_parts(stmt: Any) -> tuple[str | None, Any]:
    """(field name, RHS value node) for a `this.field = ...` statement, else
    (None, None). Only handles statements directly in the constructor body."""
    if stmt.type != "ExpressionStatement" or stmt.expression.type != "AssignmentExpression":
        return None, None
    left = stmt.expression.left
    if left.type != "MemberExpression" or left.computed or left.object.type != "ThisExpression":
        return None, None
    return left.property.name, stmt.expression.right


def _literal_to_str(node: Any) -> str | None:
    if node is not None and node.type == "Literal":
        return str(node.value)
    return None  # non-literal RHS -- a provable type may still exist, but not a provable default


# ---------------------------------------------------------------------------
# Methods
# ---------------------------------------------------------------------------


def _build_method(node: Any) -> Method:
    params = [Parameter(name=name, datatype=_UNKNOWN_TYPE) for name in _param_names(node.value.params)]
    return Method(
        name=node.key.name,
        visibility=_visibility_from_name(node.key.name),
        parameters=params,
        return_type=_UNKNOWN_TYPE,
        static=node.static,
        abstract=False,  # JS has no abstract-method syntax
    )


def _param_names(params: list[Any]) -> list[str]:
    """Plain identifier names only -- destructuring patterns can't be named
    without guessing and are dropped, not approximated."""
    names: list[str] = []
    for p in params:
        if p.type == "Identifier":
            names.append(p.name)
        elif p.type == "AssignmentPattern" and p.left.type == "Identifier":
            names.append(p.left.name)
        elif p.type == "RestElement" and p.argument.type == "Identifier":
            names.append(p.argument.name)
    return names


# ---------------------------------------------------------------------------
# Shared: dedup/numbering, visibility, layout
# ---------------------------------------------------------------------------


def _dedupe_and_number(edges: list[_RelEdge]) -> list[Relationship]:
    seen: set[tuple[str, str, RelationshipType]] = set()
    ordered_keys: list[tuple[str, str, RelationshipType]] = []
    for e in edges:
        key = (e.source_id, e.dest_id, e.type)
        if key not in seen:
            seen.add(key)
            ordered_keys.append(key)

    return [
        Relationship(
            id=f"rel_{i}",
            source=source_id,
            destination=dest_id,
            type=rel_type,
            multiplicity=Multiplicity(source="1", destination="1"),
            label="",
        )
        for i, (source_id, dest_id, rel_type) in enumerate(ordered_keys, start=1)
    ]


def _visibility_from_name(name: str) -> Visibility:
    # JS has no formal visibility keywords this parser recognizes (ES2022
    # `#private` fields aren't supported by esprima's grammar) -- a leading
    # underscore is the common "private by convention" idiom.
    return Visibility.PRIVATE if name.startswith("_") else Visibility.PUBLIC


def _layout(index: int) -> tuple[Position, Size]:
    col, row = index % _GRID_COLUMNS, index // _GRID_COLUMNS
    return (
        Position(x=col * (_BOX_WIDTH + _H_GAP), y=row * (_BOX_HEIGHT + _V_GAP)),
        Size(width=_BOX_WIDTH, height=_BOX_HEIGHT),
    )


# ---------------------------------------------------------------------------
# Control-flow extraction (Milestone 6) -- mirrors the Python parser's
# extract_control_flow file-for-file (same node/edge/tail-tracking algorithm);
# only the AST access shifts to esprima's ESTree-shaped nodes (`.type`
# strings, `BlockStatement.body` instead of Python's stmt list). See that
# file's module comment for the full scope note. esprima has no
# `ast.unparse` equivalent, so `_expr_to_str` below is a small bounded
# stringifier for common expression shapes -- anything it doesn't recognize
# renders as its node type name rather than a guess.
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
        tree = esprima.parseScript(source)
    except EsprimaError as exc:
        raise ValueError(f"Invalid JavaScript source: {exc}") from exc

    class_node = next(
        (n for n in tree.body if n.type == "ClassDeclaration" and n.id.name == class_name), None
    )
    if class_node is None:
        raise ValueError(f"Class '{class_name}' not found")

    method_node = next(
        (
            m
            for m in class_node.body.body
            if m.type == "MethodDefinition" and m.kind != "constructor" and m.key.name == method_name
        ),
        None,
    )
    if method_node is None:
        raise ValueError(f"Method '{method_name}' not found on class '{class_name}'")

    builder = _CfgBuilder()
    start_id = builder.add_node(ActivityNodeType.START)
    end_id = builder.add_node(ActivityNodeType.END)

    tails = _walk_block(method_node.value.body.body, [(start_id, "")], builder, end_id)
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
        node_type = stmt.type

        if node_type == "IfStatement":
            flush()
            cond_id = builder.add_node(ActivityNodeType.DECISION, _truncate(_expr_to_str(stmt.test)))
            for src_id, edge_label in current:
                builder.add_edge(src_id, cond_id, edge_label)
            yes_tails = _walk_block(_as_stmt_list(stmt.consequent), [(cond_id, "yes")], builder, end_id)
            no_tails = (
                _walk_block(_as_stmt_list(stmt.alternate), [(cond_id, "no")], builder, end_id)
                if stmt.alternate is not None
                else [(cond_id, "no")]
            )
            current = yes_tails + no_tails

        elif node_type in ("WhileStatement", "DoWhileStatement"):
            # DoWhileStatement is approximated as a pre-test loop -- same
            # decision-node-with-back-edge shape, just not guaranteeing a
            # first unconditional iteration. Documented v1 simplification.
            flush()
            cond_id = builder.add_node(ActivityNodeType.DECISION, _truncate(_expr_to_str(stmt.test)))
            for src_id, edge_label in current:
                builder.add_edge(src_id, cond_id, edge_label)
            body_tails = _walk_block(_as_stmt_list(stmt.body), [(cond_id, "yes")], builder, end_id)
            for tail_id, edge_label in body_tails:
                builder.add_edge(tail_id, cond_id, edge_label)
            current = [(cond_id, "no")]

        elif node_type == "ForStatement":
            flush()
            label = _expr_to_str(stmt.test) if stmt.test is not None else "for(...)"
            cond_id = builder.add_node(ActivityNodeType.DECISION, _truncate(label))
            for src_id, edge_label in current:
                builder.add_edge(src_id, cond_id, edge_label)
            body_tails = _walk_block(_as_stmt_list(stmt.body), [(cond_id, "yes")], builder, end_id)
            for tail_id, edge_label in body_tails:
                builder.add_edge(tail_id, cond_id, edge_label)
            current = [(cond_id, "no")]

        elif node_type in ("ForInStatement", "ForOfStatement"):
            flush()
            keyword = "for..in" if node_type == "ForInStatement" else "for..of"
            cond_id = builder.add_node(
                ActivityNodeType.DECISION, _truncate(f"{keyword} {_expr_to_str(stmt.right)}")
            )
            for src_id, edge_label in current:
                builder.add_edge(src_id, cond_id, edge_label)
            body_tails = _walk_block(_as_stmt_list(stmt.body), [(cond_id, "yes")], builder, end_id)
            for tail_id, edge_label in body_tails:
                builder.add_edge(tail_id, cond_id, edge_label)
            current = [(cond_id, "no")]

        elif node_type in ("ReturnStatement", "ThrowStatement"):
            keyword = "return" if node_type == "ReturnStatement" else "throw"
            expr = stmt.argument
            buffer.append(f"{keyword} {_expr_to_str(expr)}" if expr is not None else keyword)
            flush()
            for src_id, edge_label in current:
                builder.add_edge(src_id, end_id, edge_label)
            current = []

        elif node_type == "BlockStatement":
            flush()
            current = _walk_block(stmt.body, current, builder, end_id)

        else:
            buffer.append(_stmt_label(stmt))

    flush()
    return current


def _as_stmt_list(node: Any) -> list[Any]:
    if node is None:
        return []
    if node.type == "BlockStatement":
        return list(node.body)
    return [node]


def _stmt_label(stmt: Any) -> str:
    """Best-effort short label for a statement this walker doesn't model
    structurally -- never guesses semantics, falls back to the node's own
    type name when it can't render source-accurate text."""
    node_type = stmt.type
    if node_type == "ExpressionStatement":
        return _truncate(_expr_to_str(stmt.expression))
    if node_type == "VariableDeclaration":
        decls = ", ".join(_declarator_to_str(d) for d in stmt.declarations)
        return _truncate(f"{stmt.kind} {decls}")
    if node_type.endswith("Statement"):
        return str(node_type[: -len("Statement")].lower() or node_type.lower())
    return str(node_type.lower())


def _declarator_to_str(declarator: Any) -> str:
    name = str(declarator.id.name)
    if declarator.init is not None:
        return f"{name} = {_expr_to_str(declarator.init)}"
    return name


def _expr_to_str(node: Any) -> str:
    """Small bounded stringifier for esprima expression nodes -- esprima has
    no `ast.unparse` equivalent. Anything unrecognized renders as its node
    type name rather than a guessed reconstruction."""
    if node is None:
        return ""
    node_type = node.type
    if node_type == "Literal":
        return node.raw if getattr(node, "raw", None) is not None else str(node.value)
    if node_type == "Identifier":
        return str(node.name)
    if node_type == "ThisExpression":
        return "this"
    if node_type == "MemberExpression":
        obj = _expr_to_str(node.object)
        if node.computed:
            return f"{obj}[{_expr_to_str(node.property)}]"
        return f"{obj}.{node.property.name}"
    if node_type in ("BinaryExpression", "LogicalExpression"):
        return f"{_expr_to_str(node.left)} {node.operator} {_expr_to_str(node.right)}"
    if node_type == "AssignmentExpression":
        return f"{_expr_to_str(node.left)} {node.operator} {_expr_to_str(node.right)}"
    if node_type == "CallExpression":
        args = ", ".join(_expr_to_str(a) for a in node.arguments)
        return f"{_expr_to_str(node.callee)}({args})"
    if node_type == "NewExpression":
        args = ", ".join(_expr_to_str(a) for a in node.arguments)
        return f"new {_expr_to_str(node.callee)}({args})"
    if node_type == "UnaryExpression":
        return f"{node.operator}{_expr_to_str(node.argument)}"
    if node_type == "UpdateExpression":
        if node.prefix:
            return f"{node.operator}{_expr_to_str(node.argument)}"
        return f"{_expr_to_str(node.argument)}{node.operator}"
    return f"<{node_type}>"


def _truncate(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= _ACTION_LABEL_MAX else text[: _ACTION_LABEL_MAX - 1] + "…"
