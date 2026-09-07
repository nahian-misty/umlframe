import { apiFetch } from './client';
import type { ActivityDocument } from '../types/activity';

interface ActivityReverseResponse {
  document: ActivityDocument;
}

interface CodeGenerationResponse {
  files: Record<string, string>;
}

export async function activityImageToJson(file: File): Promise<ActivityDocument> {
  const formData = new FormData();
  formData.append('file', file);

  // No Content-Type header: the browser sets the multipart boundary itself.
  const result = await apiFetch<ActivityReverseResponse>('/api/activity-image-to-json', {
    method: 'POST',
    body: formData,
  });
  return result.document;
}

export async function generateActivityCode(
  document: ActivityDocument,
  language: string,
  functionName: string,
): Promise<Record<string, string>> {
  const body: Record<string, unknown> = { document, language };
  if (functionName.trim()) body.function_name = functionName.trim();

  const result = await apiFetch<CodeGenerationResponse>('/api/generate-activity-code', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return result.files;
}
