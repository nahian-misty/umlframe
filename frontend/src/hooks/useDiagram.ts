import { useCallback, useRef, useState } from 'react';

import { useCanvas, type UseCanvasResult } from './useCanvas';
import { useSelection, type UseSelectionResult } from './useSelection';
import { classFromWire, classToWire } from '../components/uml/umlClassSerializer';
import {
  DEFAULT_CLASS_SIZE,
  DEFAULT_MULTIPLICITY,
  DEFAULT_SHAPE_SIZE,
  DUPLICATE_OFFSET,
  MIN_CLASS_SIZE,
  MIN_SHAPE_SIZE,
} from '../utils/constants';
import { boundsOfRects, type Point, type Rect } from '../utils/geometry';
import { classId, nextSeqFromIds, relId, shapeId } from '../utils/id';
import type {
  DiagramState,
  GenericShape,
  RelationshipState,
  ShapeKind,
  UmlClassState,
} from '../types/diagram';
import type { RelationshipType, UmlDocument } from '../types/uml';

const EMPTY_STATE: DiagramState = { classes: [], relationships: [], shapes: [] };

export interface UseDiagramResult extends UseCanvasResult, UseSelectionResult {
  classes: UmlClassState[];
  relationships: RelationshipState[];
  shapes: GenericShape[];

  addClass: (position: Point) => string;
  updateClass: (id: string, patch: Partial<Omit<UmlClassState, 'id'>>) => void;
  moveClasses: (updates: { id: string; x: number; y: number }[]) => void;
  resizeClass: (id: string, size: { width: number; height: number }, position?: Point) => void;
  deleteClasses: (ids: string[]) => void;

  addRelationship: (source: string, destination: string, type: RelationshipType) => string;
  updateRelationship: (id: string, patch: Partial<Omit<RelationshipState, 'id'>>) => void;
  deleteRelationships: (ids: string[]) => void;

  addShape: (kind: ShapeKind, position: Point, size?: { width: number; height: number }) => string;
  moveShapes: (updates: { id: string; x: number; y: number }[]) => void;
  resizeShape: (id: string, size: { width: number; height: number }, position?: Point) => void;
  deleteShapes: (ids: string[]) => void;

  duplicateSelected: () => void;
  deleteSelected: () => void;

  toDocument: () => UmlDocument;
  loadDocument: (doc: UmlDocument) => void;
  getContentBounds: () => Rect | null;
}

