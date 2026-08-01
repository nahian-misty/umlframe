import { useCallback, useRef, useState, type RefObject } from 'react';

import { MAX_ZOOM, MIN_ZOOM, ZOOM_STEP } from '../utils/constants';
import { clamp } from '../utils/geometry';
import type { ToolId } from '../types/diagram';
import type { RelationshipType } from '../types/uml';

export interface UseCanvasResult {
  pan: { x: number; y: number };
  zoom: number;
  snapEnabled: boolean;
  activeTool: ToolId;
  activeRelationshipType: RelationshipType | null;
  pendingRelationshipSource: string | null;
  contentRef: RefObject<HTMLDivElement | null>;
  setPan: (pan: { x: number; y: number }) => void;
  panBy: (dx: number, dy: number) => void;
  setZoom: (zoom: number) => void;
  zoomIn: () => void;
  zoomOut: () => void;
  resetView: () => void;
  toggleSnap: () => void;
  setActiveTool: (tool: ToolId) => void;
  setActiveRelationshipType: (type: RelationshipType | null) => void;
  armRelationshipSource: (classId: string) => void;
  cancelPendingRelationship: () => void;
}

export function useCanvas(): UseCanvasResult {
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [zoom, setZoomState] = useState(1);
  const [snapEnabled, setSnapEnabled] = useState(true);
  const [activeTool, setActiveTool] = useState<ToolId>('select');
  const [activeRelationshipType, setActiveRelationshipType] = useState<RelationshipType | null>(
    null,
  );
  const [pendingRelationshipSource, setPendingRelationshipSource] = useState<string | null>(null);
  const contentRef = useRef<HTMLDivElement | null>(null);

  const setZoom = useCallback((next: number) => {
    setZoomState(clamp(next, MIN_ZOOM, MAX_ZOOM));
  }, []);

  const zoomIn = useCallback(() => setZoom(zoom + ZOOM_STEP), [zoom, setZoom]);
  const zoomOut = useCallback(() => setZoom(zoom - ZOOM_STEP), [zoom, setZoom]);

  const panBy = useCallback((dx: number, dy: number) => {
    setPan((prev) => ({ x: prev.x + dx, y: prev.y + dy }));
  }, []);

  const resetView = useCallback(() => {
    setPan({ x: 0, y: 0 });
    setZoomState(1);
  }, []);

  const toggleSnap = useCallback(() => setSnapEnabled((prev) => !prev), []);

  const armRelationshipSource = useCallback((classId: string) => {
    setPendingRelationshipSource(classId);
  }, []);

  const cancelPendingRelationship = useCallback(() => {
    setPendingRelationshipSource(null);
  }, []);

  return {
    pan,
    zoom,
    snapEnabled,
    activeTool,
    activeRelationshipType,
    pendingRelationshipSource,
    contentRef,
    setPan,
    panBy,
    setZoom,
    zoomIn,
    zoomOut,
    resetView,
    toggleSnap,
    setActiveTool,
    setActiveRelationshipType,
    armRelationshipSource,
    cancelPendingRelationship,
  };
}
