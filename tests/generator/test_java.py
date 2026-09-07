from backend.services.codegen_service import generate_code


LANG = "java"


def test_plain_class(simple_class):
    files = generate_code(simple_class, LANG)
    assert "User.java" in files
    src = files["User.java"]
    assert "public class User {" in src
    assert "public User()" in src


def test_private_attribute_keyword(class_with_attrs):
    src = generate_code(class_with_attrs, LANG)["User.java"]
    assert "private String email;" in src


def test_protected_attribute_keyword(class_with_attrs):
    src = generate_code(class_with_attrs, LANG)["User.java"]
    assert "protected int age;" in src


def test_static_attribute(class_with_attrs):
    src = generate_code(class_with_attrs, LANG)["User.java"]
    assert "public static int MAX_SIZE = 100;" in src


def test_method_with_params(class_with_methods):
    src = generate_code(class_with_methods, LANG)["Service.java"]
    assert "public boolean process(String data)" in src


def test_static_method(class_with_methods):
    src = generate_code(class_with_methods, LANG)["Service.java"]
    assert "public static void create()" in src


def test_abstract_method(class_with_methods):
    src = generate_code(class_with_methods, LANG)["Service.java"]
    assert "public abstract int compute();" in src


def test_abstract_class_declaration(class_with_methods):
    src = generate_code(class_with_methods, LANG)["Service.java"]
    assert "public abstract class Service {" in src


def test_inheritance_extends(inheritance_pair):
    src = generate_code(inheritance_pair, LANG)["Dog.java"]
    assert "public class Dog extends Animal {" in src


def test_aggregation_single_produces_reference_field(aggregation_single):
    src = generate_code(aggregation_single, LANG)["Department.java"]
    assert "private Employee employee;" in src


def test_aggregation_many_produces_list_field(aggregation_many):
    src = generate_code(aggregation_many, LANG)["Department.java"]
    assert "private List<Employee> employees = new ArrayList<>();" in src
    assert "import java.util.List;" in src
    assert "import java.util.ArrayList;" in src


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
    src = generate_code(doc, LANG)["Foo.java"]
    assert "UnsupportedOperationException" in src


def test_empty_document_returns_no_files():
    from backend.schemas.uml import UmlDocument
    assert generate_code(UmlDocument(), LANG) == {}