export function useDiagram(): UseDiagramResult {
  const [state, setState] = useState<DiagramState>(EMPTY_STATE);
  const classSeqRef = useRef(1);
  const relSeqRef = useRef(1);
  const shapeSeqRef = useRef(1);

  const canvas = useCanvas();
  const selection = useSelection();

  const addClass = useCallback(
    (position: Point): string => {
      const id = classId(classSeqRef.current++);
      const newClass: UmlClassState = {
        id,
        name: `NewClass${id.replace('class_', '')}`,
        attributes: [],
        methods: [],
        position,
        size: { ...DEFAULT_CLASS_SIZE },
      };
      setState((prev) => ({ ...prev, classes: [...prev.classes, newClass] }));
      selection.select({ kind: 'class', id });
      return id;
    },
    [selection],
  );

  const updateClass = useCallback((id: string, patch: Partial<Omit<UmlClassState, 'id'>>) => {
    setState((prev) => ({
      ...prev,
      classes: prev.classes.map((c) => (c.id === id ? { ...c, ...patch } : c)),
    }));
  }, []);

  const moveClasses = useCallback((updates: { id: string; x: number; y: number }[]) => {
    setState((prev) => ({
      ...prev,
      classes: prev.classes.map((c) => {
        const u = updates.find((u) => u.id === c.id);
        return u ? { ...c, position: { x: u.x, y: u.y } } : c;
      }),
    }));
  }, []);

  const resizeClass = useCallback(
    (id: string, size: { width: number; height: number }, position?: Point) => {
      const clamped = {
        width: Math.max(size.width, MIN_CLASS_SIZE.width),
        height: Math.max(size.height, MIN_CLASS_SIZE.height),
      };
      setState((prev) => ({
        ...prev,
        classes: prev.classes.map((c) =>
          c.id === id ? { ...c, size: clamped, position: position ?? c.position } : c,
        ),
      }));
    },
    [],
  );

  const deleteClasses = useCallback((ids: string[]) => {
    const idSet = new Set(ids);
    setState((prev) => ({
      ...prev,
      classes: prev.classes.filter((c) => !idSet.has(c.id)),
      relationships: prev.relationships.filter(
        (r) => !idSet.has(r.source) && !idSet.has(r.destination),
      ),
    }));
  }, []);

  const addRelationship = useCallback(
    (source: string, destination: string, type: RelationshipType): string => {
      const id = relId(relSeqRef.current++);
      const newRel: RelationshipState = {
        id,
        source,
        destination,
        type,
        multiplicity: { ...DEFAULT_MULTIPLICITY },
        label: '',
      };
      setState((prev) => ({ ...prev, relationships: [...prev.relationships, newRel] }));
      return id;
    },
    [],
  );

  const updateRelationship = useCallback(
    (id: string, patch: Partial<Omit<RelationshipState, 'id'>>) => {
      setState((prev) => ({
        ...prev,
        relationships: prev.relationships.map((r) => (r.id === id ? { ...r, ...patch } : r)),
      }));
    },
    [],
  );

  const deleteRelationships = useCallback((ids: string[]) => {
    const idSet = new Set(ids);
    setState((prev) => ({
      ...prev,
      relationships: prev.relationships.filter((r) => !idSet.has(r.id)),
    }));
  }, []);

  const addShape = useCallback(
    (kind: ShapeKind, position: Point, size?: { width: number; height: number }): string => {
      const id = shapeId(shapeSeqRef.current++);
      const newShape: GenericShape = {
        id,
        kind,
        position,
        size: size ?? { ...DEFAULT_SHAPE_SIZE },
      };
      setState((prev) => ({ ...prev, shapes: [...prev.shapes, newShape] }));
      selection.select({ kind: 'shape', id });
      return id;
    },
    [selection],
  );

  const moveShapes = useCallback((updates: { id: string; x: number; y: number }[]) => {
    setState((prev) => ({
      ...prev,
      shapes: prev.shapes.map((s) => {
        const u = updates.find((u) => u.id === s.id);
        return u ? { ...s, position: { x: u.x, y: u.y } } : s;
      }),
    }));
  }, []);

  const resizeShape = useCallback(
    (id: string, size: { width: number; height: number }, position?: Point) => {
      const clamped = {
        width: Math.max(size.width, MIN_SHAPE_SIZE.width),
        height: Math.max(size.height, MIN_SHAPE_SIZE.height),
      };
      setState((prev) => ({
        ...prev,
        shapes: prev.shapes.map((s) =>
          s.id === id ? { ...s, size: clamped, position: position ?? s.position } : s,
        ),
      }));
    },
    [],
  );

  const deleteShapes = useCallback((ids: string[]) => {
    const idSet = new Set(ids);
    setState((prev) => ({ ...prev, shapes: prev.shapes.filter((s) => !idSet.has(s.id)) }));
  }, []);

  const duplicateSelected = useCallback(() => {
    const classIds = selection.selectedIdsOfKind('class');
    const shapeIds = selection.selectedIdsOfKind('shape');
    if (classIds.length === 0 && shapeIds.length === 0) return;

    // Computed here (not inside the setState updater) because the updater
    // must stay pure: React 18 StrictMode double-invokes updaters in dev to
    // surface impure side effects, which would double-increment the id refs
    // and duplicate entries if id generation lived inside the updater.
    const newClasses: UmlClassState[] = state.classes
      .filter((c) => classIds.includes(c.id))
      .map((c) => {
        const newId = classId(classSeqRef.current++);
        return {
          ...c,
          id: newId,
          attributes: c.attributes.map((a, i) => ({ ...a, id: `${newId}_attr_${i}` })),
          methods: c.methods.map((m, i) => ({ ...m, id: `${newId}_method_${i}` })),
          position: { x: c.position.x + DUPLICATE_OFFSET.x, y: c.position.y + DUPLICATE_OFFSET.y },
        };
      });
    const newShapes: GenericShape[] = state.shapes
      .filter((s) => shapeIds.includes(s.id))
      .map((s) => {
        const newId = shapeId(shapeSeqRef.current++);
        return {
          ...s,
          id: newId,
          position: { x: s.position.x + DUPLICATE_OFFSET.x, y: s.position.y + DUPLICATE_OFFSET.y },
        };
      });

    setState((prev) => ({
      ...prev,
      classes: [...prev.classes, ...newClasses],
      shapes: [...prev.shapes, ...newShapes],
    }));

    selection.selectMany([
      ...newClasses.map((c) => ({ kind: 'class' as const, id: c.id })),
      ...newShapes.map((s) => ({ kind: 'shape' as const, id: s.id })),
    ]);
  }, [selection, state]);

  const deleteSelected = useCallback(() => {
    const classIds = selection.selectedIdsOfKind('class');
    const shapeIds = selection.selectedIdsOfKind('shape');
    const relationshipIds = selection.selectedIdsOfKind('relationship');
    if (classIds.length) deleteClasses(classIds);
    if (shapeIds.length) deleteShapes(shapeIds);
    if (relationshipIds.length) deleteRelationships(relationshipIds);
    selection.clearSelection();
  }, [selection, deleteClasses, deleteShapes, deleteRelationships]);

  const toDocument = useCallback((): UmlDocument => {
    return {
      classes: state.classes.map(classToWire),
      relationships: state.relationships.map((r) => ({
        id: r.id,
        source: r.source,
        destination: r.destination,
        type: r.type,
        multiplicity: r.multiplicity,
        label: r.label,
      })),
    };
  }, [state]);

  const loadDocument = useCallback(
    (doc: UmlDocument) => {
      const classes = doc.classes.map(classFromWire);
      const relationships: RelationshipState[] = doc.relationships.map((r) => ({
        id: r.id,
        source: r.source,
        destination: r.destination,
        type: r.type,
        multiplicity: r.multiplicity,
        label: r.label,
      }));

      setState({ classes, relationships, shapes: [] });
      classSeqRef.current = nextSeqFromIds(
        classes.map((c) => c.id),
        'class_',
      );
      relSeqRef.current = nextSeqFromIds(
        relationships.map((r) => r.id),
        'rel_',
      );
      shapeSeqRef.current = 1;
      selection.clearSelection();
      canvas.cancelPendingRelationship();
      canvas.resetView();
    },
    [selection, canvas],
  );

  const getContentBounds = useCallback((): Rect | null => {
    const rects: Rect[] = [
      ...state.classes.map((c) => ({
        x: c.position.x,
        y: c.position.y,
        width: c.size.width,
        height: c.size.height,
      })),
      ...state.shapes.map((s) => ({
        x: s.position.x,
        y: s.position.y,
        width: s.size.width,
        height: s.size.height,
      })),
    ];
    return boundsOfRects(rects);
  }, [state]);

  return {
    classes: state.classes,
    relationships: state.relationships,
    shapes: state.shapes,

    ...canvas,
    ...selection,

    addClass,
    updateClass,
    moveClasses,
    resizeClass,
    deleteClasses,

    addRelationship,
    updateRelationship,
    deleteRelationships,

    addShape,
    moveShapes,
    resizeShape,
    deleteShapes,

    duplicateSelected,
    deleteSelected,

    toDocument,
    loadDocument,
    getContentBounds,
  };
}
