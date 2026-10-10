import { apiFetch } from './client';
import type { UmlDocument } from '../types/uml';
import { PNG_EXPORT_PIXEL_RATIO } from '../utils/constants';

interface ReverseResponse {
  document: UmlDocument;
}

function pixelsToCanvasUnits(document: UmlDocument): UmlDocument {
  const scale = 1 / PNG_EXPORT_PIXEL_RATIO;
  return {
    ...document,
    classes: document.classes.map((cls) => ({
      ...cls,
      position: { x: cls.position.x * scale, y: cls.position.y * scale },
      size: { width: cls.size.width * scale, height: cls.size.height * scale },
    })),
  };
}

export async function imageToJson(file: File): Promise<UmlDocument> {
  const formData = new FormData();
  formData.append('file', file);

  // No Content-Type header here on purpose: the browser sets the multipart
  // boundary itself when the body is a FormData instance.
  const result = await apiFetch<ReverseResponse>('/api/image-to-json', {
    method: 'POST',
    body: formData,
  });
  return pixelsToCanvasUnits(result.document);
}
