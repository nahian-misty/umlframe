import { apiFetch } from './client';
import { REVERSE_LANGUAGES, type ReverseLanguage } from './reverseApi';
import type { ActivityDocument } from '../types/activity';
import type { UmlDocument } from '../types/uml';

export const PROJECTS_PAGE_SIZE = 12;

export type ProjectSort = 'updated' | 'name';

export type ProjectType = 'uml' | 'activity';

export const PROJECT_TYPE_LABELS: Record<ProjectType, string> = {
  uml: 'UML class diagram',
  activity: 'Activity diagram',
};

export interface ProjectPage {
  projects: ProjectSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface CodeToUmlInput {
  language: ReverseLanguage;
  source: string;
}

export interface CodeToActivityInput {
  language: ReverseLanguage;
  className: string;
  methodName: string;
  source: string;
}

export interface CodeInputs {
  codeToUml: CodeToUmlInput;
  codeToActivity: CodeToActivityInput;
}

export const EMPTY_CODE_INPUTS: CodeInputs = {
  codeToUml: { language: 'python', source: '' },
  codeToActivity: { language: 'python', className: '', methodName: '', source: '' },
};

interface CodeInputsWire {
  code_to_uml: { language: string; source: string };
  code_to_activity: { language: string; class_name: string; method_name: string; source: string };
}

function toLanguage(value: string): ReverseLanguage {
  return (REVERSE_LANGUAGES as readonly string[]).includes(value)
    ? (value as ReverseLanguage)
    : 'python';
}

function codeInputsFromWire(wire: CodeInputsWire | undefined): CodeInputs {
  if (!wire) return EMPTY_CODE_INPUTS;
  return {
    codeToUml: { language: toLanguage(wire.code_to_uml.language), source: wire.code_to_uml.source },
    codeToActivity: {
      language: toLanguage(wire.code_to_activity.language),
      className: wire.code_to_activity.class_name,
      methodName: wire.code_to_activity.method_name,
      source: wire.code_to_activity.source,
    },
  };
}

function codeInputsToWire(inputs: CodeInputs): CodeInputsWire {
  return {
    code_to_uml: { language: inputs.codeToUml.language, source: inputs.codeToUml.source },
    code_to_activity: {
      language: inputs.codeToActivity.language,
      class_name: inputs.codeToActivity.className,
      method_name: inputs.codeToActivity.methodName,
      source: inputs.codeToActivity.source,
    },
  };
}

export interface ClassBoxSummary {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface ProjectSummary {
  id: number;
  name: string;
  projectType: ProjectType;
  updatedAt: string;
  classCount: number;
  relationshipCount: number;
  nodeCount: number;
  classBoxes: ClassBoxSummary[];
}

export interface Project extends ProjectSummary {
  document: UmlDocument;
  activityDocument: ActivityDocument | null;
  codeInputs: CodeInputs;
  createdAt: string;
}

interface ProjectSummaryWire {
  id: number;
  name: string;
  project_type: ProjectType;
  updated_at: string;
  class_count: number;
  relationship_count: number;
  node_count: number;
  class_boxes: ClassBoxSummary[];
}

interface ProjectWire {
  id: number;
  name: string;
  project_type: ProjectType;
  document: UmlDocument;
  activity_document: ActivityDocument | null;
  code_inputs?: CodeInputsWire;
  created_at: string;
  updated_at: string;
}

function summaryFromWire(wire: ProjectSummaryWire): ProjectSummary {
  return {
    id: wire.id,
    name: wire.name,
    projectType: wire.project_type,
    updatedAt: wire.updated_at,
    classCount: wire.class_count,
    relationshipCount: wire.relationship_count,
    nodeCount: wire.node_count,
    classBoxes: wire.class_boxes,
  };
}

function projectFromWire(wire: ProjectWire): Project {
  return {
    id: wire.id,
    name: wire.name,
    projectType: wire.project_type,
    document: wire.document,
    activityDocument: wire.activity_document ?? null,
    codeInputs: codeInputsFromWire(wire.code_inputs),
    createdAt: wire.created_at,
    updatedAt: wire.updated_at,
    classCount: wire.document.classes.length,
    relationshipCount: wire.document.relationships.length,
    nodeCount: wire.activity_document?.nodes.length ?? 0,
    classBoxes: wire.document.classes.map((cls) => ({
      x: cls.position.x,
      y: cls.position.y,
      width: cls.size.width,
      height: cls.size.height,
    })),
  };
}

function authHeaders(token: string): HeadersInit {
  return { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
}

export async function listProjects(
  token: string,
  query: {
    search?: string;
    sort?: ProjectSort;
    limit?: number;
    offset?: number;
    projectType?: ProjectType;
  } = {},
): Promise<ProjectPage> {
  const params = new URLSearchParams({
    search: query.search ?? '',
    sort: query.sort ?? 'updated',
    limit: String(query.limit ?? PROJECTS_PAGE_SIZE),
    offset: String(query.offset ?? 0),
  });
  if (query.projectType) params.set('project_type', query.projectType);
  const result = await apiFetch<{
    projects: ProjectSummaryWire[];
    total: number;
    limit: number;
    offset: number;
  }>(`/api/projects?${params.toString()}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return {
    projects: result.projects.map(summaryFromWire),
    total: result.total,
    limit: result.limit,
    offset: result.offset,
  };
}

export async function createProject(
  token: string,
  name: string,
  projectType: ProjectType = 'uml',
): Promise<Project> {
  const result = await apiFetch<ProjectWire>('/api/projects', {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify({ name, project_type: projectType }),
  });
  return projectFromWire(result);
}

export async function getProject(token: string, id: number | string): Promise<Project> {
  const result = await apiFetch<ProjectWire>(`/api/projects/${id}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return projectFromWire(result);
}

export async function updateProject(
  token: string,
  id: number | string,
  patch: {
    name?: string;
    document?: UmlDocument;
    activity_document?: ActivityDocument;
    codeInputs?: CodeInputs;
  },
): Promise<Project> {
  const { codeInputs, ...rest } = patch;
  const result = await apiFetch<ProjectWire>(`/api/projects/${id}`, {
    method: 'PUT',
    headers: authHeaders(token),
    body: JSON.stringify({
      ...rest,
      ...(codeInputs ? { code_inputs: codeInputsToWire(codeInputs) } : {}),
    }),
  });
  return projectFromWire(result);
}

export async function deleteProject(token: string, id: number | string): Promise<void> {
  await apiFetch<{ status: string }>(`/api/projects/${id}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  });
}
