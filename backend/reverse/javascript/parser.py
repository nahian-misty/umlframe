from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import esprima
from esprima.error_handler import Error as EsprimaError

from backend.reverse.phrasing import describe_steps
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

# esprima exposes no type annotations (and this port has no class fields or
# TypeScript), so a type is only recorded when it can be proven: from a JSDoc
# tag, a literal / `new X()` / call whose result type is fixed, a parameter
# default value, or the `return` statements of a method. Everything else is
# "any" rather than a guess.
_UNKNOWN_TYPE = "any"

_JSDOC_SCALARS = {
    "string": "String",
    "number": "float",
    "integer": "int",
    "int": "int",
    "boolean": "boolean",
    "bool": "boolean",
    "object": "Object",
    "void": "void",
    "undefined": "void",
    "null": "void",
    "array": "List",
    "map": "Map",
    "set": "Set",
    "date": "Date",
    "regexp": "RegExp",
    "function": "Function",
}
_JSDOC_UNKNOWN = {"*", "any", "?", ""}
_BUILTIN_CONSTRUCTORS = {"Map": "Map", "Set": "Set", "Array": "List", "Date": "Date", "Object": "Object"}
_MANY_TYPES = {"List", "Set"}
_NUMERIC_TYPES = {"int", "float"}
_BOOLEAN_OPERATORS = {"==", "!=", "===", "!==", "<", ">", "<=", ">=", "instanceof", "in"}
_STRING_RETURNING_METHODS = {
    "toString", "join", "toUpperCase", "toLowerCase", "trim", "substring", "padStart", "padEnd",
    "repeat", "replace", "toFixed", "charAt",
}
_BOOLEAN_RETURNING_METHODS = {"includes", "has", "startsWith", "endsWith", "some", "every", "isArray"}
_LIST_RETURNING_METHODS = {"map", "filter", "split", "concat"}
_JSDOC_TAG = re.compile(r"@(param|arg|argument|returns?|type)\s*(?:\{([^}]*)\})?\s*(\[?[\w$.]+)?")
_IDENTIFIER = re.compile(r"[A-Za-z_$][\w$]*")

# Last resort for a parameter with no annotation, default or docs: its *name*. A parameter called
# `teacher` / `professors` is taken to be a Teacher / list of Professors when such a class exists,
# and a few ubiquitous names (`name`, `age`, `price`, `is_active`) get their obvious plain type.
_STRING_NAMES = frozenset({
    "name", "title", "brand", "label", "email", "description", "address", "city", "country",
    "color", "colour", "model", "text", "message", "username", "password", "surname", "isbn", "phone",
})
_INT_NAMES = frozenset({"age", "id", "count", "quantity", "year", "size", "number", "num", "index", "pages"})
_FLOAT_NAMES = frozenset({"price", "salary", "amount", "balance", "rate", "weight", "height", "cost"})
_BOOL_PREFIXES = frozenset({"is", "has", "can", "should"})
_NAME_WORDS = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+")


def _singular(word: str) -> str:
    if word.endswith("ies") and len(word) > 3:
        return word[:-3] + "y"
    if word.endswith("es") and len(word) > 3:
        return word[:-2]
    if word.endswith("s") and len(word) > 2:
        return word[:-1]
    return word


def _name_hint_type(name: str, class_names: set[str]) -> str | None:
    """The type a parameter's *name* suggests (see the note above), else None."""
    words = [w.lower() for w in _NAME_WORDS.findall(name)]
    if not words:
        return None
    last = words[-1]
    by_lower = {c.lower(): c for c in class_names}
    if last in by_lower:
        return by_lower[last]
    if _singular(last) in by_lower:
        return f"List[{by_lower[_singular(last)]}]"
    if words[0] in _BOOL_PREFIXES and len(words) > 1:
        return "boolean"
    if last in _STRING_NAMES:
        return "String"
    if last in _INT_NAMES:
        return "int"
    if last in _FLOAT_NAMES:
        return "float"
    return None



@dataclass
class _RelEdge:
    source_id: str
    dest_id: str
    type: RelationshipType
    many: bool = False


