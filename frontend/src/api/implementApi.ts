import { apiFetch } from './client';
import type { UmlDocument } from '../types/uml';

export interface SkippedMethod {
  key: string;
  reason: string;
}

export interface ImplementResult {
  files: Record<string, string>;
  implemented: string[];
  skipped: SkippedMethod[];
  models: string[];
}

function authHeaders(token: string): HeadersInit {
  return { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
}

/** Whether the server has an LLM configured; any failure just means "not available". */
export async function fetchImplementAvailable(token: string): Promise<boolean> {
  try {
    const result = await apiFetch<{ available: boolean }>('/api/implement-code/status', {
      headers: authHeaders(token),
    });
    return result.available;
  } catch {
    return false;
  }
}

export async function implementCode(
  token: string,
  document: UmlDocument,
  language: string,
  instructions: string,
  signal?: AbortSignal,
): Promise<ImplementResult> {
  return apiFetch<ImplementResult>('/api/implement-code', {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify({ document, language, instructions }),
    signal,
  });
}
