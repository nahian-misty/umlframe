from fastapi import HTTPException, UploadFile

from backend.models.responses import ReverseResponse
from backend.services import image_service


async def image_to_json(file: UploadFile) -> ReverseResponse:
    if file.content_type not in ("image/png", "image/jpeg", "image/jpg"):
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type '{file.content_type}'. Upload a PNG or JPEG.",
        )

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")

    try:
        document = image_service.image_to_document(image_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Image processing failed: {type(exc).__name__}: {exc}") from exc

    return ReverseResponse(document=document)
