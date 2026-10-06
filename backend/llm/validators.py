from __future__ import annotations

import ast
import re

import esprima
import javalang
from esprima.error_handler import Error as EsprimaError
from javalang.tokenizer import LexerError

_PRIVATE_NAME = re.compile(r"#(?=[A-Za-z_$])")


def _without_private_names(source: str) -> str:
    """esprima predates class private names (#x); rename them so the rest still gets checked."""
    return _PRIVATE_NAME.sub("__private_", source)


def javascript_body_error(body: str) -> str | None:
    """None when `body` is valid inside a function; the scaffold itself uses class fields that
    esprima cannot parse, so JavaScript bodies are checked on their own, never spliced."""
    try:
        esprima.parseScript(f"function __body__() {{\n{_without_private_names(body)}\n}}")
    except EsprimaError as exc:
        return f"javascript syntax error: {exc}"
    return None


def syntax_error(language: str, source: str) -> str | None:
    """None when `source` parses in `language`; otherwise a short reason. Never executes it.
    (JavaScript sources with class fields are out of esprima's reach: use javascript_body_error.)"""
    try:
        if language == "python":
            ast.parse(source)
        elif language == "java":
            javalang.parse.parse(source)
        elif language == "javascript":
            esprima.parseModule(_without_private_names(source))
        else:
            return f"unsupported language '{language}'"
    except SyntaxError as exc:
        return f"python syntax error: {exc.msg}"
    except (javalang.parser.JavaParserBaseException, LexerError) as exc:
        return f"java syntax error: {getattr(exc, 'description', None) or type(exc).__name__}"
    except EsprimaError as exc:
        return f"javascript syntax error: {exc}"
    return None
