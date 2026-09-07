from __future__ import annotations

from backend.schemas.uml import (
    Attribute,
    Method,
    Relationship,
    RelationshipType,
    UmlDocument,
    Visibility,
)

_VISIBILITY_SYMBOLS: dict[Visibility, str] = {
    Visibility.PUBLIC: "+",
    Visibility.PRIVATE: "-",
    Visibility.PROTECTED: "#",
    Visibility.PACKAGE: "~",
}

# Mermaid classDiagram edge tokens. The "whole" end of a composition/
# aggregation always carries the diamond, matching this schema's convention
# of `source` being the owning ("whole") class for both relationship types.
_RELATIONSHIP_ARROWS: dict[RelationshipType, str] = {
    RelationshipType.INHERITANCE: "--|>",
    RelationshipType.COMPOSITION: "*--",
    RelationshipType.AGGREGATION: "o--",
    RelationshipType.ASSOCIATION: "-->",
    RelationshipType.DEPENDENCY: "..>",
}

# Multiplicity is only meaningful (and only conventionally drawn) on
# association/aggregation/composition edges -- a generalization or dependency
# arrow isn't quantified in standard UML, even though the schema always
# carries a Multiplicity value for every relationship type.
_MULTIPLICITY_RELEVANT = {
    RelationshipType.ASSOCIATION,
    RelationshipType.AGGREGATION,
    RelationshipType.COMPOSITION,
}


def document_to_class_diagram(document: UmlDocument) -> str:
    """Pure transformation: UmlDocument -> Mermaid `classDiagram` syntax."""
    class_names = {cls.id: cls.name for cls in document.classes}

    lines = ["classDiagram"]
    for cls in document.classes:
        lines.append(f"    class {cls.name} {{")
        lines.extend(f"        {_render_attribute(attr)}" for attr in cls.attributes)
        lines.extend(f"        {_render_method(method)}" for method in cls.methods)
        lines.append("    }")

    for rel in document.relationships:
        lines.append(f"    {_render_relationship(rel, class_names)}")

    return "\n".join(lines)


def _render_attribute(attr: Attribute) -> str:
    symbol = _VISIBILITY_SYMBOLS[attr.visibility]
    suffix = "$" if attr.static else ""  # Mermaid's static-member marker
    return f"{symbol}{attr.datatype} {attr.name}{suffix}"


def _render_method(method: Method) -> str:
    symbol = _VISIBILITY_SYMBOLS[method.visibility]
    params = ", ".join(f"{p.name}: {p.datatype}" for p in method.parameters)
    suffix = "$" if method.static else ("*" if method.abstract else "")  # static / abstract markers
    return f"{symbol}{method.name}({params}) {method.return_type}{suffix}"


def _render_relationship(rel: Relationship, class_names: dict[str, str]) -> str:
    source = class_names[rel.source]
    destination = class_names[rel.destination]
    arrow = _RELATIONSHIP_ARROWS[rel.type]
    label = f" : {rel.label}" if rel.label else ""
    if rel.type in _MULTIPLICITY_RELEVANT:
        return f'{source} "{rel.multiplicity.source}" {arrow} "{rel.multiplicity.destination}" {destination}{label}'
    return f"{source} {arrow} {destination}{label}"
