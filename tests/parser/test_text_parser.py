import pytest

from backend.parser.text_parser import (
    ParsedAttribute,
    ParsedMethod,
    parse_attribute_line,
    parse_class_name,
    parse_method_line,
)


# ---------------------------------------------------------------------------
# parse_class_name
# ---------------------------------------------------------------------------


def test_class_name_plain():
    assert parse_class_name("User") == "User"


def test_class_name_strips_visibility_prefix():
    assert parse_class_name("+ User") == "User"


def test_class_name_picks_first_clean_line():
    assert parse_class_name("User\n- email : String") == "User"


def test_class_name_ignores_attribute_line():
    assert parse_class_name("- email : String\nUser") == "User"


# ---------------------------------------------------------------------------
# parse_attribute_line
# ---------------------------------------------------------------------------


def test_attr_public_with_type():
    result = parse_attribute_line("+ email : String")
    assert result == ParsedAttribute(name="email", datatype="String", visibility="public")


def test_attr_private_with_type():
    result = parse_attribute_line("- count : int")
    assert result == ParsedAttribute(name="count", datatype="int", visibility="private")


def test_attr_protected():
    result = parse_attribute_line("# id : UUID")
    assert result == ParsedAttribute(name="id", datatype="UUID", visibility="protected")


def test_attr_package():
    result = parse_attribute_line("~ label : String")
    assert result == ParsedAttribute(name="label", datatype="String", visibility="package")


def test_attr_with_default_value():
    result = parse_attribute_line("+ count : int = 0")
    assert result is not None
    assert result.default_value == "0"
    assert result.datatype == "int"


def test_attr_no_visibility_defaults_public():
    result = parse_attribute_line("name : String")
    assert result is not None
    assert result.visibility == "public"


def test_attr_no_type_defaults_object():
    result = parse_attribute_line("- label")
    assert result is not None
    assert result.datatype == "Object"


def test_attr_ocr_semicolon_fix():
    result = parse_attribute_line("- email ; String")
    assert result is not None
    assert result.datatype == "String"


def test_attr_skips_method_line():
    assert parse_attribute_line("+ login()") is None


def test_attr_skips_empty():
    assert parse_attribute_line("") is None
    assert parse_attribute_line("   ") is None


def test_attr_invalid_identifier_returns_none():
    assert parse_attribute_line("- 123bad : int") is None


# ---------------------------------------------------------------------------
# parse_method_line
# ---------------------------------------------------------------------------


def test_method_no_params_no_return():
    result = parse_method_line("+ login()")
    assert result == ParsedMethod(
        name="login", visibility="public", parameters=[], return_type="void"
    )


def test_method_with_return_type():
    result = parse_method_line("+ getCount() : int")
    assert result is not None
    assert result.return_type == "int"


def test_method_with_params():
    result = parse_method_line("+ find(id : int, name : String) : User")
    assert result is not None
    assert result.name == "find"
    assert len(result.parameters) == 2
    assert result.parameters[0].name == "id"
    assert result.parameters[0].datatype == "int"
    assert result.parameters[1].name == "name"
    assert result.parameters[1].datatype == "String"
    assert result.return_type == "User"


def test_method_private():
    result = parse_method_line("- validate() : bool")
    assert result is not None
    assert result.visibility == "private"


def test_method_no_parentheses_returns_none():
    assert parse_method_line("+ login") is None


def test_method_empty_returns_none():
    assert parse_method_line("") is None


def test_method_param_without_type():
    result = parse_method_line("+ process(data)")
    assert result is not None
    assert result.parameters[0].datatype == "Object"


def test_method_ocr_semicolon_in_return():
    result = parse_method_line("+ getEmail() ; String")
    assert result is not None
    assert result.return_type == "String"
