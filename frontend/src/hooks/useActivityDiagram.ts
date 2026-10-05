import { useCallback, useRef, useState } from 'react';

import { useCanvas, type UseCanvasResult } from './useCanvas';
import { useUndoableState } from './useUndoableState';
import { autoLayout } from '../utils/activityLayout';
import { ACTIVITY_NODE_SIZES, DUPLICATE_OFFSET, MIN_ACTIVITY_NODE_SIZE } from '../utils/constants';
import { boundsOfRects, type Point, type Rect } from '../utils/geometry';
import type {
  ActivityDocument,
  ActivityEdge,
  ActivityNode,
  ActivityNodeType,
} from '../types/activity';

export type ActivityToolId = 'select' | 'pan' | 'connect' | ActivityNodeType;

const DEFAULT_LABELS: Record<ActivityNodeType, string> = {
  start: '',
  end: '',
  action: 'Action',
  decision: 'Condition?',
  fork: '',
  join: '',
};

const EMPTY_DOCUMENT: ActivityDocument = { nodes: [], edges: [] };

function nextId(prefix: string, taken: Set<string>, counter: { current: number }): string {
  let id = `${prefix}${counter.current++}`;
  while (taken.has(id)) id = `${prefix}${counter.current++}`;
  return id;
}

export interface UseActivityDiagramResult extends Omit<
  UseCanvasResult,
  'activeTool' | 'setActiveTool'
> {
  nodes: ActivityNode[];
  edges: ActivityEdge[];
  activeTool: ActivityToolId;
  setActiveTool: (tool: ActivityToolId) => void;
  selectedNodeIds: string[];
  selectedEdgeIds: string[];
  pendingConnectSource: string | null;

  addNode: (type: ActivityNodeType, position: Point) => string;
  moveNodes: (updates: { id: string; x: number; y: number }[]) => void;
  resizeNode: (id: string, size: { width: number; height: number }, position: Point) => void;
  updateNodeLabel: (id: string, label: string) => void;
  addEdge: (source: string, target: string) => string | null;
  updateEdgeLabel: (id: string, label: string) => void;

  selectNodes: (ids: string[], additive?: boolean) => void;
  selectEdge: (id: string) => void;
  clearSelection: () => void;
  armConnectSource: (id: string | null) => void;
  deleteSelected: () => void;
  duplicateSelected: () => void;

  toDocument: () => ActivityDocument;
  loadDocument: (doc: ActivityDocument, options?: { layout?: boolean; undoable?: boolean }) => void;
  clear: (options?: { undoable?: boolean }) => void;
  undo: () => void;
  redo: () => void;
  canUndo: boolean;
  canRedo: boolean;
  getContentBounds: () => Rect | null;
}

