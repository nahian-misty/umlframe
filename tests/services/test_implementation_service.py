import json

import pytest

from backend.llm.types import LlmNotConfiguredError, LlmRateLimitedError, LlmUpstreamError
from backend.schemas.uml import Method, Position, Size, UmlClass, UmlDocument, Visibility
from backend.services import implementation_service
from backend.services.implementation_service import MAX_CLASSES


def _reply(**bodies: str) -> str:
    return json.dumps({"methods": {key.replace("__", "."): body for key, body in bodies.items()}})


def _method(name: str, return_type: str = "void", **kw) -> Method:
    return Method(name=name, visibility=Visibility.PUBLIC, parameters=[], return_type=return_type, **kw)


def _class(class_id: str, name: str, methods: list[Method]) -> UmlClass:
    return UmlClass(
        id=class_id,
        name=name,
        methods=methods,
        position=Position(x=0, y=0),
        size=Size(width=100, height=100),
    )


def test_bodies_from_the_model_are_spliced_into_the_scaffold(account_document, fake_llm):
    client = fake_llm(
        _reply(
            Account__deposit="self.__balance += amount",
            Account__getBalance="return self.__balance",
        )
    )

    result = implementation_service.implement_code(
        account_document, "python", "keep it simple", client
    )

    assert result.implemented == ["Account.deposit", "Account.getBalance"]
    assert result.skipped == []
    assert result.models == ["fake/model"]
    source = result.files["Account.py"]
    assert "        self.__balance += amount\n" in source
    assert "        return self.__balance\n" in source
    assert "    @abstractmethod\n    def audit(self) -> None:\n        ...\n" in source


def test_the_prompt_lists_only_concrete_methods_and_carries_the_user_notes(account_document, fake_llm):
    client = fake_llm(_reply(Account__deposit="pass", Account__getBalance="return 0"))

    implementation_service.implement_code(account_document, "python", "use a ledger list", client)

    (messages,) = client.prompts
    assert '["Account.deposit", "Account.getBalance"]' in messages[1].content
    assert "use a ledger list" in messages[1].content


def test_a_missing_body_keeps_its_stub_and_is_reported(account_document, fake_llm):
    client = fake_llm(_reply(Account__getBalance="return self.__balance"))

    result = implementation_service.implement_code(account_document, "python", "", client)

    assert result.implemented == ["Account.getBalance"]
    assert [(s.key, s.reason) for s in result.skipped] == [
        ("Account.deposit", "the model returned no body")
    ]
    assert "    def deposit(self, amount: int) -> None:\n        ...\n" in result.files["Account.py"]


def test_a_body_with_a_syntax_error_is_dropped_but_valid_ones_survive(account_document, fake_llm):
    client = fake_llm(_reply(Account__deposit="self.__balance = (", Account__getBalance="return 1"))

    result = implementation_service.implement_code(account_document, "python", "", client)

    assert result.implemented == ["Account.getBalance"]
    assert [s.key for s in result.skipped] == ["Account.deposit"]
    assert "python syntax error" in result.skipped[0].reason
    assert "self.__balance = (" not in result.files["Account.py"]


def test_a_python_body_that_repeats_the_signature_is_rejected(account_document, fake_llm):
    client = fake_llm(
        _reply(
            Account__deposit="def deposit(self, amount):\n    self.__balance += amount",
            Account__getBalance="return 1",
        )
    )

    result = implementation_service.implement_code(account_document, "python", "", client)

    assert result.implemented == ["Account.getBalance"]
    assert result.skipped[0].reason == "the model included the method signature"


def test_a_reply_that_is_not_json_leaves_every_stub_and_reports_why(account_document, fake_llm):
    result = implementation_service.implement_code(
        account_document, "python", "", fake_llm("I cannot help with that")
    )

    assert result.implemented == []
    assert {s.key for s in result.skipped} == {"Account.deposit", "Account.getBalance"}
    assert all("valid JSON" in s.reason for s in result.skipped)


def test_java_and_javascript_bodies_are_validated_and_spliced(account_document, fake_llm):
    java = implementation_service.implement_code(
        account_document,
        "java",
        "",
        fake_llm(_reply(Account__deposit="this.balance += amount;", Account__getBalance="return this.balance;")),
    )
    assert "        return this.balance;\n" in java.files["Account.java"]
    assert java.skipped == []

    js = implementation_service.implement_code(
        account_document,
        "javascript",
        "",
        fake_llm(_reply(Account__deposit="this.#balance += amount;", Account__getBalance="return (")),
    )
    assert js.implemented == ["Account.deposit"]
    assert "javascript syntax error" in js.skipped[0].reason


def test_overloaded_method_names_get_distinct_keys(fake_llm):
    document = UmlDocument(classes=[_class("class_1", "A", [_method("f"), _method("f", "int")])])
    client = fake_llm(_reply(A__f="return None", **{"A__f#2": "return 1"}))

    result = implementation_service.implement_code(document, "python", "", client)

    assert result.implemented == ["A.f", "A.f#2"]
    source = result.files["A.py"]
    assert "def f(self) -> None:\n        return None\n" in source
    assert "def f(self) -> int:\n        return 1\n" in source


def test_a_class_with_only_abstract_methods_makes_no_model_call(fake_llm):
    document = UmlDocument(classes=[_class("class_1", "A", [_method("f", abstract=True)])])
    client = fake_llm(_reply())

    result = implementation_service.implement_code(document, "python", "", client)

    assert client.prompts == []
    assert result.implemented == [] and result.skipped == []


def test_one_failing_class_does_not_sink_the_others(fake_llm):
    document = UmlDocument(
        classes=[_class("class_1", "A", [_method("a")]), _class("class_2", "B", [_method("b")])]
    )

    def reply(messages):
        if '"class_name": "A"' in messages[1].content:
            return LlmUpstreamError("model unavailable")
        return _reply(B__b="return None")

    result = implementation_service.implement_code(document, "python", "", fake_llm(reply))

    assert result.implemented == ["B.b"]
    assert [(s.key, s.reason) for s in result.skipped] == [("A.a", "model unavailable")]


def test_when_no_class_gets_an_answer_the_cause_is_raised(account_document, fake_llm):
    with pytest.raises(LlmRateLimitedError):
        implementation_service.implement_code(
            account_document, "python", "", fake_llm(LlmRateLimitedError("slow down"))
        )
    with pytest.raises(LlmUpstreamError):
        implementation_service.implement_code(
            account_document, "python", "", fake_llm(LlmUpstreamError("down"))
        )
    with pytest.raises(LlmNotConfiguredError):
        implementation_service.implement_code(
            account_document, "python", "", fake_llm(LlmNotConfiguredError("bad key"))
        )


def test_an_unconfigured_client_is_rejected_before_any_work(account_document, fake_llm):
    client = fake_llm(_reply(), configured=False)
    with pytest.raises(LlmNotConfiguredError):
        implementation_service.implement_code(account_document, "python", "", client)
    assert client.prompts == []


def test_unsupported_language_and_oversized_documents_are_rejected(account_document, fake_llm):
    with pytest.raises(ValueError, match="Unsupported"):
        implementation_service.implement_code(account_document, "cobol", "", fake_llm(_reply()))

    big = UmlDocument(
        classes=[_class(f"class_{i}", f"C{i}", [_method("m")]) for i in range(MAX_CLASSES + 1)]
    )
    with pytest.raises(ValueError, match="Too many classes"):
        implementation_service.implement_code(big, "python", "", fake_llm(_reply()))
