import { useEffect } from 'react';

import { arrowKeyDelta } from '../utils/arrowNudge';
import type { UseDiagramResult } from './useDiagram';

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  return tag === 'INPUT' || tag === 'TEXTAREA' || target.isContentEditable;
}

export function useKeyboardShortcuts(diagram: UseDiagramResult, enabled = true): void {
  useEffect(() => {
    if (!enabled) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (isEditableTarget(event.target)) return;

      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'z') {
        event.preventDefault();
        if (event.shiftKey) diagram.redo();
        else diagram.undo();
        return;
      }

      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'y') {
        event.preventDefault();
        diagram.redo();
        return;
      }

      if (event.key === 'Delete' || event.key === 'Backspace') {
        if (diagram.selected.length === 0) return;
        event.preventDefault();
        diagram.deleteSelected();
        return;
      }

      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'd') {
        if (diagram.selected.length === 0) return;
        event.preventDefault();
        diagram.duplicateSelected();
        return;
      }

      const nudge = arrowKeyDelta(event);
      if (nudge) {
        const classIds = new Set(
          diagram.selected.filter((r) => r.kind === 'class').map((r) => r.id),
        );
        const shapeIds = new Set(
          diagram.selected.filter((r) => r.kind === 'shape').map((r) => r.id),
        );
        if (classIds.size + shapeIds.size === 0) return;
        event.preventDefault();
        const moved = (item: { id: string; position: { x: number; y: number } }) => ({
          id: item.id,
          x: item.position.x + nudge.dx,
          y: item.position.y + nudge.dy,
        });
        diagram.moveClasses(diagram.classes.filter((c) => classIds.has(c.id)).map(moved));
        diagram.moveShapes(diagram.shapes.filter((s) => shapeIds.has(s.id)).map(moved));
        return;
      }

      if (event.key === 'Escape') {
        diagram.clearSelection();
        diagram.cancelPendingRelationship();
        diagram.setActiveTool('select');
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [diagram, enabled]);
}
