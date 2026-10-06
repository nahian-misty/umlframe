import pytest

from backend.services.codegen_service import describe_class, generate_code

PYTHON_STUBS = (
    "from abc import ABC, abstractmethod\n\n\n"
    "class Account(ABC):\n"
    "    def __init__(self) -> None:\n"
    "        self.__balance: int = None\n\n"
    "    def deposit(self, amount: int) -> None:\n"
    "        ...\n\n"
    "    def getBalance(self) -> int:\n"
    "        ...\n\n"
    "    @abstractmethod\n"
    "    def audit(self) -> None:\n"
    "        ...\n\n"
)

JAVA_DEPOSIT_IMPLEMENTED = (
    "public abstract class Account {\n\n"
    "    private int balance;\n\n"
    "    public Account() {\n"
    "    }\n\n"
    "    public void deposit(int amount) {\n"
    "        this.balance += amount;\n"
    "    }\n"
    "    public int getBalance() {\n"
    '        throw new UnsupportedOperationException("Not implemented");\n'
    "    }\n"
    "    public abstract void audit();\n"
    "}\n"
)

JAVASCRIPT_DEPOSIT_IMPLEMENTED = (
    "class Account {\n"
    "    #balance = null;\n\n"
    "    constructor() {\n"
    "        // initialise fields above\n"
    "    }\n\n"
    "    deposit(amount) {\n"
    "        this.#balance += amount;\n"
    "    }\n\n"
    "    getBalance() {\n"
    "        throw new Error('Not implemented');\n"
    "    }\n\n"
    "    audit() {\n"
    "        throw new Error('Not implemented');\n"
    "    }\n\n"
    "}\n\n"
    "export { Account };\n"
)


def test_python_stubs_are_unchanged_when_nothing_is_implemented(account_document):
    assert generate_code(account_document, "python")["Account.py"] == PYTHON_STUBS


def test_python_implemented_method_replaces_only_its_own_stub(account_document):
    files = generate_code(account_document, "python", {("class_1", 0): "self.__balance += amount"})
    assert files["Account.py"] == PYTHON_STUBS.replace(
        "    def deposit(self, amount: int) -> None:\n        ...\n",
        "    def deposit(self, amount: int) -> None:\n        self.__balance += amount\n",
    )


def test_java_implemented_method_replaces_the_stub_inside_its_braces(account_document):
    files = generate_code(account_document, "java", {("class_1", 0): "this.balance += amount;"})
    assert files["Account.java"] == JAVA_DEPOSIT_IMPLEMENTED


def test_javascript_implemented_method_replaces_the_stub_inside_its_braces(account_document):
    files = generate_code(account_document, "javascript", {("class_1", 0): "this.#balance += amount;"})
    assert files["Account.js"] == JAVASCRIPT_DEPOSIT_IMPLEMENTED


def test_python_bodies_are_indented_and_replace_only_their_method(account_document):
    files = generate_code(
        account_document,
        "python",
        {("class_1", 0): "self.__balance += amount", ("class_1", 1): "if True:\n    return self.__balance\nreturn 0"},
    )
    source = files["Account.py"]
    assert (
        "    def deposit(self, amount: int) -> None:\n        self.__balance += amount\n\n" in source
    )
    assert (
        "    def getBalance(self) -> int:\n"
        "        if True:\n"
        "            return self.__balance\n"
        "        return 0\n\n" in source
    )


def test_abstract_methods_ignore_a_supplied_body(account_document):
    source = generate_code(account_document, "python", {("class_1", 2): "return 1"})["Account.py"]
    assert "    @abstractmethod\n    def audit(self) -> None:\n        ...\n" in source
    assert "return 1" not in source


def test_blank_lines_inside_a_body_carry_no_trailing_spaces(account_document):
    source = generate_code(
        account_document, "python", {("class_1", 0): "a = 1\n\nb = 2"}
    )["Account.py"]
    assert "        a = 1\n\n        b = 2\n" in source


def test_tabs_and_common_indentation_are_normalised(account_document):
    source = generate_code(
        account_document, "python", {("class_1", 0): "    if x:\n\t    y = 1"}
    )["Account.py"]
    assert "        if x:\n            y = 1\n" in source


def test_whitespace_only_body_falls_back_to_the_stub(account_document):
    source = generate_code(account_document, "python", {("class_1", 0): "   \n  "})["Account.py"]
    assert "    def deposit(self, amount: int) -> None:\n        ...\n" in source


def test_class_ids_restricts_the_rendered_files(account_document):
    assert generate_code(account_document, "python", class_ids={"nope"}) == {}
    assert set(generate_code(account_document, "python", class_ids={"class_1"})) == {"Account.py"}


@pytest.mark.parametrize("language", ["python", "java", "javascript"])
def test_stub_output_is_identical_with_empty_implementations(account_document, language):
    assert generate_code(account_document, language, {}) == generate_code(account_document, language)


def test_describe_class_uses_the_names_the_scaffold_generates(account_document):
    description = describe_class(account_document, "class_1", "python")
    assert [(a.name, a.access) for a in description.attributes] == [("balance", "self.__balance")]
    deposit = description.methods[0]
    assert (deposit.key, deposit.signature, deposit.access) == (
        "Account.deposit",
        "def deposit(self, amount: int) -> None",
        "self.deposit",
    )
    assert description.methods[2].abstract is True

    java = describe_class(account_document, "class_1", "java")
    assert java.attributes[0].access == "this.balance"
    assert java.methods[1].signature == "public int getBalance()"


def test_describe_class_unknown_class_or_language_raises(account_document):
    with pytest.raises(ValueError, match="not found"):
        describe_class(account_document, "class_9", "python")
    with pytest.raises(ValueError, match="Unsupported"):
        describe_class(account_document, "class_1", "cobol")
