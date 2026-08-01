import type { Multiplicity, RelationshipType, Visibility } from './uml';

/**
 * Internal editor state. Field names match the Unified UML JSON wire format
 * (types/uml.ts) except `defaultValue`/`returnType`, which are camelCase here
 * and mapped to `default_value`/`return_type` in umlClassSerializer.ts.
 */

export interface AttributeState {
  id: string;
  name: string;
  datatype: string;
  visibility: Visibility;
  defaultValue: string | null;
  static: boolean;
  final: boolean;
}

export interface ParameterState {
  name: string;
  datatype: string;
}

export interface MethodState {
  id: string;
  name: string;
  visibility: Visibility;
  parameters: ParameterState[];
  returnType: string;
  static: boolean;
  abstract: boolean;
}

export interface UmlClassState {
  id: string;
  name: string;
  attributes: AttributeState[];
  methods: MethodState[];
  position: { x: number; y: number };
  size: { width: number; height: number };
}

export interface RelationshipState {
  id: string;
  source: string;
  destination: string;
  type: RelationshipType;
  multiplicity: Multiplicity;
  label: string;
}

export type ShapeKind = 'rectangle' | 'circle' | 'diamond' | 'line' | 'arrow';

/**
 * Freeform canvas primitives for the Milestone-1 "generic shape library"
 * requirement. NOT part of the Unified UML JSON schema — stripped out during
 * serialization in useDiagram.toDocument() and never sent to the backend.
 */
export interface GenericShape {
  id: string;
  kind: ShapeKind;
  position: { x: number; y: number };
  size: { width: number; height: number };
}

export type ToolId =
  | 'select'
  | 'pan'
  | 'rectangle'
  | 'circle'
  | 'diamond'
  | 'line'
  | 'arrow'
  | 'uml-class'
  | 'relationship';

export type SelectableKind = 'class' | 'shape' | 'relationship';

export interface SelectableRef {
  kind: SelectableKind;
  id: string;
}

export interface DiagramState {
  classes: UmlClassState[];
  relationships: RelationshipState[];
  shapes: GenericShape[];
}
