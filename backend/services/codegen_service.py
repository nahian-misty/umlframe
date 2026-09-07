from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import jinja2

from backend.generator import registry as reg
from backend.generator.registry import LanguageConfig
from backend.schemas.uml import Attribute, Method, RelationshipType, UmlClass, UmlDocument

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


def _build_method_context(method: Method, config: LanguageConfig, lang: str) -> MethodContext:
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
    return MethodContext(
        name=method.name,
        prefixed_name=prefix + method.name,
        return_type=mapped_return,
        params=params,
        static=method.static,
        abstract=method.abstract,
        visibility_keyword=keyword,
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
            elif mapped == "date":
                needed.add("datetime")
            elif mapped == "datetime":
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


def _find_parent(cls: UmlClass, document: UmlDocument, class_map: dict[str, UmlClass]) -> str | None:
    for rel in document.relationships:
        if rel.type == RelationshipType.INHERITANCE and rel.source == cls.id:
            parent_cls = class_map.get(rel.destination)
            if parent_cls:
                return parent_cls.name
    return None


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
) -> dict:
    class_names = {c.name for c in document.classes}
    parent = _find_parent(cls, document, class_map)
    has_abstract = any(m.abstract for m in cls.methods)

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
    methods = [_build_method_context(m, config, lang) for m in cls.methods]

    class_imports = sorted(_collect_class_imports(cls, config, class_names) | relationship_class_names)
    stdlib_imports = _collect_stdlib_imports(cls, config, lang)
    if lang == "java" and any(f.many for f in relationship_fields):
        stdlib_imports = sorted(set(stdlib_imports) | {"java.util.List", "java.util.ArrayList"})

    return {
        "class_name": cls.name,
        "parent": parent,
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


def generate_code(document: UmlDocument, language: str) -> dict[str, str]:
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
        context = _build_template_context(cls, document, class_map, config, language)
        content = template.render(**context)
        filename = cls.name + config.file_extension
        files[filename] = content

    return files
