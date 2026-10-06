/**
 * Mirrors backend/schemas/uml.py exactly. This is the wire format for the
 * Unified UML JSON — the only shape the backend accepts or returns.
 */

export type Visibility = 'public' | 'private' | 'protected' | 'package';

/** Shown above a class name: «interface», «abstract», or nothing special for a class. */
export type ClassKind = 'class' | 'interface' | 'abstract';

export type RelationshipType =
  'association' | 'aggregation' | 'composition' | 'inheritance' | 'dependency' | 'realization';

export interface Parameter {
  name: string;
  datatype: string;
}

export interface Attribute {
  name: string;
  datatype: string;
  visibility: Visibility;
  default_value: string | null;
  static: boolean;
  final: boolean;
}

export interface Method {
  name: string;
  visibility: Visibility;
  parameters: Parameter[];
  return_type: string;
  static: boolean;
  abstract: boolean;
}

export interface Position {
  x: number;
  y: number;
}

export interface Size {
  width: number;
  height: number;
}

export interface UmlClass {
  id: string;
  name: string;
  kind: ClassKind;
  attributes: Attribute[];
  methods: Method[];
  position: Position;
  size: Size;
}

export interface Multiplicity {
  source: string;
  destination: string;
}

export interface Relationship {
  id: string;
  source: string;
  destination: string;
  type: RelationshipType;
  multiplicity: Multiplicity;
  label: string;
}

export interface UmlDocument {
  classes: UmlClass[];
  relationships: Relationship[];
}