export function useActivityDiagram(): UseActivityDiagramResult {
  const history = useUndoableState<ActivityDocument>(EMPTY_DOCUMENT);
  const { state: doc, update: setDoc, reset: resetHistory } = history;
  const { undo: undoHistory, redo: redoHistory } = history;
  const [activeTool, setActiveTool] = useState<ActivityToolId>('select');
  const [selectedNodeIds, setSelectedNodeIds] = useState<string[]>([]);
  const [selectedEdgeIds, setSelectedEdgeIds] = useState<string[]>([]);
  const [pendingConnectSource, setPendingConnectSource] = useState<string | null>(null);
  const nodeSeq = useRef({ current: 1 });
  const edgeSeq = useRef({ current: 1 });

  const canvas = useCanvas();
  const { resetView } = canvas;

  const clearSelection = useCallback(() => {
    setSelectedNodeIds([]);
    setSelectedEdgeIds([]);
  }, []);

  const addNode = useCallback(
    (type: ActivityNodeType, position: Point): string => {
      const id = nextId('node_', new Set(doc.nodes.map((n) => n.id)), nodeSeq.current);
      const node: ActivityNode = {
        id,
        type,
        label: DEFAULT_LABELS[type],
        position,
        size: { ...ACTIVITY_NODE_SIZES[type] },
      };
      setDoc((prev) => ({ ...prev, nodes: [...prev.nodes, node] }));
      setSelectedNodeIds([id]);
      setSelectedEdgeIds([]);
      return id;
    },
    [doc.nodes, setDoc],
  );

  const moveNodes = useCallback((updates: { id: string; x: number; y: number }[]) => {
    setDoc(
      (prev) => ({
        ...prev,
        nodes: prev.nodes.map((node) => {
          const update = updates.find((u) => u.id === node.id);
          return update ? { ...node, position: { x: update.x, y: update.y } } : node;
        }),
      }),
      'move-nodes',
    );
  }, [setDoc]);

  const resizeNode = useCallback(
    (id: string, size: { width: number; height: number }, position: Point) => {
      setDoc(
        (prev) => ({
          ...prev,
          nodes: prev.nodes.map((node) =>
            node.id === id
              ? {
                  ...node,
                  position,
                  size: {
                    width: Math.max(MIN_ACTIVITY_NODE_SIZE.width, size.width),
                    height: Math.max(MIN_ACTIVITY_NODE_SIZE.height, size.height),
                  },
                }
              : node,
          ),
        }),
        `resize-node:${id}`,
      );
    },
    [setDoc],
  );

  const updateNodeLabel = useCallback((id: string, label: string) => {
    setDoc(
      (prev) => ({
        ...prev,
        nodes: prev.nodes.map((node) => (node.id === id ? { ...node, label } : node)),
      }),
      `node-label:${id}`,
    );
  }, [setDoc]);

  const addEdge = useCallback(
    (source: string, target: string): string | null => {
      if (source === target) return null;
      if (doc.edges.some((e) => e.source === source && e.target === target)) return null;
      const id = nextId('edge_', new Set(doc.edges.map((e) => e.id)), edgeSeq.current);
      setDoc((prev) => ({ ...prev, edges: [...prev.edges, { id, source, target, label: '' }] }));
      return id;
    },
    [doc.edges, setDoc],
  );

  const updateEdgeLabel = useCallback((id: string, label: string) => {
    setDoc(
      (prev) => ({
        ...prev,
        edges: prev.edges.map((edge) => (edge.id === id ? { ...edge, label } : edge)),
      }),
      `edge-label:${id}`,
    );
  }, [setDoc]);

  const selectNodes = useCallback((ids: string[], additive = false) => {
    setSelectedEdgeIds([]);
    setSelectedNodeIds((prev) => (additive ? [...new Set([...prev, ...ids])] : ids));
  }, []);

  const selectEdge = useCallback((id: string) => {
    setSelectedNodeIds([]);
    setSelectedEdgeIds([id]);
  }, []);

  const deleteSelected = useCallback(() => {
    const nodeIds = new Set(selectedNodeIds);
    const edgeIds = new Set(selectedEdgeIds);
    setDoc((prev) => ({
      nodes: prev.nodes.filter((n) => !nodeIds.has(n.id)),
      edges: prev.edges.filter(
        (e) => !edgeIds.has(e.id) && !nodeIds.has(e.source) && !nodeIds.has(e.target),
      ),
    }));
    clearSelection();
    setPendingConnectSource(null);
  }, [selectedNodeIds, selectedEdgeIds, clearSelection, setDoc]);

  const duplicateSelected = useCallback(() => {
    const taken = new Set(doc.nodes.map((n) => n.id));
    const copies: ActivityNode[] = doc.nodes
      // A document may have only one Start node, so Start is never duplicated.
      .filter((n) => selectedNodeIds.includes(n.id) && n.type !== 'start')
      .map((n) => {
        const id = nextId('node_', taken, nodeSeq.current);
        taken.add(id);
        return {
          ...n,
          id,
          position: { x: n.position.x + DUPLICATE_OFFSET.x, y: n.position.y + DUPLICATE_OFFSET.y },
        };
      });
    if (copies.length === 0) return;
    setDoc((prev) => ({ ...prev, nodes: [...prev.nodes, ...copies] }));
    setSelectedNodeIds(copies.map((c) => c.id));
    setSelectedEdgeIds([]);
  }, [doc.nodes, selectedNodeIds, setDoc]);

  const toDocument = useCallback((): ActivityDocument => doc, [doc]);

  const loadDocument = useCallback(
    (next: ActivityDocument, options?: { layout?: boolean; undoable?: boolean }) => {
      const loaded = options?.layout ? autoLayout(next) : next;
      if (options?.undoable) setDoc(() => loaded);
      else resetHistory(loaded);
      nodeSeq.current.current = 1;
      edgeSeq.current.current = 1;
      clearSelection();
      setPendingConnectSource(null);
      setActiveTool('select');
      resetView();
    },
    [clearSelection, resetView, setDoc, resetHistory],
  );

  const clear = useCallback(
    (options?: { undoable?: boolean }) => loadDocument(EMPTY_DOCUMENT, options),
    [loadDocument],
  );

  const undo = useCallback(() => {
    undoHistory();
    clearSelection();
    setPendingConnectSource(null);
  }, [undoHistory, clearSelection]);

  const redo = useCallback(() => {
    redoHistory();
    clearSelection();
    setPendingConnectSource(null);
  }, [redoHistory, clearSelection]);

  const getContentBounds = useCallback(
    (): Rect | null =>
      boundsOfRects(
        doc.nodes.map((n) => ({
          x: n.position.x,
          y: n.position.y,
          width: n.size.width,
          height: n.size.height,
        })),
      ),
    [doc.nodes],
  );

  return {
    ...canvas,
    nodes: doc.nodes,
    edges: doc.edges,
    activeTool,
    setActiveTool,
    selectedNodeIds,
    selectedEdgeIds,
    pendingConnectSource,
    addNode,
    moveNodes,
    resizeNode,
    updateNodeLabel,
    addEdge,
    updateEdgeLabel,
    selectNodes,
    selectEdge,
    clearSelection,
    armConnectSource: setPendingConnectSource,
    deleteSelected,
    duplicateSelected,
    toDocument,
    loadDocument,
    clear,
    undo,
    redo,
    canUndo: history.canUndo,
    canRedo: history.canRedo,
    getContentBounds,
  };
}
