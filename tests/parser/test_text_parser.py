import pytest

from backend.parser.text_parser import (
    ParsedAttribute,
    ParsedMethod,
    is_method_line,
    parse_attribute_line,
    parse_class_header,
    parse_class_name,
    parse_method_line,
    parse_multiplicity,
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


# ---------------------------------------------------------------------------
# Class header: stereotypes
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "text,expected",
    [
        ("<<interface>>\nOwner", ("Owner", "interface")),
        ("«interface»\nOwner", ("Owner", "interface")),
        ("<<abstract>>\nShape", ("Shape", "abstract")),
        ("Shape {abstract}", ("Shape", "abstract")),
        ("<<Interface>> Owner", ("Owner", "interface")),
        ("User", ("User", None)),
    ],
)
def test_class_header_reads_stereotype_and_name(text, expected):
    assert parse_class_header(text) == expected


def test_class_name_skips_the_stereotype_line():
    assert parse_class_name("<<interface>>\nOwner") == "Owner"


# ---------------------------------------------------------------------------
# OCR repairs
# ---------------------------------------------------------------------------


def test_brace_read_for_parenthesis_is_repaired():
    assert parse_method_line("+quack{)") == ParsedMethod("quack", "public", [], "void")


def test_trailing_border_noise_is_dropped():
    assert parse_method_line("+mate() |") == ParsedMethod("mate", "public", [], "void")


def test_curly_quotes_in_default_value_become_straight():
    result = parse_attribute_line("+beakColr: String = “yellow”")
    assert result is not None
    assert result.default_value == '"yellow"'


@pytest.mark.parametrize("written", ["String[ ]", "String ]", "String[]"])
def test_array_types_are_normalised(written):
    result = parse_attribute_line(f"- authors : {written}")
    assert result is not None
    assert result.datatype == "String[]"


def test_array_return_type_is_normalised():
    result = parse_method_line("+getAuthors() : String ]")
    assert result is not None
    assert result.return_type == "String[]"


@pytest.mark.parametrize(
    "read,written",
    [("sizelnFt", "sizeInFt"), ("lsOpen", "isOpen"), ("isOpen", "isOpen"), ("kiln", "kiln")],
)
def test_capital_i_read_as_l_is_repaired_in_camel_case(read, written):
    result = parse_attribute_line(f"- {read} : int")
    assert result is not None
    assert result.name == written


def test_is_method_line_sees_through_brace_noise():
    assert is_method_line("+quack{)")
    assert not is_method_line("+age: Int")


@pytest.mark.parametrize(
    "text,expected",
    [
        ("1", "1"),
        ("*", "*"),
        ("0..*", "0..*"),
        ("0.*", "0..*"),
        ("0..", "0..*"),
        ("1,.*", "1..*"),
        ("0..1", "0..1"),
        ("n", "*"),
        ("abc", None),
        ("", None),
    ],
)
def test_multiplicity_is_normalised(text, expected):
    assert parse_multiplicity(text) == expected


@pytest.mark.parametrize("written,value", [("400ft", '"400ft"'), ("blue", '"blue"'), ("no", '"no"')])
def test_a_value_written_where_a_type_goes_becomes_a_quoted_default(written, value):
    result = parse_attribute_line(f"- x : {written}")
    assert result is not None
    assert (result.datatype, result.default_value) == ("String", value)


@pytest.mark.parametrize("written", ["Color", "double", "String[]", "List<String>"])
def test_real_types_are_kept(written):
    result = parse_attribute_line(f"- x : {written}")
    assert result is not None
    assert (result.datatype, result.default_value) == (written, None)


def test_a_return_type_that_is_not_a_type_falls_back_to_void():
    result = parse_method_line("+ numSeats() : 5")
    assert result is not None
    assert result.return_type == "void"


def test_class_stereotype_line_is_not_taken_for_the_name():
    assert parse_class_header("«class»\nBook") == ("Book", "class")
    assert parse_class_name("«class»\nBook") == "Book"


def test_interface_stereotype_still_marks_an_interface():
    assert parse_class_header("«interface»\nShape") == ("Shape", "interface")


def test_attribute_minus_read_as_a_curly_quote_is_private():
    assert parse_attribute_line("“author: String") == ParsedAttribute(
        name="author", datatype="String", visibility="private"
    )


def test_bracket_generic_type_is_kept_as_a_type():
    parsed = parse_attribute_line("-books: List[Book]")

    assert parsed is not None
    assert (parsed.datatype, parsed.default_value) == ("List[Book]", None)


@pytest.mark.parametrize("line", ["+ attribute", "+ method"])
def test_editor_placeholder_rows_are_not_members(line):
    assert parse_attribute_line(line) is None
    assert parse_method_line(line) is None


def test_method_cut_off_by_an_ellipsis_keeps_no_guessed_type():
    parsed = parse_method_line("+addBook(book: Book): v..")

    assert parsed is not None
    assert parsed.return_type == "void"
    assert [p.name for p in parsed.parameters] == ["book"]


def test_signature_cut_off_before_its_closing_paren_drops_the_incomplete_parameter():
    parsed = parse_method_line("+borrow(member: Member, book: Bo...")

    assert parsed is not None
    assert [p.name for p in parsed.parameters] == ["member"]
