from fastapi import APIRouter

from backend.api.controllers import codegen_controller
from backend.models.requests import GenerateCodeRequest
from backend.models.responses import CodeGenerationResponse, LanguageListResponse, TemplateListResponse

router = APIRouter(prefix="/api", tags=["codegen"])


@router.post("/generate-code", response_model=CodeGenerationResponse)
async def generate_code(request: GenerateCodeRequest) -> CodeGenerationResponse:
    return await codegen_controller.generate(request)


@router.get("/languages", response_model=LanguageListResponse)
async def list_languages() -> LanguageListResponse:
    return await codegen_controller.list_languages()


@router.get("/templates", response_model=TemplateListResponse)
async def list_templates() -> TemplateListResponse:
    return await codegen_controller.list_templates()
