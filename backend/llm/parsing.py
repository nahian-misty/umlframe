from __future__ import annotations

import json
import re

from pydantic import BaseModel

MAX_BODY_LENGTH = 4000
_FENCE = re.compile(r"^\s*```[a-zA-Z0-9_+-]*\s*\n(?P<body>.*?)\n?\s*```\s*$", re.DOTALL)


class ParsedBodies(BaseModel):
    """What could be read from a model reply: usable bodies, and why the others were not."""

    bodies: dict[str, str]
    rejected: dict[str, str]


def _strip_fences(text: str) -> str:
    match = _FENCE.match(text)
    return match.group("body") if match else text.strip()


def _extract_object(text: str) -> object:
    cleaned = _strip_fences(text)
    try:
        return json.loads(cleaned)
    except ValueError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end <= start:
            raise
        return json.loads(cleaned[start : end + 1])


def parse_method_bodies(text: str, requested_keys: list[str]) -> ParsedBodies:
    """Read `{"methods": {key: body}}` (or a bare `{key: body}`) from a model reply.

    Unknown keys are dropped; requested keys that are missing, not text, empty or too long are
    reported in `rejected`. Raises ValueError when the reply is not a JSON object at all."""
    try:
        data = _extract_object(text)
    except ValueError as exc:
        raise ValueError("The model did not return valid JSON") from exc
    if not isinstance(data, dict):
        raise ValueError("The model did not return a JSON object")
    methods = data.get("methods", data)
    if not isinstance(methods, dict):
        raise ValueError("The model's 'methods' value is not an object")

    bodies: dict[str, str] = {}
    rejected: dict[str, str] = {}
    for key in requested_keys:
        value = methods.get(key)
        if value is None:
            rejected[key] = "the model returned no body"
        elif not isinstance(value, str) or not value.strip():
            rejected[key] = "the model returned an empty or non-text body"
        else:
            body = _strip_fences(value)
            if len(body) > MAX_BODY_LENGTH:
                rejected[key] = f"the body was longer than {MAX_BODY_LENGTH} characters"
            else:
                bodies[key] = body
    return ParsedBodies(bodies=bodies, rejected=rejected)