@dataclass
class _Held:
    """A relationship derived from an attribute: how the owner came to hold the target."""

    target: str
    created: bool
    many: bool


@dataclass
class _DocTags:
    params: dict[str, str]
    returns: str | None
    type: str | None


_NO_TAGS = _DocTags({}, None, None)


def _parse_tree(source: str) -> Any:
    """Script grammar first; ES-module syntax (import/export) as a fallback."""
    try:
        return esprima.parseScript(source, {"comment": True, "range": True})
    except EsprimaError as script_error:
        try:
            return esprima.parseModule(source, {"comment": True, "range": True})
        except EsprimaError:
            raise ValueError(f"Invalid JavaScript source: {script_error}") from script_error


def _top_level_classes(tree: Any) -> list[Any]:
    """Top-level `class Foo {}` declarations, including `export class` / `export default class`.
    Classes assigned via an expression and nested/local classes are not visited, matching
    the Python/Java parsers' "top-level named class only" scope."""
    classes: list[Any] = []
    for node in tree.body:
        declaration = node
        if node.type in ("ExportNamedDeclaration", "ExportDefaultDeclaration"):
            declaration = node.declaration
        if declaration is not None and declaration.type == "ClassDeclaration" and declaration.id:
            classes.append(declaration)
    return classes


def parse(source: str) -> UmlDocument:
    """Reverse-engineer JavaScript source into a Unified UML JSON document."""
    tree = _parse_tree(source)
    class_defs = _top_level_classes(tree)
    class_ids = {node.id.name: f"class_{i}" for i, node in enumerate(class_defs, start=1)}
    docs = _JsDocs(source, list(tree.comments or []))

    classes: list[UmlClass] = []
    edges: list[_RelEdge] = []
    for index, node in enumerate(class_defs):
        uml_class, class_edges = _build_class(node, class_ids[node.id.name], index, class_ids, docs)
        classes.append(uml_class)
        edges.extend(class_edges)

    return UmlDocument(classes=classes, relationships=_dedupe_and_number(edges))


# ---------------------------------------------------------------------------
# JSDoc -- `/** @param {Person} owner  @returns {number}  @type {string} */`
# ---------------------------------------------------------------------------


class _JsDocs:
    """Finds the JSDoc block directly in front of a node and reads its type tags."""

    def __init__(self, source: str, comments: list[Any]) -> None:
        self._source = source
        self._blocks = [
            (c.range[0], c.range[1], c.value) for c in comments
            if c.type == "Block" and c.value.startswith("*")
        ]

    def before(self, node: Any) -> _DocTags:
        start = node.range[0]
        for _, end, text in reversed(self._blocks):
            if end > start:
                continue
            if self._source[end:start].strip():
                return _NO_TAGS
            return self._tags(text)
        return _NO_TAGS

    @staticmethod
    def _tags(text: str) -> _DocTags:
        params: dict[str, str] = {}
        returns: str | None = None
        declared: str | None = None
        for match in _JSDOC_TAG.finditer(text):
            tag, raw_type, name = match.groups()
            if raw_type is None:
                continue
            neutral = _jsdoc_type(raw_type)
            if tag in ("param", "arg", "argument") and name:
                params[name.strip("[]").split(".")[0].split("=")[0]] = neutral
            elif tag in ("return", "returns"):
                returns = neutral
            elif tag == "type":
                declared = neutral
        return _DocTags(params, returns, declared)


def _jsdoc_type(raw: str) -> str:
    """A JSDoc type expression as the language-neutral vocabulary (unknown -> "any")."""
    text = raw.strip().lstrip("?!").strip()
    if text.endswith("="):
        text = text[:-1].strip()
    if text.startswith("..."):
        text = text[3:]
    if text.startswith("(") and text.endswith(")"):
        text = text[1:-1]
    if "|" in text and "<" not in text:
        parts = [p.strip() for p in text.split("|") if p.strip() not in ("null", "undefined")]
        text = parts[0] if len(parts) == 1 else "*"
    if text.endswith("[]"):
        return f"List[{_jsdoc_type(text[:-2])}]"
    generic = re.match(r"^([\w$.]+)\s*<(.*)>$", text)
    if generic:
        outer = _jsdoc_type(generic.group(1))
        inner = ", ".join(_jsdoc_type(part) for part in _split_generic(generic.group(2)))
        return f"{outer}[{inner}]"
    if text in _JSDOC_UNKNOWN:
        return _UNKNOWN_TYPE
    return _JSDOC_SCALARS.get(text.lower(), text)


