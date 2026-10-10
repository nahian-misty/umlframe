from __future__ import annotations

import re
from dataclasses import dataclass

_VISIBILITY_PREFIX: dict[str, str] = {
    "+": "public",
    "-": "private",
    "#": "protected",
    "~": "package",
}

_OCR_FIXES: list[tuple[str, str]] = [
    (";", ":"),
    ("—", "-"),  # em-dash
    ("–", "-"),  # en-dash
    ("·", "."),  # middle dot
    ("“", '"'),  # curly double quotes
    ("”", '"'),
    ("‘", "'"),  # curly single quotes
    ("’", "'"),
    ("{)", "()"),  # "(" read as "{"
    ("(}", "()"),
]

# Characters Tesseract adds after a line of text from a border or divider it brushed.
_TRAILING_NOISE = re.compile(r"[\s|_\\/!]+$")

# An "I" (capital i) is read as "l" in sans-serif type. Camel-case words beginning
# "is" or containing "In" are the common victims.
_OCR_IDENTIFIER_FIXES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^ls(?=[A-Z])"), "is"),
    (re.compile(r"(?<=[a-z])ln(?=[A-Z])"), "In"),
]

_LEADING_QUOTE = re.compile(r"^[\"']\s*(?=[A-Za-z_])")
_STEREOTYPE_BRACKETS = "<>«»{}[]()"
_STEREOTYPE_WORDS = {"interface": "interface", "abstract": "abstract"}
_PLAIN_STEREOTYPE = "class"
_PLACEHOLDER_ROWS = frozenset({"attribute", "method"})


@dataclass
class ParsedParameter:
    name: str
    datatype: str


@dataclass
class ParsedAttribute:
    name: str
    datatype: str
    visibility: str
    default_value: str | None = None


@dataclass
class ParsedMethod:
    name: str
    visibility: str
    parameters: list[ParsedParameter]
    return_type: str


# ---------------------------------------------------------------------------
# Public parsers
# ---------------------------------------------------------------------------


def parse_class_name(text: str) -> str:
    """Extract a clean class name from the top-compartment OCR text."""
    return parse_class_header(text)[0]


def parse_class_header(text: str) -> tuple[str, str | None]:
    """(class name, stereotype) from the top-compartment OCR text. The stereotype is
    "interface" or "abstract" when a «interface» / <<abstract>> / {abstract} marker
    is written above or beside the name, else None."""
    stereotype: str | None = None
    name = ""
    for raw in text.splitlines():
        line = _normalize(raw)
        marker = _stereotype_in(line)
        if marker is not None:
            stereotype = stereotype or marker
            line = _strip_stereotype(line)
        line = line.lstrip("+-#~ ").strip()
        # Skip lines that look like attributes or methods
        if line and ":" not in line and "(" not in line and not name:
            name = line
    return (name or _normalize(text).strip()), stereotype


def _stereotype_in(line: str) -> str | None:
    if not any(char in line for char in _STEREOTYPE_BRACKETS):
        return None
    lowered = line.lower()
    for word, stereotype in _STEREOTYPE_WORDS.items():
        if word in lowered:
            return stereotype
    if _PLAIN_STEREOTYPE in lowered:
        return _PLAIN_STEREOTYPE
    return None


def _strip_stereotype(line: str) -> str:
    """The line with any bracketed stereotype ("<<interface>>", "{abstract}") removed."""
    return re.sub(r"[<«{\[(]{1,2}\s*[A-Za-z ]+?\s*[>»}\])]{1,2}", " ", line).strip()


_MULTIPLICITY = re.compile(r"^(\d+|\*|n)(?:\.{1,3}(\d+|\*|n)?)?$")


def parse_multiplicity(text: str) -> str | None:
    """A UML multiplicity ("1", "*", "0..1", "1..*") from OCR text, tolerating the
    dots being lost or doubled ("0.*", "0.", "1,.*"), or None if it is not one."""
    cleaned = re.sub(r"[\s'\"]", "", text.replace(",", "."))
    match = _MULTIPLICITY.match(cleaned)
    if match is None:
        return None
    low, high = match.group(1), match.group(2)
    if "." not in cleaned:
        return "*" if low == "n" else low
    upper = "*" if high in (None, "n") else high
    return f"{'*' if low == 'n' else low}..{upper}"


def is_method_line(line: str) -> bool:
    """Whether a line reads as a call signature, after OCR repairs ("quack{)")."""
    return "(" in _normalize(line)


