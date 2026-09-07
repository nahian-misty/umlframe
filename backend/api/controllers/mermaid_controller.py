from fastapi import HTTPException

from backend.models.requests import JsonToMermaidRequest
from backend.models.responses import MermaidResponse
from backend.services import mermaid_service


async def json_to_mermaid(request: JsonToMermaidRequest) -> MermaidResponse:
    try:
        if request.diagram_type == "activity":
            assert request.activity is not None  # enforced by JsonToMermaidRequest's validator
            diagram = mermaid_service.activity_to_mermaid(request.activity)
        else:
            assert request.document is not None  # enforced by JsonToMermaidRequest's validator
            diagram = mermaid_service.document_to_mermaid(request.document)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Mermaid generation failed") from exc
    return MermaidResponse(diagram=diagram)
