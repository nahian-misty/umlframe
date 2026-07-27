from fastapi import HTTPException

from backend.generator.registry import SUPPORTED_LANGUAGES, TEMPLATES_ROOT
from backend.models.requests import GenerateCodeRequest
from backend.models.responses import CodeGenerationResponse, LanguageListResponse, TemplateListResponse
from backend.services import codegen_service


async def generate(request: GenerateCodeRequest) -> CodeGenerationResponse:
    try:
        files = codegen_service.generate_code(request.document, request.language)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Code generation failed") from exc
    return CodeGenerationResponse(files=files)


async def list_languages() -> LanguageListResponse:
    return LanguageListResponse(languages=SUPPORTED_LANGUAGES)


async def list_templates() -> TemplateListResponse:
    templates: dict[str, list[str]] = {}
    for lang in SUPPORTED_LANGUAGES:
        lang_dir = TEMPLATES_ROOT / lang
        if lang_dir.is_dir():
            templates[lang] = sorted(f.name for f in lang_dir.iterdir() if f.suffix == ".j2")
    return TemplateListResponse(templates=templates)
