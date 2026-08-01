import { apiFetch } from './client';
import type { UmlDocument } from '../types/uml';

interface ReverseResponse {
  document: UmlDocument;
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
  return result.document;
}
