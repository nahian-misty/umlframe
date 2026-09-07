"""End-to-end reverse pipeline: source → UmlDocument → Mermaid, for all three
languages, plus the activity-diagram extension (source → ActivityDocument →
Mermaid flowchart) and a lightweight forward/reverse consistency check.
"""

from pathlib import Path

from backend.services import codegen_service, mermaid_service, reverse_service

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _load(language: str, name: str) -> str:
    return (FIXTURES / language / name).read_text()


# ---------------------------------------------------------------------------
# Reverse pipeline: source -> UmlDocument -> Mermaid class diagram
# ---------------------------------------------------------------------------


def test_python_source_to_class_diagram():
    source = _load("python", "composition_aggregation.py")
    document = reverse_service.source_to_document(source, "python")
    diagram = mermaid_service.document_to_mermaid(document)

    assert diagram.startswith("classDiagram")
    assert "class Car" in diagram
    assert "class Engine" in diagram
    assert "*--" in diagram  # composition (Car *-- Engine)
    assert "o--" in diagram  # aggregation (Car o-- Person / Wheel)


def test_java_source_to_class_diagram():
    source = _load("java", "composition_aggregation.java")
    document = reverse_service.source_to_document(source, "java")
    diagram = mermaid_service.document_to_mermaid(document)

    assert diagram.startswith("classDiagram")
    assert len(document.classes) >= 2
    assert len(document.relationships) >= 1


def test_javascript_source_to_class_diagram():
    source = _load("javascript", "composition.js")
    document = reverse_service.source_to_document(source, "javascript")
    diagram = mermaid_service.document_to_mermaid(document)

    assert diagram.startswith("classDiagram")
    assert len(document.classes) >= 2
    assert "*--" in diagram  # JS reverse parser only ever infers composition


# ---------------------------------------------------------------------------
# Reverse pipeline extension: source -> ActivityDocument -> Mermaid flowchart
# ---------------------------------------------------------------------------

_CONTROL_FLOW_SOURCE = {
    "python": (
        "class Calc:\n"
        "    def classify(self, x: int) -> str:\n"
        "        if x > 0:\n"
        "            return 'positive'\n"
        "        return 'non-positive'\n"
    ),
    "java": (
        "public class Calc {\n"
        "    public String classify(int x) {\n"
        "        if (x > 0) { return \"positive\"; }\n"
        "        return \"non-positive\";\n"
        "    }\n"
        "}\n"
    ),
    "javascript": (
        "class Calc {\n"
        "    classify(x) {\n"
        "        if (x > 0) { return 'positive'; }\n"
        "        return 'non-positive';\n"
        "    }\n"
        "}\n"
    ),
}


def test_control_flow_extraction_to_activity_diagram_all_languages():
    for language, source in _CONTROL_FLOW_SOURCE.items():
        control_flow = reverse_service.source_to_control_flow(source, language, "Calc", "classify")
        diagram = mermaid_service.activity_to_mermaid(control_flow)

        assert diagram.startswith("flowchart TD")
        assert '"x > 0"' in diagram
        assert '-->|"yes"|' in diagram
        assert '-->|"no"|' in diagram


# ---------------------------------------------------------------------------
# Cross-pipeline consistency: forward-generate Python code from a hand-built
# UmlDocument, then reverse-parse that generated code and confirm the class
# structure round-trips. Kept simple -- a sanity check, not a fuzzer.
# ---------------------------------------------------------------------------


def test_codegen_then_reverse_round_trip_preserves_class_structure():
    from backend.schemas.uml import Attribute, Position, Size, UmlClass, UmlDocument, Visibility

    document = UmlDocument(
        classes=[
            UmlClass(
                id="class_1",
                name="Account",
                attributes=[Attribute(name="balance", datatype="int", visibility=Visibility.PRIVATE)],
                methods=[],
                position=Position(x=0, y=0),
                size=Size(width=200, height=140),
            )
        ],
        relationships=[],
    )

    files = codegen_service.generate_code(document, "python")
    generated_source = files["Account.py"]

    round_tripped = reverse_service.source_to_document(generated_source, "python")

    assert len(round_tripped.classes) == 1
    account = round_tripped.classes[0]
    assert account.name == "Account"
    # Python codegen prefixes a PRIVATE attribute with "__" (its own visibility
    # convention), which the reverse parser then reads back as PRIVATE via
    # name-mangling detection -- the visibility survives the round trip, the
    # exact name doesn't (a known, accepted asymmetry between the two
    # pipelines' visibility conventions, not a bug in either one alone).
    balance = next(a for a in account.attributes if "balance" in a.name)
    assert balance.visibility == Visibility.PRIVATE
