from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor

from pydantic import BaseModel

from backend.generator.class_description import ClassDescription, MethodDescription
from backend.generator.registry import REGISTRY, SUPPORTED_LANGUAGES
from backend.llm.parsing import parse_method_bodies
from backend.llm.prompts import MAX_INSTRUCTIONS_LENGTH, build_messages
from backend.llm.types import (
    LlmClient,
    LlmError,
    LlmNotConfiguredError,
    LlmRateLimitedError,
    LlmUpstreamError,
)
from backend.llm.validators import javascript_body_error, syntax_error
from backend.schemas.uml import UmlDocument
from backend.services import codegen_service

MAX_CLASSES = 15
MAX_METHODS_PER_CLASS = 30
MAX_PARALLEL_CLASSES = 3
MAX_TOKENS_PER_CLASS = 3000


class SkippedMethod(BaseModel):
    key: str
    reason: str


class ImplementationResult(BaseModel):
    files: dict[str, str]
    implemented: list[str]
    skipped: list[SkippedMethod]
    models: list[str]


class _ClassOutcome(BaseModel):
    accepted: dict[int, str] = {}
    implemented: list[str] = []
    skipped: list[SkippedMethod] = []
    model: str | None = None
    error: str | None = None
    error_kind: str | None = None


def implement_code(
    document: UmlDocument, language: str, instructions: str, client: LlmClient
) -> ImplementationResult:
    """The normal scaffold with LLM-written bodies for non-abstract methods.

    Any method the model does not deliver (or delivers invalid code for) keeps the stub and is
    listed in `skipped`. The model only ever sees data derived from the validated document and
    its reply is only ever text that gets syntax-checked, never executed."""
    if language not in REGISTRY:
        raise ValueError(f"Unsupported language: '{language}'. Supported: {SUPPORTED_LANGUAGES}")
    if not client.is_configured:
        raise LlmNotConfiguredError(
            "The LLM is not configured: set OPENROUTER_API_KEY and OPENROUTER_MODELS."
        )
    _check_limits(document)
    notes = instructions.strip()[:MAX_INSTRUCTIONS_LENGTH]

    descriptions = [
        codegen_service.describe_class(document, cls.id, language) for cls in document.classes
    ]
    jobs = [(cls.id, desc) for cls, desc in zip(document.classes, descriptions, strict=True)]
    jobs = [(cid, desc) for cid, desc in jobs if any(not m.abstract for m in desc.methods)]

    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_CLASSES) as pool:
        outcomes = list(
            pool.map(lambda job: _implement_class(document, language, notes, client, *job), jobs)
        )

    _raise_if_every_call_failed(outcomes)

    implementations = {
        (cid, index): body
        for (cid, _), outcome in zip(jobs, outcomes, strict=True)
        for index, body in outcome.accepted.items()
    }
    return ImplementationResult(
        files=codegen_service.generate_code(document, language, implementations),
        implemented=[key for outcome in outcomes for key in outcome.implemented],
        skipped=[skip for outcome in outcomes for skip in outcome.skipped],
        models=sorted({outcome.model for outcome in outcomes if outcome.model}),
    )


def _check_limits(document: UmlDocument) -> None:
    if len(document.classes) > MAX_CLASSES:
        raise ValueError(f"Too many classes for LLM implementation (maximum {MAX_CLASSES}).")
    for cls in document.classes:
        if len(cls.methods) > MAX_METHODS_PER_CLASS:
            raise ValueError(
                f"Class '{cls.name}' has too many methods for LLM implementation "
                f"(maximum {MAX_METHODS_PER_CLASS})."
            )


def _implement_class(
    document: UmlDocument,
    language: str,
    notes: str,
    client: LlmClient,
    class_id: str,
    description: ClassDescription,
) -> _ClassOutcome:
    targets = [m for m in description.methods if not m.abstract]
    keys = [m.key for m in targets]
    try:
        completion = client.complete(build_messages(description, notes, keys), MAX_TOKENS_PER_CLASS)
    except LlmError as exc:
        reason = str(exc)
        return _ClassOutcome(
            skipped=[SkippedMethod(key=key, reason=reason) for key in keys],
            error=reason,
            error_kind=type(exc).__name__,
        )

    try:
        parsed = parse_method_bodies(completion.content, keys)
    except ValueError as exc:
        return _ClassOutcome(
            skipped=[SkippedMethod(key=key, reason=str(exc)) for key in keys],
            model=completion.model,
        )

    skipped = [SkippedMethod(key=key, reason=reason) for key, reason in parsed.rejected.items()]
    candidates: dict[int, str] = {}
    by_key = {m.key: m for m in targets}
    for key, body in parsed.bodies.items():
        method = by_key[key]
        if _repeats_signature(language, method, body):
            skipped.append(SkippedMethod(key=key, reason="the model included the method signature"))
        else:
            candidates[method.index] = body

    accepted, invalid = _keep_valid_bodies(document, language, class_id, candidates)
    skipped += [SkippedMethod(key=_key_of(targets, i), reason=why) for i, why in invalid.items()]
    return _ClassOutcome(
        accepted=accepted,
        implemented=[_key_of(targets, index) for index in sorted(accepted)],
        skipped=skipped,
        model=completion.model,
    )


def _key_of(targets: list[MethodDescription], index: int) -> str:
    return next(m.key for m in targets if m.index == index)


def _repeats_signature(language: str, method: MethodDescription, body: str) -> bool:
    if language != "python":
        return False
    return re.match(rf"\s*(async\s+)?def\s+{re.escape(method.name)}\s*\(", body) is not None


def _keep_valid_bodies(
    document: UmlDocument, language: str, class_id: str, candidates: dict[int, str]
) -> tuple[dict[int, str], dict[int, str]]:
    """Keep the candidate bodies that are valid code. Python and Java bodies are spliced into the
    class and the result must parse (the whole set first, then each body alone to find the
    culprits); JavaScript bodies are checked on their own (see javascript_body_error)."""
    if not candidates:
        return {}, {}
    if language == "javascript":
        js_errors = {i: err for i, body in candidates.items() if (err := javascript_body_error(body))}
        return {i: body for i, body in candidates.items() if i not in js_errors}, js_errors

    def error_for(subset: dict[int, str]) -> str | None:
        files = codegen_service.generate_code(
            document,
            language,
            {(class_id, index): body for index, body in subset.items()},
            {class_id},
        )
        return syntax_error(language, next(iter(files.values())))

    if error_for(candidates) is None:
        return dict(candidates), {}
    accepted: dict[int, str] = {}
    invalid: dict[int, str] = {}
    for index, body in candidates.items():
        reason = error_for({index: body})
        if reason is None:
            accepted[index] = body
        else:
            invalid[index] = reason
    return accepted, invalid


def _raise_if_every_call_failed(outcomes: list[_ClassOutcome]) -> None:
    """If no class got any reply from the model, surface the cause instead of an empty result."""
    if not outcomes or any(outcome.error is None for outcome in outcomes):
        return
    kinds = {outcome.error_kind for outcome in outcomes}
    first = next(outcome for outcome in outcomes if outcome.error is not None)
    if LlmNotConfiguredError.__name__ in kinds:
        raise LlmNotConfiguredError(first.error or "The LLM is not configured.")
    if LlmRateLimitedError.__name__ in kinds:
        raise LlmRateLimitedError(first.error or "The model is rate-limited.")
    raise LlmUpstreamError(first.error or "The model could not be reached.")
