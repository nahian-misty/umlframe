from fastapi import HTTPException, UploadFile
from pydantic import ValidationError

from backend.models.responses import ActivityReverseResponse
from backend.services import activity_image_service


async def activity_image_to_json(file: UploadFile) -> ActivityReverseResponse:
    if file.content_type not in ("image/png", "image/jpeg", "image/jpg"):
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type '{file.content_type}'. Upload a PNG or JPEG.",
        )

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")

    try:
        document = activity_image_service.activity_image_to_document(image_bytes)
    except (ValueError, ValidationError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Activity image processing failed: {type(exc).__name__}: {exc}",
        ) from exc

    return ActivityReverseResponse(document=document)
