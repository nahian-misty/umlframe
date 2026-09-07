import { apiFetch } from './client';
import type { ActivityDocument } from '../types/activity';
import type { UmlDocument } from '../types/uml';

export const REVERSE_LANGUAGES = ['python', 'java', 'javascript'] as const;
export type ReverseLanguage = (typeof REVERSE_LANGUAGES)[number];

interface ReverseResponse {
  document: UmlDocument;
  control_flow: ActivityDocument | null;
}

export async function reverseToJson(
  source: string,
  language: ReverseLanguage,
): Promise<UmlDocument> {
  const result = await apiFetch<ReverseResponse>('/api/reverse', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source, language }),
  });
  return result.document;
}

export async function reverseToControlFlow(
  source: string,
  language: ReverseLanguage,
  className: string,
  methodName: string,
): Promise<ActivityDocument> {
  const result = await apiFetch<ReverseResponse>('/api/reverse', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      source,
      language,
      class_name: className,
      method_name: methodName,
    }),
  });
  if (!result.control_flow) {
    throw new Error('The server did not return control-flow for that class/method.');
  }
  return result.control_flow;
}