def _split_generic(text: str) -> list[str]:
    parts, depth, current = [], 0, ""
    for char in text:
        if char == "<":
            depth += 1
        elif char == ">":
            depth -= 1
        if char == "," and depth == 0:
            parts.append(current)
            current = ""
        else:
            current += char
    return [*parts, current] if current.strip() else parts


def _class_names_in(datatype: str, known_classes: set[str]) -> set[str]:
    return {word for word in _IDENTIFIER.findall(datatype) if word in known_classes}


def _is_many(datatype: str) -> bool:
    return datatype.split("[", 1)[0].strip() in _MANY_TYPES


# ---------------------------------------------------------------------------
# Type inference from expressions
# ---------------------------------------------------------------------------


class _Scope:
    """What is known while reading one function: parameter types and the owner's field types."""

    def __init__(self, params: dict[str, str], fields: dict[str, str], known: set[str]) -> None:
        self.params = params
        self.fields = fields
        self.known = known


def _walk(node: Any, into_functions: bool = True) -> Iterator[Any]:
    """Every ESTree node under `node`, depth first (optionally not entering nested functions)."""
    if isinstance(node, list):
        for item in node:
            yield from _walk(item, into_functions)
        return
    if not hasattr(node, "type") or isinstance(node, str):
        return
    yield node
    if not into_functions and node.type in _FUNCTION_TYPES:
        return
    for value in vars(node).values():
        if isinstance(value, list) or hasattr(value, "type"):
            yield from _walk(value, into_functions)


_FUNCTION_TYPES = {"FunctionExpression", "FunctionDeclaration", "ArrowFunctionExpression"}


def _literal_type(node: Any) -> str | None:
    value = node.value
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        raw = str(getattr(node, "raw", value)).lower()
        is_float = isinstance(value, float) or (not raw.startswith("0x") and any(c in raw for c in ".e"))
        return "float" if is_float else "int"
    if isinstance(value, str) and getattr(node, "regex", None) is None:
        return "String"
    return None


def _infer_type(node: Any, scope: _Scope) -> str | None:
    """The provable type of an expression, or None when it cannot be known."""
    if node is None:
        return None
    kind = node.type
    if kind == "Literal":
        return "RegExp" if getattr(node, "regex", None) else _literal_type(node)
    if kind == "TemplateLiteral":
        return "String"
    if kind == "ArrayExpression":
        return _array_type(node, scope)
    if kind == "ObjectExpression":
        return "Object"
    if kind == "NewExpression":
        return _new_type(node)
    if kind == "Identifier":
        return scope.params.get(node.name)
    if kind == "MemberExpression":
        return _member_type(node, scope)
    if kind == "UnaryExpression":
        return _unary_type(node, scope)
    if kind == "BinaryExpression":
        return _binary_type(node, scope)
    if kind in ("LogicalExpression", "ConditionalExpression"):
        return _merge_types(node, scope)
    if kind == "CallExpression":
        return _call_type(node, scope)
    if kind == "AwaitExpression":
        return _infer_type(node.argument, scope)
    if kind in _FUNCTION_TYPES:
        return "Function"
    return None


def _new_type(node: Any) -> str | None:
    if node.callee.type != "Identifier":
        return None
    name: str = node.callee.name
    return _BUILTIN_CONSTRUCTORS.get(name, name)


def _array_type(node: Any, scope: _Scope) -> str:
    element_types = {_infer_type(e, scope) for e in node.elements if e is not None}
    if len(element_types) == 1 and None not in element_types:
        return f"List[{element_types.pop()}]"
    return "List"


