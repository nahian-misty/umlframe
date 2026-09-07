from fastapi import APIRouter

from backend.api.controllers import mermaid_controller
from backend.models.requests import JsonToMermaidRequest
from backend.models.responses import MermaidResponse

router = APIRouter(prefix="/api", tags=["mermaid"])


@router.post("/json-to-mermaid", response_model=MermaidResponse)
async def json_to_mermaid(request: JsonToMermaidRequest) -> MermaidResponse:
    return await mermaid_controller.json_to_mermaid(request)
