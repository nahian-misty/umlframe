import { apiFetch } from './client';
import type { UmlDocument } from '../types/uml';

interface LanguageListResponse {
  languages: string[];
}

interface CodeGenerationResponse {
  files: Record<string, string>;
}

export async function fetchLanguages(): Promise<string[]> {
  const result = await apiFetch<LanguageListResponse>('/api/languages');
  return result.languages;
}

export async function generateCode(
  document: UmlDocument,
  language: string,
): Promise<Record<string, string>> {
  const result = await apiFetch<CodeGenerationResponse>('/api/generate-code', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ document, language }),
  });
  return result.files;
}
