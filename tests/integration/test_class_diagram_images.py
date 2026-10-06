"""Class-diagram images drawn in other tools (coloured headers, rounded corners,
JPEG artefacts, fan-in buses, dashed realisations) must come out as the diagram
says. Gated on tesseract: the OCR stage is real here."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from backend.schemas.uml import UmlDocument
from backend.services.image_service import image_to_document

pytestmark = pytest.mark.skipif(
    shutil.which("tesseract") is None, reason="tesseract-ocr binary not found"
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "class_diagrams"


def _document(name: str) -> UmlDocument:
    return image_to_document((FIXTURES / name).read_bytes())


def _class(document: UmlDocument, name: str):
    return next(c for c in document.classes if c.name == name)


def _edges(document: UmlDocument) -> set[tuple[str, str, str]]:
    names = {c.id: c.name for c in document.classes}
    return {(names[r.source], r.type.value, names[r.destination]) for r in document.relationships}


def test_arrows_with_open_heads_are_associations_pointing_at_the_head() -> None:
    document = _document("uml_1.jpg")

    assert sorted(c.name for c in document.classes) == ["Animal", "Dish", "Duck", "Zebra"]
    assert _edges(document) == {
        ("Duck", "association", "Animal"),
        ("Dish", "association", "Animal"),
        ("Zebra", "association", "Animal"),
    }
    duck = _class(document, "Duck")
    assert [(a.name, a.datatype, a.default_value) for a in duck.attributes] == [
        ("beakColr", "String", '"yellow"')
    ]
    assert [m.name for m in duck.methods] == ["swim", "quack"]


def test_private_marks_and_camel_case_survive_ocr() -> None:
    dish = _class(_document("uml_1.jpg"), "Dish")

    assert [(a.name, a.visibility.value) for a in dish.attributes] == [
        ("sizeInFt", "private"),
        ("canEat", "private"),
    ]
    assert [(m.name, m.visibility.value) for m in dish.methods] == [("swim", "private")]


def test_shared_inheritance_bus_gives_one_edge_per_child() -> None:
    document = _document("uml_2.png")

    assert _edges(document) == {
        ("Duck", "inheritance", "Animal"),
        ("Fish", "inheritance", "Animal"),
        ("Zebra", "inheritance", "Animal"),
    }
    animal = _class(document, "Animal")
    assert [m.name for m in animal.methods] == ["isMammal", "mate"]
    assert _class(document, "Zebra").methods[0].name == "run"


def test_coloured_rounded_boxes_are_read_and_the_diamond_marks_the_whole() -> None:
    document = _document("uml_3.png")

    assert sorted(c.name for c in document.classes) == ["Player", "Team"]
    assert _edges(document) == {("Player", "aggregation", "Team")}
    player = _class(document, "Player")
    assert [(a.name, a.datatype) for a in player.attributes] == [
        ("name", "string"),
        ("position", "string"),
        ("jerseyNumber", "int"),
    ]
    assert [m.name for m in player.methods] == ["playGame", "train"]


def test_hollow_triangles_are_inheritance_and_array_types_are_tidied() -> None:
    document = _document("uml_4.png")

    assert _edges(document) == {
        ("Book", "inheritance", "Document"),
        ("EMail", "inheritance", "Document"),
    }
    document_class = _class(document, "Document")
    assert [m.return_type for m in document_class.methods] == ["String[]", "void", "date"]
    assert _class(document, "EMail").attributes[1].datatype == "String[]"


def test_stereotype_marks_an_interface_and_dashed_triangles_realise_it() -> None:
    document = _document("uml_5.png")

    owner = _class(document, "Owner")
    assert owner.kind.value == "interface"
    assert [m.name for m in owner.methods] == ["acquire", "dispose"]
    assert _class(document, "Person").kind.value == "class"
    assert _edges(document) == {
        ("Person", "realization", "Owner"),
        ("Corporation", "realization", "Owner"),
    }


def test_mixed_diagram_kinds_relationships_and_multiplicities() -> None:
    document = _document("uml_6.png")

    assert _class(document, "Drawable").kind.value == "interface"  # realised, though italic
    assert _class(document, "Structure").kind.value == "abstract"  # italic name
    assert _class(document, "Room").kind.value == "class"
    assert _edges(document) == {
        ("Room", "realization", "Drawable"),
        ("Room", "composition", "Furniture"),
        ("Room", "composition", "Structure"),
        ("Window", "inheritance", "Structure"),
        ("Wall", "inheritance", "Structure"),
        ("Couch", "inheritance", "Furniture"),
    }
    names = {c.id: c.name for c in document.classes}
    composition = {
        names[r.destination]: (r.multiplicity.source, r.multiplicity.destination)
        for r in document.relationships
        if r.type.value == "composition"
    }
    assert composition == {"Furniture": ("1", "0..*"), "Structure": ("1", "0..*")}


def test_two_compartment_box_keeps_its_members_as_methods() -> None:
    drawable = _class(_document("uml_6.png"), "Drawable")

    assert drawable.attributes == []
    assert [m.name for m in drawable.methods] == ["redraw", "hide"]
