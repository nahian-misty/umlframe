from fastapi import HTTPException

from backend.models.requests import ReverseRequest
from backend.models.responses import ReverseResponse
from backend.services import reverse_service


async def reverse_source(request: ReverseRequest) -> ReverseResponse:
    if not request.source.strip():
        raise HTTPException(status_code=422, detail="Source code is empty.")

    try:
        document = reverse_service.source_to_document(request.source, request.language, request.filename)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Reverse engineering failed: {type(exc).__name__}: {exc}") from exc

    control_flow = None
    if request.class_name is not None and request.method_name is not None:
        try:
            control_flow = reverse_service.source_to_control_flow(
                request.source, request.language, request.class_name, request.method_name
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=500, detail=f"Control-flow extraction failed: {type(exc).__name__}: {exc}"
            ) from exc

    return ReverseResponse(document=document, control_flow=control_flow)
