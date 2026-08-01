import { apiFetch } from './client';
import type { UmlDocument } from '../types/uml';

export interface ClassBoxSummary {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface ProjectSummary {
  id: number;
  name: string;
  updatedAt: string;
  classCount: number;
  relationshipCount: number;
  classBoxes: ClassBoxSummary[];
}

export interface Project extends ProjectSummary {
  document: UmlDocument;
  createdAt: string;
}

interface ProjectSummaryWire {
  id: number;
  name: string;
  updated_at: string;
  class_count: number;
  relationship_count: number;
  class_boxes: ClassBoxSummary[];
}

interface ProjectWire {
  id: number;
  name: string;
  document: UmlDocument;
  created_at: string;
  updated_at: string;
}

function summaryFromWire(wire: ProjectSummaryWire): ProjectSummary {
  return {
    id: wire.id,
    name: wire.name,
    updatedAt: wire.updated_at,
    classCount: wire.class_count,
    relationshipCount: wire.relationship_count,
    classBoxes: wire.class_boxes,
  };
}

function projectFromWire(wire: ProjectWire): Project {
  return {
    id: wire.id,
    name: wire.name,
    document: wire.document,
    createdAt: wire.created_at,
    updatedAt: wire.updated_at,
    classCount: wire.document.classes.length,
    relationshipCount: wire.document.relationships.length,
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

export async function listProjects(token: string): Promise<ProjectSummary[]> {
  const result = await apiFetch<{ projects: ProjectSummaryWire[] }>('/api/projects', {
    headers: { Authorization: `Bearer ${token}` },
  });
  return result.projects.map(summaryFromWire);
}

export async function createProject(token: string, name: string): Promise<Project> {
  const result = await apiFetch<ProjectWire>('/api/projects', {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify({ name }),
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
  patch: { name?: string; document?: UmlDocument },
): Promise<Project> {
  const result = await apiFetch<ProjectWire>(`/api/projects/${id}`, {
    method: 'PUT',
    headers: authHeaders(token),
    body: JSON.stringify(patch),
  });
  return projectFromWire(result);
}

export async function deleteProject(token: string, id: number | string): Promise<void> {
  await apiFetch<{ status: string }>(`/api/projects/${id}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  });
}