def _member_type(node: Any, scope: _Scope) -> str | None:
    if node.computed:
        return None
    name = node.property.name
    if node.object.type == "ThisExpression":
        return scope.fields.get(name)
    if name == "length":
        return "int"
    return None


def _unary_type(node: Any, scope: _Scope) -> str | None:
    if node.operator == "!":
        return "boolean"
    if node.operator == "typeof":
        return "String"
    if node.operator in ("-", "+"):
        inner = _infer_type(node.argument, scope)
        return inner if inner in _NUMERIC_TYPES else None
    return None


def _binary_type(node: Any, scope: _Scope) -> str | None:
    if node.operator in _BOOLEAN_OPERATORS:
        return "boolean"
    left, right = _infer_type(node.left, scope), _infer_type(node.right, scope)
    if node.operator == "+" and "String" in (left, right):
        return "String"
    if left in _NUMERIC_TYPES and right in _NUMERIC_TYPES:
        both_int = left == right == "int"
        return "int" if both_int and node.operator not in ("/", "**") else "float"
    return None


def _merge_types(node: Any, scope: _Scope) -> str | None:
    branches = (
        [node.consequent, node.alternate] if node.type == "ConditionalExpression"
        else [node.left, node.right]
    )
    types = {_infer_type(b, scope) for b in branches}
    return types.pop() if len(types) == 1 else None


def _call_type(node: Any, scope: _Scope) -> str | None:
    callee = node.callee
    if callee.type == "Identifier":
        return {"String": "String", "Number": "float", "parseInt": "int", "parseFloat": "float",
                "Boolean": "boolean"}.get(callee.name)
    if callee.type != "MemberExpression" or callee.computed:
        return None
    method = callee.property.name
    if callee.object.type == "Identifier" and callee.object.name == "Math":
        return "float"
    if callee.object.type == "Identifier" and callee.object.name == "JSON" and method == "stringify":
        return "String"
    if method in _STRING_RETURNING_METHODS:
        return "String"
    if method in _BOOLEAN_RETURNING_METHODS:
        return "boolean"
    if method in _LIST_RETURNING_METHODS:
        return "List"
    return None


def _local_types(nodes: list[Any], scope: _Scope) -> dict[str, str]:
    """`const x = new Loan()` -> x: Loan, for a name only ever declared with one provable type."""
    found: dict[str, set[str | None]] = {}
    for node in nodes:
        if node.type == "VariableDeclarator" and node.id.type == "Identifier":
            found.setdefault(node.id.name, set()).add(_infer_type(node.init, scope))
    return {n: types.pop() for n, types in found.items() if len(types) == 1 and None not in types}  # type: ignore[misc]


def _return_type(function: Any, scope: _Scope, declared: str | None) -> str:
    """JSDoc `@returns` wins; otherwise what every `return` statement provably yields."""
    if declared is not None:
        return declared
    nodes = list(_walk(function.body, into_functions=False))
    scope = _Scope({**_local_types(nodes, scope), **scope.params}, scope.fields, scope.known)
    returns = [n for n in nodes if n.type == "ReturnStatement"]
    values = [r.argument for r in returns if r.argument is not None]
    if not values:
        return "void"
    types = {_infer_type(v, scope) for v in values}
    if len(types) == 1 and None not in types:
        return types.pop() or _UNKNOWN_TYPE
    return _UNKNOWN_TYPE


# ---------------------------------------------------------------------------
# Class assembly
# ---------------------------------------------------------------------------


def _members(node: Any) -> list[Any]:
    return [m for m in node.body.body if m.type == "MethodDefinition"]


def _member_name(member: Any) -> str | None:
    key = member.key
    if key.type == "Identifier":
        return str(key.name)
    if key.type == "Literal" and isinstance(key.value, str) and _IDENTIFIER.fullmatch(key.value):
        return key.value
    return None


