from backend.services.codegen_service import generate_code


LANG = "python"


def test_plain_class(simple_class):
    files = generate_code(simple_class, LANG)
    assert "User.py" in files
    src = files["User.py"]
    assert "class User:" in src
    assert "def __init__(self)" in src


def test_private_attribute_gets_dunder_prefix(class_with_attrs):
    src = generate_code(class_with_attrs, LANG)["User.py"]
    assert "self.__email: str" in src


def test_protected_attribute_gets_single_prefix(class_with_attrs):
    src = generate_code(class_with_attrs, LANG)["User.py"]
    assert "self._age: int" in src


def test_static_attribute_at_class_scope(class_with_attrs):
    src = generate_code(class_with_attrs, LANG)["User.py"]
    assert "MAX_SIZE: int = 100" in src
    assert "self.MAX_SIZE" not in src


def test_string_type_mapped_to_str(class_with_attrs):
    src = generate_code(class_with_attrs, LANG)["User.py"]
    assert "str" in src
    assert "String" not in src


def test_method_with_params(class_with_methods):
    src = generate_code(class_with_methods, LANG)["Service.py"]
    assert "def process(self, data: str) -> bool:" in src


def test_static_method_decorator(class_with_methods):
    src = generate_code(class_with_methods, LANG)["Service.py"]
    assert "@staticmethod" in src
    assert "def create(" in src


def test_abstract_method_decorator(class_with_methods):
    src = generate_code(class_with_methods, LANG)["Service.py"]
    assert "@abstractmethod" in src
    assert "def compute(self)" in src


def test_abstract_class_imports_abc(class_with_methods):
    src = generate_code(class_with_methods, LANG)["Service.py"]
    assert "from abc import ABC, abstractmethod" in src


def test_inheritance_extends_parent(inheritance_pair):
    files = generate_code(inheritance_pair, LANG)
    dog_src = files["Dog.py"]
    assert "class Dog(Animal):" in dog_src
    assert "super().__init__()" in dog_src


def test_cross_class_import(cross_class_refs):
    src = generate_code(cross_class_refs, LANG)["Order.py"]
    assert "from .User import User" in src


def test_aggregation_single_produces_reference_field(aggregation_single):
    src = generate_code(aggregation_single, LANG)["Department.py"]
    assert "self.__employee: Employee = None" in src
    assert "from .Employee import Employee" in src


def test_aggregation_many_produces_list_field(aggregation_many):
    src = generate_code(aggregation_many, LANG)["Department.py"]
    assert "self.__employees: list[Employee] = []" in src


def test_composition_many_produces_list_field(composition_many):
    src = generate_code(composition_many, LANG)["Car.py"]
    assert "self.__wheels: list[Wheel] = []" in src


def test_aggregation_field_not_added_to_part_class(aggregation_single):
    src = generate_code(aggregation_single, LANG)["Employee.py"]
    assert "Department" not in src


def test_empty_document_returns_no_files():
    from backend.schemas.uml import UmlDocument
    files = generate_code(UmlDocument(), LANG)
    assert files == {}
