"""Plain-English phrases for the statements an activity diagram box stands for.

The control-flow extractors hand over each straight-line statement as source text; this turns it
into a short action label ("Calculate total", "Create CartItem", "Print \"Cart is empty.\"")
instead of the code itself. Rule-based and language-neutral; anything it does not recognise is
returned unchanged, so a label is never invented."""

from __future__ import annotations

import re

_IDENT = r"[A-Za-z_$][\w$]*"
_PATH = rf"{_IDENT}(?:\.{_IDENT})*"
_SELF_PREFIXES = ("this.", "self.")

_ASSIGN = re.compile(
    rf"^(?:(?:const|let|var|final)\s+)?(?:[\w$<>\[\],.?]+\s+)?({_PATH})\s*(\+=|-=|=)(?!=)\s*(.+)$",
    re.DOTALL,
)
_CALL = re.compile(rf"^(?:new\s+)?({_PATH})\s*\((.*)\)$", re.DOTALL)
_RETURN = re.compile(r"^return(?:\s+(.+))?$", re.DOTALL)
_RAISE = re.compile(rf"^(raise|throw)\s+(?:new\s+)?({_IDENT})")
_STEP = re.compile(rf"^({_PATH})(\+\+|--)$")
_STRING = re.compile(r"""^(?:"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')$""")
_LITERAL = re.compile(r"^-?\d+(?:\.\d+)?$|^(?:true|false|null|None|True|False|undefined)$")
_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")

_PRINT_CALLS = {
    "print",
    "console.log",
    "console.info",
    "console.warn",
    "console.error",
    "System.out.println",
    "System.out.print",
    "System.err.println",
}
_ADD_METHODS = {"append", "push", "add", "addLast", "addFirst", "insert"}
_REMOVE_METHODS = {"remove", "pop", "delete", "removeFirst", "removeLast"}
_ARITHMETIC = re.compile(r"[-+*/%]|\bmod\b")
_NOOP_STATEMENTS = {"pass": "Do nothing", "...": "Do nothing"}


def describe_steps(statements: list[str]) -> str:
    """One box's worth of straight-line statements as a single label."""
    return "; ".join(describe_step(s) for s in statements)


def describe_step(statement: str) -> str:
    text = statement.strip().rstrip(";").strip()
    if text in _NOOP_STATEMENTS:
        return _NOOP_STATEMENTS[text]
    for rule in (_return_phrase, _raise_phrase, _assignment_phrase, _step_phrase, _call_phrase):
        phrase = rule(text)
        if phrase:
            return phrase
    return statement


def _words(identifier: str) -> list[str]:
    """`calculateTotal` / `calculate_total` -> ['calculate', 'total']."""
    parts: list[str] = []
    for chunk in identifier.replace("$", "").split("_"):
        parts.extend(_CAMEL_BOUNDARY.split(chunk))
    return [p.lower() for p in parts if p]


def _bare(path: str) -> str:
    """The last name of a dotted path, without a leading `this.`/`self.`."""
    return path.rsplit(".", 1)[-1]


def _sentence(words: list[str]) -> str:
    return " ".join(words).capitalize()


def _value_phrase(value: str) -> str | None:
    """A short name for a simple value (identifier, member, string), else None."""
    text = value.strip()
    if _STRING.match(text) or _LITERAL.match(text):
        return text
    if re.fullmatch(_PATH, text):
        return " ".join(_words(_bare(text)))
    return None


def _return_phrase(text: str) -> str | None:
    match = _RETURN.match(text)
    if not match:
        return None
    if match.group(1) is None:
        return "Return"
    value = _value_phrase(match.group(1))
    return f"Return {value}" if value else "Return result"


def _raise_phrase(text: str) -> str | None:
    match = _RAISE.match(text)
    return f"{match.group(1).capitalize()} {match.group(2)}" if match else None


def _step_phrase(text: str) -> str | None:
    match = _STEP.match(text)
    if not match:
        return None
    verb = "Increase" if match.group(2) == "++" else "Decrease"
    return f"{verb} {' '.join(_words(_bare(match.group(1))))}"


def _assignment_phrase(text: str) -> str | None:
    match = _ASSIGN.match(text)
    if not match:
        return None
    target, operator, value = match.group(1), match.group(2), match.group(3).strip()
    name = " ".join(_words(_bare(target)))
    if operator == "+=":
        return f"Increase {name}"
    if operator == "-=":
        return f"Decrease {name}"
    call = _CALL.match(value)
    if call and value.startswith("new "):
        return f"Create {_bare(call.group(1))}"
    if call:
        return _call_result_phrase(call.group(1), name)
    if _ARITHMETIC.search(value):
        return f"Calculate {name}"
    return f"Set {name}"


def _call_result_phrase(callee: str, target_name: str) -> str:
    words = _words(_bare(callee))
    if len(words) == 1:
        return f"{_sentence(words)} {target_name}"
    return _sentence(words)


def _call_phrase(text: str) -> str | None:
    match = _CALL.match(text)
    if not match:
        return None
    callee, arguments = match.group(1), _split_arguments(match.group(2))
    if text.startswith("new "):
        return f"Create {_bare(callee)}"
    if callee in _PRINT_CALLS:
        shown = _value_phrase(arguments[0]) if arguments else None
        return f"Print {shown}" if shown else "Print output"
    owner, _, method = callee.rpartition(".")
    method = method or callee
    owner_name = " ".join(_words(_bare(owner))) if owner and owner not in ("this", "self") else ""
    item = _value_phrase(arguments[0]) if arguments else None
    if method in _ADD_METHODS and item and owner_name:
        return f"Add {item} to {owner_name}"
    if method in _REMOVE_METHODS and item and owner_name:
        return f"Remove {item} from {owner_name}"
    words = _words(method)
    if len(words) == 1:
        subject = item or owner_name
        return f"{_sentence(words)} {subject}".strip()
    return _sentence(words)


def _split_arguments(text: str) -> list[str]:
    """Top-level comma-separated arguments (commas inside brackets or strings are kept)."""
    arguments: list[str] = []
    depth, quote, start = 0, "", 0
    for index, char in enumerate(text):
        if quote:
            if char == quote and text[index - 1] != "\\":
                quote = ""
        elif char in "\"'":
            quote = char
        elif char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        elif char == "," and depth == 0:
            arguments.append(text[start:index].strip())
            start = index + 1
    tail = text[start:].strip()
    if tail:
        arguments.append(tail)
    return arguments