def _param_types(function: Any, tags: _DocTags, known: set[str]) -> dict[str, str]:
    """Parameter name -> type: JSDoc first, else the type of its default value, else (last
    resort) what its name suggests."""
    types: dict[str, str] = {}
    scope = _Scope({}, {}, set())
    for param in function.params:
        if param.type == "AssignmentPattern" and param.left.type == "Identifier":
            name, default = param.left.name, _infer_type(param.right, scope)
        elif param.type == "Identifier":
            name, default = param.name, None
        elif param.type == "RestElement" and param.argument.type == "Identifier":
            name, default = param.argument.name, "List"
        else:
            continue
        found = tags.params.get(name) or default
        if not found or found == _UNKNOWN_TYPE:
            found = _name_hint_type(name, known)
        if found and found != _UNKNOWN_TYPE:
            types[name] = found
    return types


def _build_class(
    node: Any, class_id: str, index: int, class_ids: dict[str, str], docs: _JsDocs
) -> tuple[UmlClass, list[_RelEdge]]:
    known = set(class_ids)
    name = node.id.name
    members = _members(node)
    attrs, held = _instance_attributes(members, known, docs)
    owned = {h.target for h in held}
    field_types = {a.name: a.datatype for a in attrs if a.datatype != _UNKNOWN_TYPE}

    methods: list[Method] = []
    uses: set[str] = set()
    for member in members:
        member_name = _member_name(member)
        if member_name is None:
            continue
        tags = docs.before(member)
        function = member.value
        scope = _Scope(_param_types(function, tags, known), field_types, known)
        uses |= _referenced_classes(function, scope, tags, known)
        if member.kind == "constructor":
            continue
        methods.append(_build_method(member, member_name, function, scope, tags))

    edges = [
        _RelEdge(class_id, class_ids[h.target], _held_type(h), h.many)
        for h in held if h.target != name
    ]
    uses -= owned | {name}
    edges += [_RelEdge(class_id, class_ids[t], RelationshipType.DEPENDENCY) for t in sorted(uses)]

    super_class = node.superClass
    if super_class is not None and super_class.type == "Identifier" and super_class.name in known:
        edges.append(_RelEdge(class_id, class_ids[super_class.name], RelationshipType.INHERITANCE))

    position, size = _layout(index)
    uml_class = UmlClass(
        id=class_id, name=name, attributes=attrs, methods=methods, position=position, size=size
    )
    return uml_class, edges


def _held_type(held: _Held) -> RelationshipType:
    """Created by the owner -> composition; a held collection -> aggregation; a held single
    reference (passed in, not created) -> association."""
    if held.created:
        return RelationshipType.COMPOSITION
    return RelationshipType.AGGREGATION if held.many else RelationshipType.ASSOCIATION


def _referenced_classes(function: Any, scope: _Scope, tags: _DocTags, known: set[str]) -> set[str]:
    """Known classes a function visibly uses: `new X()`, `X.call()`, or a JSDoc type naming X."""
    used: set[str] = set()
    for text in [*tags.params.values(), tags.returns or ""]:
        used |= _class_names_in(text, known)
    for param_type in scope.params.values():
        used |= _class_names_in(param_type, known)
    for sub in _walk(function.body):
        if sub.type == "NewExpression" and sub.callee.type == "Identifier":
            used |= {sub.callee.name} & known
        elif sub.type == "MemberExpression" and sub.object.type == "Identifier":
            used |= {sub.object.name} & known
    return used


def _instance_attributes(
    members: list[Any], known: set[str], docs: _JsDocs
) -> tuple[list[Attribute], list[_Held]]:
    """`this.x = ...` state. The constructor is read first (so its type wins), then every other
    method; `this.list.push(new X())` upgrades an attribute to a held collection of X."""
    ordered = sorted(members, key=lambda m: m.kind != "constructor")
    attrs: dict[str, Attribute] = {}
    held: dict[str, _Held] = {}

    for member in ordered:
        function = member.value
        scope = _Scope(_param_types(function, docs.before(member), known), {}, known)
        for stmt in _one_level(function.body.body):
            name, value = _this_assignment_parts(stmt)
            if name is None or name in attrs:
                continue
            datatype, relation = _attribute_type(value, docs.before(stmt), scope, known)
            attrs[name] = Attribute(
                name=name,
                datatype=datatype,
                visibility=_visibility_from_name(name),
                default_value=_literal_to_str(value),
                static=False,
                final=False,
            )
            if relation is not None:
                held[name] = relation
    _apply_collection_additions(members, attrs, held, known)
    return list(attrs.values()), list(held.values())


