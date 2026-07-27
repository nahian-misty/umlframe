from fastapi import APIRouter, File, UploadFile

from backend.api.controllers import image_controller
from backend.models.responses import ReverseResponse

router = APIRouter(prefix="/api", tags=["image"])


@router.post("/image-to-json", response_model=ReverseResponse)
async def image_to_json(file: UploadFile = File(...)) -> ReverseResponse:
    return await image_controller.image_to_json(file)
