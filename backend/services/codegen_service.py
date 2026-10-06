from __future__ import annotations

import textwrap
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import jinja2

from backend.generator import registry as reg
from backend.generator.class_description import (
    AttributeDescription,
    ClassDescription,
    CollaboratorDescription,
    MethodDescription,
)
from backend.generator.registry import LanguageConfig
from backend.schemas.uml import (
    Attribute,
    ClassKind,
    Method,
    RelationshipType,
    UmlClass,
    UmlDocument,
)

TEMPLATES_ROOT = Path(__file__).parent.parent / "generator" / "templates"


# ---------------------------------------------------------------------------
# Context dataclasses passed to templates
# ---------------------------------------------------------------------------


@dataclass
class AttrContext:
    name: str
    prefixed_name: str
    type: str
    default_value: str | None
    static: bool
    final: bool
    visibility_keyword: str


@dataclass
class MethodContext:
    name: str
    prefixed_name: str
    return_type: str
    params: list[str]
    static: bool
    abstract: bool
    visibility_keyword: str
    body_lines: list[str]


@dataclass
class ImportContext:
    module: str
    name: str


@dataclass
class RelationshipFieldContext:
    """A field derived from an AGGREGATION/COMPOSITION edge rather than an
    explicitly-declared Attribute: source = the "whole" class that gets the
    field, destination = the "part" class the field references. Per
    CLAUDE.md's Template Design rule, this structural decision (does the edge
    imply a field, and what type) is resolved here, not in the template."""

    part_class_name: str
    many: bool


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _map_type(datatype: str, type_map: dict[str, str]) -> str:
    return type_map.get(datatype, datatype)


def _build_attr_context(attr: Attribute, config: LanguageConfig, class_names: set[str]) -> AttrContext:
    mapped_type = _map_type(attr.datatype, config.type_map)
    prefix = config.visibility_prefix.get(attr.visibility.value, "")
    keyword = config.visibility_keyword.get(attr.visibility.value, "")
    return AttrContext(
        name=attr.name,
        prefixed_name=prefix + attr.name,
        type=mapped_type,
        default_value=attr.default_value,
        static=attr.static,
        final=attr.final,
        visibility_keyword=keyword,
    )


TAB_AS_SPACES = "    "
MAX_COLLABORATOR_METHODS = 10


def _normalize_body_lines(body: str | None) -> list[str] | None:
    """A supplied method body as clean, unindented lines, or None when it has no content."""
    if body is None:
        return None
    lines = [line.rstrip() for line in textwrap.dedent(body.replace("\t", TAB_AS_SPACES)).split("\n")]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return lines or None


def _build_method_context(
    method: Method,
    config: LanguageConfig,
    lang: str,
    body: str | None = None,
    force_abstract: bool = False,
) -> MethodContext:
    mapped_return = _map_type(method.return_type, config.type_map)
    keyword = config.visibility_keyword.get(method.visibility.value, "")

    params: list[str] = []
    for p in method.parameters:
        mapped_param_type = _map_type(p.datatype, config.type_map)
        if lang == "python":
            params.append(f"{p.name}: {mapped_param_type}")
        elif lang == "java":
            params.append(f"{mapped_param_type} {p.name}")
        else:
            params.append(p.name)

    prefix = config.visibility_prefix.get(method.visibility.value, "")
    abstract = method.abstract or force_abstract
    supplied = None if abstract else _normalize_body_lines(body)
    return MethodContext(
        name=method.name,
        prefixed_name=prefix + method.name,
        return_type=mapped_return,
        params=params,
        static=method.static,
        abstract=abstract,
        visibility_keyword=keyword,
        body_lines=supplied if supplied is not None else list(config.stub_body_lines),
    )


def _collect_class_imports(cls: UmlClass, config: LanguageConfig, class_names: set[str]) -> set[str]:
    refs: set[str] = set()
    for attr in cls.attributes:
        if attr.datatype in class_names and attr.datatype != cls.name:
            refs.add(attr.datatype)
    for method in cls.methods:
        if method.return_type in class_names and method.return_type != cls.name:
            refs.add(method.return_type)
        for param in method.parameters:
            if param.datatype in class_names and param.datatype != cls.name:
                refs.add(param.datatype)
    return refs