def _attribute_type(
    value: Any, tags: _DocTags, scope: _Scope, known: set[str]
) -> tuple[str, _Held | None]:
    created = value is not None and _creates_instances(value, known)
    datatype = tags.type or _infer_type(value, scope) or _UNKNOWN_TYPE
    targets = _class_names_in(datatype, known)
    if len(targets) != 1:
        return datatype, None
    return datatype, _Held(next(iter(targets)), created, _is_many(datatype))


def _creates_instances(value: Any, known: set[str]) -> bool:
    """`new Known()`, or an array literal made only of them."""
    if value.type == "NewExpression":
        return value.callee.type == "Identifier" and value.callee.name in known
    if value.type == "ArrayExpression" and value.elements:
        return all(e is not None and _creates_instances(e, known) for e in value.elements)
    return False


def _apply_collection_additions(
    members: list[Any], attrs: dict[str, Attribute], held: dict[str, _Held], known: set[str]
) -> None:
    """`this.items.push(new Item())` (or a local assigned `new Item()`) -> `items` holds many
    Items, created by the owner."""
    for member in members:
        created_locals = _locals_created_from_new(member.value.body, known)
        for call in _walk(member.value.body):
            target = _push_target(call)
            if target is None:
                continue
            field, argument = target
            if argument.type == "Identifier" and argument.name in created_locals:
                argument = created_locals[argument.name]
            if field not in attrs or field in held or not _creates_instances(argument, known):
                continue
            item = argument.callee.name
            attrs[field] = attrs[field].model_copy(update={"datatype": f"List[{item}]"})
            held[field] = _Held(item, created=True, many=True)


def _locals_created_from_new(body: Any, known: set[str]) -> dict[str, Any]:
    """`const item = new Known(...)` declarations in a function body, by variable name."""
    created: dict[str, Any] = {}
    for node in _walk(body, into_functions=False):
        if node.type != "VariableDeclarator" or node.id.type != "Identifier":
            continue
        if node.init is not None and node.init.type == "NewExpression" and _creates_instances(node.init, known):
            created[node.id.name] = node.init
    return created


def _push_target(node: Any) -> tuple[str, Any] | None:
    if node.type != "CallExpression" or len(node.arguments) != 1:
        return None
    callee = node.callee
    if callee.type != "MemberExpression" or callee.computed or callee.property.name not in ("push", "add"):
        return None
    owner = callee.object
    if owner.type != "MemberExpression" or owner.computed or owner.object.type != "ThisExpression":
        return None
    return owner.property.name, node.arguments[0]


def _one_level(body: list[Any]) -> list[Any]:
    """Statements plus one level into if/for/while/try blocks (never nested functions)."""
    result: list[Any] = []
    for stmt in body:
        result.append(stmt)
        blocks: list[Any] = []
        if stmt.type == "IfStatement":
            blocks = [stmt.consequent, stmt.alternate]
        elif stmt.type in ("ForStatement", "WhileStatement", "ForInStatement", "ForOfStatement"):
            blocks = [stmt.body]
        elif stmt.type == "TryStatement":
            blocks = [stmt.block, stmt.finalizer, stmt.handler.body if stmt.handler else None]
        for block in blocks:
            if block is not None and block.type == "BlockStatement":
                result.extend(block.body)
            elif block is not None:
                result.append(block)
    return result


def _this_assignment_parts(stmt: Any) -> tuple[str | None, Any]:
    """(field name, RHS value node) for a `this.field = ...` statement, else (None, None)."""
    if stmt.type != "ExpressionStatement" or stmt.expression.type != "AssignmentExpression":
        return None, None
    left = stmt.expression.left
    if left.type != "MemberExpression" or left.computed or left.object.type != "ThisExpression":
        return None, None
    if stmt.expression.operator != "=":
        return None, None
    return left.property.name, stmt.expression.right


