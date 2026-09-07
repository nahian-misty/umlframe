from fastapi import APIRouter, File, UploadFile

from backend.api.controllers import activity_image_controller
from backend.models.responses import ActivityReverseResponse

router = APIRouter(prefix="/api", tags=["activity-image"])


@router.post("/activity-image-to-json", response_model=ActivityReverseResponse)
async def activity_image_to_json(file: UploadFile = File(...)) -> ActivityReverseResponse:
    return await activity_image_controller.activity_image_to_json(file)
