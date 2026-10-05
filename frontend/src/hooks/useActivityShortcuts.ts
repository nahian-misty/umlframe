import { useEffect } from 'react';

import type { UseActivityDiagramResult } from './useActivityDiagram';

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  return tag === 'INPUT' || tag === 'TEXTAREA' || target.isContentEditable;
}

export function useActivityShortcuts(activity: UseActivityDiagramResult, enabled: boolean): void {
  useEffect(() => {
    if (!enabled) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (isEditableTarget(event.target)) return;
      const hasSelection = activity.selectedNodeIds.length + activity.selectedEdgeIds.length > 0;

      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'z') {
        event.preventDefault();
        if (event.shiftKey) activity.redo();
        else activity.undo();
      } else if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'y') {
        event.preventDefault();
        activity.redo();
      } else if ((event.key === 'Delete' || event.key === 'Backspace') && hasSelection) {
        event.preventDefault();
        activity.deleteSelected();
      } else if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'd') {
        if (!hasSelection) return;
        event.preventDefault();
        activity.duplicateSelected();
      } else if (event.key === 'Escape') {
        activity.clearSelection();
        activity.armConnectSource(null);
        activity.setActiveTool('select');
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [activity, enabled]);
}
