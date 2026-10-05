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

export interface MethodControlFlow {
  className: string;
  methodName: string;
  controlFlow: ActivityDocument | null;
  error: string | null;
}

export function methodKey(method: Pick<MethodControlFlow, 'className' | 'methodName'>): string {
  return `${method.className}.${method.methodName}`;
}

export async function reverseToControlFlows(
  source: string,
  language: ReverseLanguage,
): Promise<MethodControlFlow[]> {
  const result = await apiFetch<{
    methods: {
      class_name: string;
      method_name: string;
      control_flow: ActivityDocument | null;
      error: string | null;
    }[];
  }>('/api/reverse-control-flows', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source, language }),
  });
  return result.methods.map((m) => ({
    className: m.class_name,
    methodName: m.method_name,
    controlFlow: m.control_flow,
    error: m.error,
  }));
}
