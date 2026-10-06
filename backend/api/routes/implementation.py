from fastapi import APIRouter, Depends

from backend.api.controllers import implementation_controller
from backend.api.dependencies.auth import get_current_user
from backend.api.dependencies.llm import get_llm_client
from backend.db.models import User
from backend.llm.types import LlmClient
from backend.models.requests import ImplementCodeRequest
from backend.models.responses import ImplementCodeResponse, ImplementStatusResponse

router = APIRouter(prefix="/api", tags=["implementation"])


@router.post("/implement-code", response_model=ImplementCodeResponse)
async def implement_code(
    request: ImplementCodeRequest,
    current_user: User = Depends(get_current_user),
    client: LlmClient = Depends(get_llm_client),
) -> ImplementCodeResponse:
    return await implementation_controller.implement_code(request, client)


@router.get("/implement-code/status", response_model=ImplementStatusResponse)
async def implement_status(
    current_user: User = Depends(get_current_user),
    client: LlmClient = Depends(get_llm_client),
) -> ImplementStatusResponse:
    return await implementation_controller.implement_status(client)
