import pytest

from backend.llm.validators import syntax_error


@pytest.mark.parametrize(
    ("language", "source"),
    [
        ("python", "class A:\n    def f(self):\n        return 1\n"),
        ("java", "class A { int f() { return 1; } }"),
        ("javascript", "class A { f() { return 1; } }\nexport { A };"),
    ],
)
def test_valid_source_has_no_error(language, source):
    assert syntax_error(language, source) is None


@pytest.mark.parametrize(
    ("language", "source"),
    [
        ("python", "class A:\n    def f(self):\n        return (\n"),
        ("java", "class A { int f() { return ; } "),
        ("javascript", "class A { f() { return ; }"),
    ],
)
def test_broken_source_reports_a_reason(language, source):
    assert "syntax error" in (syntax_error(language, source) or "")


def test_unknown_language_is_reported():
    assert "unsupported" in syntax_error("cobol", "x")


def test_javascript_private_names_do_not_trip_the_old_parser():
    from backend.llm.validators import javascript_body_error

    assert javascript_body_error("this.#balance += amount;\nreturn this.#balance;") is None


def test_javascript_body_is_checked_inside_a_function():
    from backend.llm.validators import javascript_body_error

    assert javascript_body_error("return 1;") is None
    assert "syntax error" in (javascript_body_error("return (") or "")
    assert "syntax error" in (javascript_body_error("}} injected {{") or "")
