from fastapi import HTTPException

from backend.models.requests import GenerateActivityCodeRequest
from backend.models.responses import CodeGenerationResponse
from backend.services import activity_codegen_service


async def generate(request: GenerateActivityCodeRequest) -> CodeGenerationResponse:
    try:
        files = activity_codegen_service.generate_activity_code(
            request.document, request.language, request.function_name
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Activity code generation failed") from exc
    return CodeGenerationResponse(files=files)
