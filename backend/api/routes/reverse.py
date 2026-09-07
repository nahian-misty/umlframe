from fastapi import APIRouter

from backend.api.controllers import reverse_controller
from backend.models.requests import ReverseRequest
from backend.models.responses import ReverseResponse

router = APIRouter(prefix="/api", tags=["reverse"])


@router.post("/reverse", response_model=ReverseResponse)
async def reverse_source(request: ReverseRequest) -> ReverseResponse:
    return await reverse_controller.reverse_source(request)
