from backend.services.codegen_service import generate_code


LANG = "javascript"


def test_plain_class(simple_class):
    files = generate_code(simple_class, LANG)
    assert "User.js" in files
    src = files["User.js"]
    assert "class User {" in src
    assert "constructor()" in src
    assert "export { User }" in src


def test_private_field_hash_prefix(class_with_attrs):
    src = generate_code(class_with_attrs, LANG)["User.js"]
    assert "#email" in src


def test_public_field_no_prefix(class_with_attrs):
    src = generate_code(class_with_attrs, LANG)["User.js"]
    assert "age = null;" in src


def test_static_method_keyword(class_with_methods):
    src = generate_code(class_with_methods, LANG)["Service.js"]
    assert "static create()" in src


def test_method_params_names_only(class_with_methods):
    src = generate_code(class_with_methods, LANG)["Service.js"]
    assert "process(data)" in src


def test_method_stub_throws(simple_class):
    from backend.schemas.uml import Method, Position, Size, UmlClass, UmlDocument, Visibility

    doc = UmlDocument(
        classes=[
            UmlClass(
                id="class_1",
                name="Foo",
                methods=[Method(name="bar", visibility=Visibility.PUBLIC)],
                position=Position(x=0, y=0),
                size=Size(width=100, height=80),
            )
        ],
        relationships=[],
    )
    src = generate_code(doc, LANG)["Foo.js"]
    assert "throw new Error('Not implemented')" in src


def test_inheritance_extends(inheritance_pair):
    src = generate_code(inheritance_pair, LANG)["Dog.js"]
    assert "class Dog extends Animal {" in src
    assert "super();" in src


def test_cross_class_import(cross_class_refs):
    src = generate_code(cross_class_refs, LANG)["Order.js"]
    assert "import { User } from './User.js';" in src


def test_aggregation_single_produces_reference_field(aggregation_single):
    src = generate_code(aggregation_single, LANG)["Department.js"]
    assert "#employee = null;" in src
    assert "import { Employee } from './Employee.js';" in src


def test_aggregation_many_produces_list_field(aggregation_many):
    src = generate_code(aggregation_many, LANG)["Department.js"]
    assert "#employees = [];" in src


def test_named_export(simple_class):
    src = generate_code(simple_class, LANG)["User.js"]
    assert "export { User }" in src


def test_empty_document_returns_no_files():
    from backend.schemas.uml import UmlDocument
    assert generate_code(UmlDocument(), LANG) == {}
