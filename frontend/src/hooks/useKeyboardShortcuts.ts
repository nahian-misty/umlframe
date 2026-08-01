import { useEffect } from 'react';

import type { UseDiagramResult } from './useDiagram';

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  return tag === 'INPUT' || tag === 'TEXTAREA' || target.isContentEditable;
}

export function useKeyboardShortcuts(diagram: UseDiagramResult): void {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (isEditableTarget(event.target)) return;

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

      if (event.key === 'Escape') {
        diagram.clearSelection();
        diagram.cancelPendingRelationship();
        diagram.setActiveTool('select');
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [diagram]);
}
