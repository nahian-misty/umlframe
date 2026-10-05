import base64

from fastapi import HTTPException

from backend.models.requests import ActivityDiagramImageRequest
from backend.models.responses import ActivityDiagramImageResponse
from backend.services import activity_diagram_renderer


async def activity_json_to_image(request: ActivityDiagramImageRequest) -> ActivityDiagramImageResponse:
    try:
        png_bytes = activity_diagram_renderer.render_activity_diagram(request.activity)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Activity diagram rendering failed") from exc
    return ActivityDiagramImageResponse(image_base64=base64.b64encode(png_bytes).decode("ascii"))