def _collect_stdlib_imports(
    cls: UmlClass,
    config: LanguageConfig,
    lang: str,
) -> list[ImportContext] | list[str]:
    if lang == "python":
        needed: set[str] = set()
        all_types = [attr.datatype for attr in cls.attributes] + [m.return_type for m in cls.methods]
        for p in [p for m in cls.methods for p in m.parameters]:
            all_types.append(p.datatype)
        for t in all_types:
            mapped = _map_type(t, config.type_map)
            if mapped == "UUID":
                needed.add("uuid")
            elif mapped == "date" or mapped == "datetime":
                needed.add("datetime")
        result = []
        for mod in needed:
            if mod == "uuid":
                result.append(ImportContext(module="uuid", name="UUID"))
            elif mod == "datetime":
                result.append(ImportContext(module="datetime", name="datetime"))
        return result

    if lang == "java":
        needed_java: set[str] = set()
        all_mapped = []
        for attr in cls.attributes:
            all_mapped.append(_map_type(attr.datatype, config.type_map))
        for method in cls.methods:
            all_mapped.append(_map_type(method.return_type, config.type_map))
            for p in method.parameters:
                all_mapped.append(_map_type(p.datatype, config.type_map))
        for mapped in all_mapped:
            if mapped in config.standard_imports:
                needed_java.add(config.standard_imports[mapped])
        return sorted(needed_java)

    return []


# Both mean "is a kind of" to generated code: `extends`, or `implements` for an interface.
_SUBTYPE_EDGES = (RelationshipType.INHERITANCE, RelationshipType.REALIZATION)


def _find_parents(
    cls: UmlClass, document: UmlDocument, class_map: dict[str, UmlClass]
) -> tuple[str | None, list[str]]:
    """(parent class, interfaces) from the INHERITANCE edges leaving `cls`.

    An edge to an interface is an implementation (or, from an interface, an
    extension), so only the first edge to a non-interface becomes the parent class;
    an interface has no parent class at all, only the interfaces it extends."""
    parent: str | None = None
    interfaces: list[str] = []
    for rel in document.relationships:
        if rel.type not in _SUBTYPE_EDGES or rel.source != cls.id:
            continue
        target = class_map.get(rel.destination)
        if target is None:
            continue
        if target.kind == ClassKind.INTERFACE or cls.kind == ClassKind.INTERFACE:
            interfaces.append(target.name)
        elif parent is None:
            parent = target.name
    return parent, interfaces


def _inherited_obligations(
    cls: UmlClass, document: UmlDocument, class_map: dict[str, UmlClass]
) -> list[Method]:
    """Methods `cls` must define but does not: every method of an interface it
    implements and every abstract method of an abstract parent, up the chain,
    unless it declares one of that name itself (an abstract class may leave them)."""
    if cls.kind == ClassKind.ABSTRACT:
        return []
    have = {m.name for m in cls.methods}
    missing: list[Method] = []
    seen: set[str] = set()
    pending = [cls]
    while pending:
        current = pending.pop()
        for rel in document.relationships:
            if rel.type not in _SUBTYPE_EDGES or rel.source != current.id:
                continue
            target = class_map.get(rel.destination)
            if target is None or target.id in seen:
                continue
            seen.add(target.id)
            promised = [
                m for m in target.methods if target.kind == ClassKind.INTERFACE or m.abstract
            ]
            for method in promised:
                if method.name not in have:
                    have.add(method.name)
                    missing.append(method.model_copy(update={"abstract": False}))
            pending.append(target)
    return missing


_RELATIONSHIP_FIELD_TYPES = (RelationshipType.AGGREGATION, RelationshipType.COMPOSITION)


def _is_many(multiplicity_value: str) -> bool:
    return "*" in multiplicity_value


def _pluralize(name: str) -> str:
    if name.endswith(("s", "x", "z", "ch", "sh")):
        return name + "es"
    if len(name) > 1 and name.endswith("y") and name[-2] not in "aeiou":
        return name[:-1] + "ies"
    return name + "s"


def _decapitalize(name: str) -> str:
    return name[0].lower() + name[1:] if name else name


def _find_relationship_fields(
    cls: UmlClass, document: UmlDocument, class_map: dict[str, UmlClass]
) -> list[RelationshipFieldContext]:
    """AGGREGATION/COMPOSITION edges where `cls` is the "whole" (source) each
    imply a field referencing the "part" (destination) class."""
    fields = []
    for rel in document.relationships:
        if rel.type not in _RELATIONSHIP_FIELD_TYPES or rel.source != cls.id:
            continue
        part_cls = class_map.get(rel.destination)
        if part_cls is None:
            continue
        fields.append(
            RelationshipFieldContext(
                part_class_name=part_cls.name,
                many=_is_many(rel.multiplicity.destination),
            )
        )
    return fields


