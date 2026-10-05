from fastapi import APIRouter

from backend.api.controllers import activity_render_controller
from backend.models.requests import ActivityDiagramImageRequest
from backend.models.responses import ActivityDiagramImageResponse

router = APIRouter(prefix="/api", tags=["activity_render"])


@router.post("/activity-json-to-image", response_model=ActivityDiagramImageResponse)
async def activity_json_to_image(request: ActivityDiagramImageRequest) -> ActivityDiagramImageResponse:
    return await activity_render_controller.activity_json_to_image(request)
