import { apiFetch } from './client';
import type { UmlDocument } from '../types/uml';

interface MermaidResponse {
  diagram: string;
}

export async function jsonToMermaid(document: UmlDocument): Promise<string> {
  const result = await apiFetch<MermaidResponse>('/api/json-to-mermaid', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ document }),
  });
  return result.diagram;
}