def _build_relationship_attr_context(
    field: RelationshipFieldContext, config: LanguageConfig, lang: str
) -> AttrContext:
    name = _pluralize(_decapitalize(field.part_class_name)) if field.many else _decapitalize(field.part_class_name)

    if lang == "python":
        field_type = f"list[{field.part_class_name}]" if field.many else field.part_class_name
        default_value = "[]" if field.many else None
    elif lang == "java":
        field_type = f"List<{field.part_class_name}>" if field.many else field.part_class_name
        default_value = "new ArrayList<>()" if field.many else None
    else:  # javascript is untyped; `type` is unused by its template
        field_type = field.part_class_name
        default_value = "[]" if field.many else None

    return AttrContext(
        name=name,
        prefixed_name=config.visibility_prefix.get("private", "") + name,
        type=field_type,
        default_value=default_value,
        static=False,
        final=False,
        visibility_keyword=config.visibility_keyword.get("private", ""),
    )


def _build_template_context(
    cls: UmlClass,
    document: UmlDocument,
    class_map: dict[str, UmlClass],
    config: LanguageConfig,
    lang: str,
    bodies: Mapping[int, str] | None = None,
) -> dict:
    class_names = {c.name for c in document.classes}
    parent, interfaces = _find_parents(cls, document, class_map)
    is_interface = cls.kind == ClassKind.INTERFACE
    has_abstract = is_interface or cls.kind == ClassKind.ABSTRACT or any(m.abstract for m in cls.methods)

    attrs = [_build_attr_context(a, config, class_names) for a in cls.attributes]
    existing_attr_names = {a.name for a in attrs}

    relationship_fields = _find_relationship_fields(cls, document, class_map)
    relationship_class_names: set[str] = set()
    for field in relationship_fields:
        attr_ctx = _build_relationship_attr_context(field, config, lang)
        if attr_ctx.name in existing_attr_names:
            continue  # an explicitly-declared attribute already owns this name
        existing_attr_names.add(attr_ctx.name)
        attrs.append(attr_ctx)
        if field.part_class_name != cls.name:
            relationship_class_names.add(field.part_class_name)

    static_attributes = [a for a in attrs if a.static]
    instance_attributes = [a for a in attrs if not a.static]
    bodies = bodies or {}
    methods = [
        _build_method_context(m, config, lang, bodies.get(index), force_abstract=is_interface)
        for index, m in enumerate(cls.methods)
    ]
    if cls.kind != ClassKind.INTERFACE:
        # A concrete class must define what its interfaces and abstract parents promise.
        methods += [
            _build_method_context(m, config, lang, force_abstract=cls.kind == ClassKind.ABSTRACT)
            for m in _inherited_obligations(cls, document, class_map)
        ]

    # Java resolves a same-package base type without an import; JavaScript has no
    # interfaces to inherit from, so only its parent class is imported.
    inherited_class_names: set[str] = set()
    if lang != "java":
        inherited_class_names = {parent} if parent else set()
    if lang == "python":
        inherited_class_names |= set(interfaces)
    # Generated Java files share one (default) package, where `import Foo;` is an error.
    class_imports = [] if lang == "java" else sorted(
        _collect_class_imports(cls, config, class_names)
        | relationship_class_names
        | inherited_class_names
    )
    stdlib_imports = _collect_stdlib_imports(cls, config, lang)
    if lang == "java" and any(f.many for f in relationship_fields):
        stdlib_imports = sorted(set(stdlib_imports) | {"java.util.List", "java.util.ArrayList"})

    return {
        "class_name": cls.name,
        "parent": parent,
        "interfaces": interfaces,
        "bases": ([parent] if parent else []) + interfaces,
        "is_interface": is_interface,
        "forbid_instantiation": is_interface or cls.kind == ClassKind.ABSTRACT,
        "has_abstract": has_abstract,
        "attributes": attrs,
        "static_attributes": static_attributes,
        "instance_attributes": instance_attributes,
        "methods": methods,
        "class_imports": class_imports,
        "stdlib_imports": stdlib_imports,
        "package": None,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_code(
    document: UmlDocument,
    language: str,
    implementations: Mapping[tuple[str, int], str] | None = None,
    class_ids: set[str] | None = None,
) -> dict[str, str]:
    """Render one source file per class.

    `implementations` optionally maps (class id, index in that class's methods) to a method
    body; a method without one keeps the language's stub. `class_ids` restricts the output to
    those classes (used to check a single class on its own)."""
    if language not in reg.REGISTRY:
        raise ValueError(f"Unsupported language: '{language}'. Supported: {reg.SUPPORTED_LANGUAGES}")

    config = reg.REGISTRY[language]
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATES_ROOT / config.template_dir)),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    template = env.get_template("class.j2")

    class_map = {cls.id: cls for cls in document.classes}
    files: dict[str, str] = {}

    for cls in document.classes:
        if class_ids is not None and cls.id not in class_ids:
            continue
        bodies = {
            index: body for (cid, index), body in (implementations or {}).items() if cid == cls.id
        }
        context = _build_template_context(cls, document, class_map, config, language, bodies)
        content = template.render(**context)
        filename = cls.name + config.file_extension
        files[filename] = content

    return files


