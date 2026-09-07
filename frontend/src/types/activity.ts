/**
 * Mirrors backend/schemas/activity.py. The wire format for the Activity
 * Diagram sibling schema (Milestone 9 forward pipeline + Milestone 6
 * control-flow extraction). Not an extension of UmlDocument.
 */

import type { Position, Size } from './uml';

export type ActivityNodeType = 'start' | 'end' | 'action' | 'decision' | 'fork' | 'join';

export interface ActivityNode {
  id: string;
  type: ActivityNodeType;
  label: string;
  position: Position;
  size: Size;
}

export interface ActivityEdge {
  id: string;
  source: string;
  target: string;
  label: string;
}

export interface ActivityDocument {
  nodes: ActivityNode[];
  edges: ActivityEdge[];
}
