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
]


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
    for line in text.splitlines():
        line = _normalize(line).lstrip("+-#~ ").strip()
        # Skip lines that look like attributes or methods
        if line and ":" not in line and "(" not in line:
            return line
    return _normalize(text).strip()


def parse_attribute_line(line: str) -> ParsedAttribute | None:
    line = _normalize(line)
    if not line or "(" in line:
        return None

    visibility, line = _strip_visibility(line)

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

    if not _valid_identifier(name):
        return None

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

    paren_open = line.find("(")
    paren_close = line.rfind(")")
    if paren_open == -1:
        return None

    name = line[:paren_open].strip()
    if not _valid_identifier(name):
        return None

    param_str = line[paren_open + 1 : paren_close] if paren_close > paren_open else ""
    after_paren = line[paren_close + 1 :].strip() if paren_close != -1 else ""

    return_type = "void"
    if after_paren.startswith(":"):
        return_type = after_paren[1:].strip() or "void"

    return ParsedMethod(
        name=name,
        visibility=visibility,
        parameters=_parse_parameters(param_str),
        return_type=return_type,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _normalize(text: str) -> str:
    for wrong, right in _OCR_FIXES:
        text = text.replace(wrong, right)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _strip_visibility(line: str) -> tuple[str, str]:
    if line and line[0] in _VISIBILITY_PREFIX:
        return _VISIBILITY_PREFIX[line[0]], line[1:].strip()
    return "public", line


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
            params.append(ParsedParameter(name=name.strip(), datatype=dtype.strip()))
        else:
            params.append(ParsedParameter(name=part, datatype="Object"))
    return params


def _valid_identifier(s: str) -> bool:
    return bool(re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", s))
