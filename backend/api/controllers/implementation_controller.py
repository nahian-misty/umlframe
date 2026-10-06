from fastapi import HTTPException
from starlette.concurrency import run_in_threadpool

from backend.llm.types import LlmClient, LlmError, LlmNotConfiguredError, LlmRateLimitedError
from backend.models.requests import ImplementCodeRequest
from backend.models.responses import (
    ImplementCodeResponse,
    ImplementStatusResponse,
    SkippedMethodResponse,
)
from backend.services import implementation_service


async def implement_code(request: ImplementCodeRequest, client: LlmClient) -> ImplementCodeResponse:
    try:
        # The model call blocks for seconds, so keep it off the event loop.
        result = await run_in_threadpool(
            implementation_service.implement_code,
            request.document,
            request.language,
            request.instructions,
            client,
        )
    except LlmNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LlmRateLimitedError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except LlmError as exc:
        raise HTTPException(status_code=502, detail=f"The language model failed: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Method implementation failed") from exc
    return ImplementCodeResponse(
        files=result.files,
        implemented=result.implemented,
        skipped=[SkippedMethodResponse(key=s.key, reason=s.reason) for s in result.skipped],
        models=result.models,
    )


async def implement_status(client: LlmClient) -> ImplementStatusResponse:
    return ImplementStatusResponse(available=client.is_configured)
