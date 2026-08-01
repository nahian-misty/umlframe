import type { RelationshipType } from '../../types/uml';

export interface RelationshipStyle {
  dashed: boolean;
  markerStart?: string;
  markerEnd?: string;
}

/**
 * association: solid line, open arrowhead at destination
 * dependency: dashed line, open arrowhead at destination
 * inheritance: solid line, hollow triangle at destination
 * aggregation: solid line, hollow diamond at source (the "whole" side)
 * composition: solid line, filled diamond at source (the "whole" side)
 */
export const RELATIONSHIP_STYLES: Record<RelationshipType, RelationshipStyle> = {
  association: { dashed: false, markerEnd: 'arrow-open' },
  dependency: { dashed: true, markerEnd: 'arrow-open' },
  inheritance: { dashed: false, markerEnd: 'triangle-hollow' },
  aggregation: { dashed: false, markerStart: 'diamond-hollow' },
  composition: { dashed: false, markerStart: 'diamond-filled' },
};

export const RELATIONSHIP_LABELS: Record<RelationshipType, string> = {
  association: 'Association',
  aggregation: 'Aggregation',
  composition: 'Composition',
  inheritance: 'Inheritance',
  dependency: 'Dependency',
};
