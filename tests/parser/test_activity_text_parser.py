from backend.parser.activity_text_parser import classify_guard, normalize_label

# ---------------------------------------------------------------------------
# normalize_label
# ---------------------------------------------------------------------------


def test_normalize_label_plain():
    assert normalize_label("do work") == "do work"


def test_normalize_label_collapses_whitespace_and_newlines():
    assert normalize_label("  check\n  the   value ") == "check the value"


def test_normalize_label_fixes_em_dash():
    assert normalize_label("n —= 1") == "n -= 1"


def test_normalize_label_fixes_en_dash():
    assert normalize_label("x –> y") == "x -> y"


def test_normalize_label_fixes_middle_dot():
    assert normalize_label("obj·method") == "obj.method"


def test_normalize_label_keeps_semicolons():
    # ";" is legitimate statement text in an action label, unlike a class line.
    assert normalize_label("a += 1; b += 1") == "a += 1; b += 1"


def test_normalize_label_empty():
    assert normalize_label("   \n  ") == ""


# ---------------------------------------------------------------------------
# classify_guard
# ---------------------------------------------------------------------------


def test_classify_guard_yes_synonyms():
    for token in ("yes", "Yes", "YES", "y", "true", "T"):
        assert classify_guard(token) == "yes"


def test_classify_guard_no_synonyms():
    for token in ("no", "No", "n", "false", "F"):
        assert classify_guard(token) == "no"


def test_classify_guard_strips_trailing_punctuation():
    assert classify_guard("yes.") == "yes"
    assert classify_guard("no!") == "no"


def test_classify_guard_unreadable_returns_empty():
    for token in ("", "maybe", "x > 0", "???"):
        assert classify_guard(token) == ""
