import pytest

from backend.reverse.phrasing import describe_step, describe_steps


@pytest.mark.parametrize(
    ("statement", "expected"),
    [
        ("const total = this.cart.calculateTotal()", "Calculate total"),
        ("total = self.cart.calculate_total()", "Calculate total"),
        ("data = fetch()", "Fetch data"),
        ("const item = new CartItem(product, quantity)", "Create CartItem"),
        ("CartItem item = new CartItem(product, quantity);", "Create CartItem"),
        ("int z = y * 2", "Calculate z"),
        ("name = other", "Set name"),
        ("count += 1", "Increase count"),
        ("count -= 1", "Decrease count"),
        ("i++", "Increase i"),
        ("this.items.push(item)", "Add item to items"),
        ("self.items.append(item)", "Add item to items"),
        ("this.items.remove(item)", "Remove item from items"),
        ('console.log("Cart is empty.")', 'Print "Cart is empty."'),
        ("print(total)", "Print total"),
        ('System.out.println("hi");', 'Print "hi"'),
        ("print(a + b)", "Print output"),
        ("repo.save(user)", "Save user"),
        ("save()", "Save"),
        ("send_welcome_email()", "Send welcome email"),
        ("return", "Return"),
        ("return total", "Return total"),
        ("return 0", "Return 0"),
        ("return a / b", "Return result"),
        ("raise ValueError('bad')", "Raise ValueError"),
        ("throw new IllegalStateException(\"x\")", "Throw IllegalStateException"),
        ("pass", "Do nothing"),
    ],
)
def test_statement_is_described_in_plain_english(statement, expected):
    assert describe_step(statement) == expected


@pytest.mark.parametrize("statement", ["x == 3", "weird <stuff>", "a[0]"])
def test_unrecognised_statement_is_returned_unchanged(statement):
    assert describe_step(statement) == statement


def test_a_comma_inside_a_string_argument_does_not_split_arguments():
    assert describe_step('console.log("a, b", total)') == 'Print "a, b"'


def test_several_statements_in_one_box_are_joined():
    assert describe_steps(["y = x + 1", "return y"]) == "Calculate y; Return y"
