import pytest

from backend.llm.parsing import MAX_BODY_LENGTH, parse_method_bodies

KEYS = ["A.one", "A.two"]


def test_reads_the_methods_object():
    parsed = parse_method_bodies('{"methods": {"A.one": "return 1", "A.two": "return 2"}}', KEYS)
    assert parsed.bodies == {"A.one": "return 1", "A.two": "return 2"}
    assert parsed.rejected == {}


def test_accepts_a_bare_key_to_body_object():
    assert parse_method_bodies('{"A.one": "x", "A.two": "y"}', KEYS).bodies == {
        "A.one": "x",
        "A.two": "y",
    }


def test_strips_a_markdown_fence_around_the_whole_reply():
    reply = '```json\n{"methods": {"A.one": "return 1"}}\n```'
    assert parse_method_bodies(reply, ["A.one"]).bodies == {"A.one": "return 1"}


def test_finds_the_json_object_inside_chatty_text():
    reply = 'Sure! Here you go:\n{"methods": {"A.one": "return 1"}}\nHope that helps.'
    assert parse_method_bodies(reply, ["A.one"]).bodies == {"A.one": "return 1"}


def test_strips_fences_inside_a_body():
    reply = '{"methods": {"A.one": "```python\\nreturn 1\\n```"}}'
    assert parse_method_bodies(reply, ["A.one"]).bodies == {"A.one": "return 1"}


def test_unknown_keys_are_dropped_and_missing_ones_rejected():
    parsed = parse_method_bodies('{"methods": {"A.one": "x", "B.evil": "rm -rf /"}}', KEYS)
    assert parsed.bodies == {"A.one": "x"}
    assert parsed.rejected == {"A.two": "the model returned no body"}


def test_non_text_empty_and_oversized_bodies_are_rejected():
    reply = '{"methods": {"A.one": 5, "A.two": "%s"}}' % ("x" * (MAX_BODY_LENGTH + 1))
    parsed = parse_method_bodies(reply, KEYS)
    assert parsed.bodies == {}
    assert "non-text" in parsed.rejected["A.one"]
    assert "longer than" in parsed.rejected["A.two"]
    assert "non-text" in parse_method_bodies('{"methods": {"A.one": "  "}}', ["A.one"]).rejected["A.one"]


@pytest.mark.parametrize("reply", ["not json at all", "[1, 2]", '{"methods": []}', ""])
def test_a_reply_that_is_not_an_object_of_bodies_raises(reply):
    with pytest.raises(ValueError):
        parse_method_bodies(reply, KEYS)
