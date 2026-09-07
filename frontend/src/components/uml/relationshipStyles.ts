import type { RelationshipType } from '../../types/uml';

export interface RelationshipStyle {
  dashed: boolean;
  markerStart?: string;
  markerEnd?: string;
  // Inheritance (generalization) has no UML multiplicity — a subclass isn't
  // "1..* of" its superclass — so its edge shouldn't show the "1"/"1" labels
  // every other relationship type carries.
  showMultiplicity: boolean;
}

/**
 * association: solid line, open arrowhead at destination
 * dependency: dashed line, open arrowhead at destination
 * inheritance: solid line, hollow triangle at destination
 * aggregation: solid line, hollow diamond at source (the "whole" side)
 * composition: solid line, filled diamond at source (the "whole" side)
 */
export const RELATIONSHIP_STYLES: Record<RelationshipType, RelationshipStyle> = {
  association: { dashed: false, markerEnd: 'arrow-open', showMultiplicity: true },
  dependency: { dashed: true, markerEnd: 'arrow-open', showMultiplicity: true },
  inheritance: { dashed: false, markerEnd: 'triangle-hollow', showMultiplicity: false },
  aggregation: { dashed: false, markerStart: 'diamond-hollow', showMultiplicity: true },
  composition: { dashed: false, markerStart: 'diamond-filled', showMultiplicity: true },
};

export const RELATIONSHIP_LABELS: Record<RelationshipType, string> = {
  association: 'Association',
  aggregation: 'Aggregation',
  composition: 'Composition',
  inheritance: 'Inheritance',
  dependency: 'Dependency',
};