# ---------------------------------------------------------------------------
# Class descriptions (input for the optional LLM method implementation)
# ---------------------------------------------------------------------------


def _member_access(language: str, class_name: str, name: str, static: bool) -> str:
    owner = class_name if static else ("self" if language == "python" else "this")
    return f"{owner}.{name}"


def _method_signature(method: MethodContext, language: str) -> str:
    params = ", ".join(method.params)
    if language == "python":
        self_part = [] if method.static else ["self"]
        return f"def {method.prefixed_name}({', '.join(self_part + method.params)}) -> {method.return_type}"
    if language == "java":
        modifiers = " ".join(
            part for part in (method.visibility_keyword, "static" if method.static else "") if part
        )
        return f"{modifiers} {method.return_type} {method.name}({params})".strip()
    return f"{'static ' if method.static else ''}{method.prefixed_name}({params})"


def _method_keys(methods: list[Method], class_name: str) -> list[str]:
    seen: dict[str, int] = {}
    keys: list[str] = []
    for method in methods:
        seen[method.name] = seen.get(method.name, 0) + 1
        suffix = "" if seen[method.name] == 1 else f"#{seen[method.name]}"
        keys.append(f"{class_name}.{method.name}{suffix}")
    return keys


def _collaborators(
    cls: UmlClass,
    document: UmlDocument,
    class_map: dict[str, UmlClass],
    config: LanguageConfig,
    language: str,
) -> list[CollaboratorDescription]:
    collaborators: list[CollaboratorDescription] = []
    for rel in document.relationships:
        if rel.source == cls.id:
            other, role = class_map[rel.destination], "this class uses, owns or extends it"
        elif rel.destination == cls.id:
            other, role = class_map[rel.source], "it uses, owns or extends this class"
        else:
            continue
        public_methods = [
            _method_signature(_build_method_context(m, config, language), language)
            for m in other.methods
            if m.visibility.value == "public"
        ][:MAX_COLLABORATOR_METHODS]
        collaborators.append(
            CollaboratorDescription(
                kind=rel.type.value, role=role, class_name=other.name, methods=public_methods
            )
        )
    return collaborators


def describe_class(document: UmlDocument, class_id: str, language: str) -> ClassDescription:
    """Describe a class the way its generated scaffold names things, for a model that will
    write method bodies (signatures, how to reach attributes and sibling methods, collaborators)."""
    if language not in reg.REGISTRY:
        raise ValueError(f"Unsupported language: '{language}'. Supported: {reg.SUPPORTED_LANGUAGES}")
    class_map = {c.id: c for c in document.classes}
    if class_id not in class_map:
        raise ValueError(f"Class '{class_id}' not found")
    cls = class_map[class_id]
    config = reg.REGISTRY[language]

    context = _build_template_context(cls, document, class_map, config, language)
    attributes = [
        AttributeDescription(
            name=attr.name,
            type=attr.type,
            access=_member_access(
                language,
                cls.name,
                attr.name if language == "java" else attr.prefixed_name,
                attr.static,
            ),
            static=attr.static,
            final=attr.final,
        )
        for attr in context["attributes"]
    ]
    keys = _method_keys(cls.methods, cls.name)
    methods = [
        MethodDescription(
            index=index,
            key=keys[index],
            name=method.name,
            signature=_method_signature(method, language),
            access=_member_access(
                language,
                cls.name,
                method.name if language == "java" else method.prefixed_name,
                method.static,
            ),
            return_type=method.return_type,
            static=method.static,
            abstract=method.abstract,
        )
        for index, method in enumerate(context["methods"])
    ]
    return ClassDescription(
        class_name=cls.name,
        language=language,
        parent=context["parent"],
        attributes=attributes,
        methods=methods,
        collaborators=_collaborators(cls, document, class_map, config, language),
    )