def _literal_to_str(node: Any) -> str | None:
    if node is not None and node.type == "Literal" and not getattr(node, "regex", None):
        return str(node.value)
    return None  # non-literal RHS -- a provable type may still exist, but not a provable default


# ---------------------------------------------------------------------------
# Methods
# ---------------------------------------------------------------------------


def _build_method(member: Any, name: str, function: Any, scope: _Scope, tags: _DocTags) -> Method:
    params = [
        Parameter(name=param, datatype=scope.params.get(param, _UNKNOWN_TYPE))
        for param in _param_names(function.params)
    ]
    return Method(
        name=name,
        visibility=_visibility_from_name(name),
        parameters=params,
        return_type=_return_type(function, scope, tags.returns),
        static=member.static,
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
    many_by_key: dict[tuple[str, str, RelationshipType], bool] = {}
    for e in edges:
        key = (e.source_id, e.dest_id, e.type)
        many_by_key[key] = many_by_key.get(key, False) or e.many

    return [
        Relationship(
            id=f"rel_{i}",
            source=source_id,
            destination=dest_id,
            type=rel_type,
            multiplicity=Multiplicity(source="1", destination="*" if many else "1"),
            label="",
        )
        for i, ((source_id, dest_id, rel_type), many) in enumerate(many_by_key.items(), start=1)
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


def list_methods(source: str) -> list[tuple[str, str]]:
    """(class name, method name) for every non-constructor method of every top-level class."""
    methods: list[tuple[str, str]] = []
    for node in _top_level_classes(_parse_tree(source)):
        for member in node.body.body:
            name = _member_name(member) if member.type == "MethodDefinition" else None
            if name and member.kind != "constructor" and (node.id.name, name) not in methods:
                methods.append((node.id.name, name))
    return methods


def extract_control_flow(source: str, class_name: str, method_name: str) -> ActivityDocument:
    """Reverse-engineer one method's control flow into an ActivityDocument."""
    class_node = next((n for n in _top_level_classes(_parse_tree(source)) if n.id.name == class_name), None)
    if class_node is None:
        raise ValueError(f"Class '{class_name}' not found")

    method_node = next(
        (
            m
            for m in class_node.body.body
            if m.type == "MethodDefinition" and m.kind != "constructor" and _member_name(m) == method_name
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
        node_id = builder.add_node(ActivityNodeType.ACTION, _truncate(describe_steps(buffer)))
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

        elif node_type == "TryStatement":
            flush()
            handlers = [] if stmt.handler is None else [stmt.handler]
            current = _walk_try(
                _as_stmt_list(stmt.block),
                [_as_stmt_list(h.body) for h in handlers],
                _as_stmt_list(stmt.finalizer),
                current,
                builder,
                end_id,
            )

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


def _walk_try(
    body: list[Any],
    handlers: list[list[Any]],
    finalbody: list[Any],
    entry: _OpenTails,
    builder: _CfgBuilder,
    end_id: str,
) -> _OpenTails:
    """try/catch/finally as branches: a decision splits the exception path (the catch block)
    from the normal path (the body); both merge into a `finally` node. JavaScript has a single
    untyped catch, so there is no handler chain. A `return` inside the try still goes straight
    to END, bypassing the finally."""
    handler_tails: _OpenTails = []
    normal_entry = entry

    if handlers:
        root_id = builder.add_node(ActivityNodeType.DECISION, "exception thrown?")
        for src_id, edge_label in entry:
            builder.add_edge(src_id, root_id, edge_label)
        normal_entry = [(root_id, "no")]
        handler_tails = _walk_block(handlers[0], [(root_id, "yes")], builder, end_id)

    merged = _walk_block(body, normal_entry, builder, end_id) + handler_tails

    if not finalbody or not merged:
        return merged
    finally_id = builder.add_node(ActivityNodeType.ACTION, "finally")
    for src_id, edge_label in merged:
        builder.add_edge(src_id, finally_id, edge_label)
    return _walk_block(finalbody, [(finally_id, "")], builder, end_id)


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
