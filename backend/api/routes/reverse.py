from fastapi import APIRouter

from backend.api.controllers import reverse_controller
from backend.models.requests import ControlFlowsRequest, ReverseRequest
from backend.models.responses import ControlFlowsResponse, ReverseResponse

router = APIRouter(prefix="/api", tags=["reverse"])


@router.post("/reverse", response_model=ReverseResponse)
async def reverse_source(request: ReverseRequest) -> ReverseResponse:
    return await reverse_controller.reverse_source(request)


@router.post("/reverse-control-flows", response_model=ControlFlowsResponse)
async def reverse_control_flows(request: ControlFlowsRequest) -> ControlFlowsResponse:
    return await reverse_controller.reverse_control_flows(request)
