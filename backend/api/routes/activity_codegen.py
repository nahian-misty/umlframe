from fastapi import APIRouter

from backend.api.controllers import activity_codegen_controller
from backend.models.requests import GenerateActivityCodeRequest
from backend.models.responses import CodeGenerationResponse

router = APIRouter(prefix="/api", tags=["activity-codegen"])


@router.post("/generate-activity-code", response_model=CodeGenerationResponse)
async def generate_activity_code(request: GenerateActivityCodeRequest) -> CodeGenerationResponse:
    return await activity_codegen_controller.generate(request)
