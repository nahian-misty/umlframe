import { useCallback, useState } from 'react';

const HISTORY_LIMIT = 50;
/** Repeated edits with the same key closer together than this form one undo step. */
const COALESCE_WINDOW_MS = 600;

interface History<T> {
  past: T[];
  present: T;
  future: T[];
  lastKey: string | null;
  lastAt: number;
}

export interface UndoableState<T> {
  state: T;
  /**
   * Apply `updater` as one undoable edit. A `coalesceKey` merges a burst of edits of the same
   * kind (a drag, typing in one field) into a single history entry.
   */
  update: (updater: (prev: T) => T, coalesceKey?: string) => void;
  /** Replace the state and forget all history (loading a different document). */
  reset: (next: T) => void;
  undo: () => void;
  redo: () => void;
  canUndo: boolean;
  canRedo: boolean;
}

export function useUndoableState<T>(initial: T): UndoableState<T> {
  const [history, setHistory] = useState<History<T>>({
    past: [],
    present: initial,
    future: [],
    lastKey: null,
    lastAt: 0,
  });

  const update = useCallback((updater: (prev: T) => T, coalesceKey?: string) => {
    setHistory((h) => {
      const next = updater(h.present);
      if (next === h.present) return h;
      const now = Date.now();
      const coalesce =
        coalesceKey !== undefined &&
        h.lastKey === coalesceKey &&
        now - h.lastAt < COALESCE_WINDOW_MS;
      return {
        past: coalesce ? h.past : [...h.past, h.present].slice(-HISTORY_LIMIT),
        present: next,
        future: [],
        lastKey: coalesceKey ?? null,
        lastAt: now,
      };
    });
  }, []);

  const reset = useCallback((next: T) => {
    setHistory({ past: [], present: next, future: [], lastKey: null, lastAt: 0 });
  }, []);

  const undo = useCallback(() => {
    setHistory((h) =>
      h.past.length === 0
        ? h
        : {
            past: h.past.slice(0, -1),
            present: h.past[h.past.length - 1],
            future: [h.present, ...h.future],
            lastKey: null,
            lastAt: 0,
          },
    );
  }, []);

  const redo = useCallback(() => {
    setHistory((h) =>
      h.future.length === 0
        ? h
        : {
            past: [...h.past, h.present],
            present: h.future[0],
            future: h.future.slice(1),
            lastKey: null,
            lastAt: 0,
          },
    );
  }, []);

  return {
    state: history.present,
    update,
    reset,
    undo,
    redo,
    canUndo: history.past.length > 0,
    canRedo: history.future.length > 0,
  };
}