def parse_attribute_line(line: str) -> ParsedAttribute | None:
    line = _normalize(line)
    if not line or "(" in line:
        return None

    visibility, line = _strip_visibility(line)
    if line.lower() in _PLACEHOLDER_ROWS:
        return None

    default_value: str | None = None
    if "=" in line:
        parts = line.split("=", 1)
        line = parts[0].strip()
        default_value = parts[1].strip() or None

    if ":" in line:
        name_part, type_part = line.split(":", 1)
        name = name_part.strip()
        datatype = type_part.strip() or "Object"
    else:
        name = line.strip()
        datatype = "Object"

    name = _fix_identifier(name)
    if not _valid_identifier(name):
        return None

    datatype = _clean_type(datatype)
    if not _is_type_name(datatype) or _is_plain_word_value(datatype):
        # "x : 400ft" or "color : blue" gives a value, not a type: keep it, quoted so
        # generated code stays valid, as the default of a String.
        default_value = default_value or f'"{datatype}"'
        datatype = "String"

    return ParsedAttribute(
        name=name,
        datatype=datatype,
        visibility=visibility,
        default_value=default_value,
    )


def parse_method_line(line: str) -> ParsedMethod | None:
    line = _normalize(line)
    if not line or "(" not in line:
        return None

    visibility, line = _strip_visibility(line)
    if line.lower() in _PLACEHOLDER_ROWS:
        return None

    paren_open = line.find("(")
    paren_close = line.rfind(")")
    if paren_open == -1:
        return None

    name = _fix_identifier(line[:paren_open].strip())
    if not _valid_identifier(name):
        return None

    truncated = paren_close < paren_open
    param_str = line[paren_open + 1 : paren_close] if not truncated else line[paren_open + 1 :]
    after_paren = line[paren_close + 1 :].strip() if not truncated else ""

    return_type = "void"
    if after_paren.startswith(":"):
        return_type = _clean_type(after_paren[1:]) or "void"
        if not _is_type_name(return_type) or return_type.endswith("."):
            return_type = "void"  # ": 5" is not a type; guessing one would be invention

    return ParsedMethod(
        name=name,
        visibility=visibility,
        parameters=_parse_parameters(_drop_truncated_tail(param_str) if truncated else param_str),
        return_type=return_type,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _normalize(text: str) -> str:
    for wrong, right in _OCR_FIXES:
        text = text.replace(wrong, right)
    text = re.sub(r"\s+", " ", text)
    return _TRAILING_NOISE.sub("", text.strip())


def _fix_identifier(name: str) -> str:
    for pattern, replacement in _OCR_IDENTIFIER_FIXES:
        name = pattern.sub(replacement, name)
    return name


_TYPE_TOKEN = re.compile(
    r"^[A-Za-z_][\w.]*(<[\w., ?<>]*>|\[[A-Za-z_][\w., ?\[\]]*\])?(\[\])*$"
)


def _is_type_name(datatype: str) -> bool:
    return bool(_TYPE_TOKEN.match(datatype))


_LOWERCASE_TYPES = frozenset(
    {"int", "long", "short", "byte", "char", "float", "double", "boolean", "bool", "void",
     "string", "str", "date", "number", "object", "any", "list", "map", "set"}
)


def _is_plain_word_value(datatype: str) -> bool:
    """A lowercase word that is not a known primitive ("blue", "no") reads as a value."""
    return datatype.isalpha() and datatype.islower() and datatype not in _LOWERCASE_TYPES


def _clean_type(datatype: str) -> str:
    """An array type with its spacing and any lost "[" repaired: "String[ ]" and
    "String ]" both become "String[]"."""
    datatype = re.sub(r"\s*\[\s*\]", "[]", datatype.strip())
    return re.sub(r"\s+\]$", "[]", datatype)


def _strip_visibility(line: str) -> tuple[str, str]:
    line = _LEADING_QUOTE.sub("-", line)
    if line and line[0] in _VISIBILITY_PREFIX:
        return _VISIBILITY_PREFIX[line[0]], line[1:].strip()
    return "public", line


def _drop_truncated_tail(param_str: str) -> str:
    """A signature cut off by an ellipsis ("findBook(title: String...") ends in a parameter
    whose type may be incomplete: that last parameter is dropped rather than guessed."""
    return param_str.rpartition(",")[0]


def _parse_parameters(param_str: str) -> list[ParsedParameter]:
    if not param_str.strip():
        return []
    params: list[ParsedParameter] = []
    for part in param_str.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            name, dtype = part.split(":", 1)
            params.append(ParsedParameter(name=name.strip(), datatype=_clean_type(dtype)))
        else:
            params.append(ParsedParameter(name=part, datatype="Object"))
    return params


def _valid_identifier(s: str) -> bool:
    return bool(re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", s))
