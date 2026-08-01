import { useCallback, useMemo, useState } from 'react';

import type { SelectableRef } from '../types/diagram';

const refKey = (ref: SelectableRef): string => `${ref.kind}:${ref.id}`;

export interface UseSelectionResult {
  selected: SelectableRef[];
  hoveredId: string | null;
  isSelected: (ref: SelectableRef) => boolean;
  select: (ref: SelectableRef) => void;
  toggleSelect: (ref: SelectableRef) => void;
  selectMany: (refs: SelectableRef[]) => void;
  clearSelection: () => void;
  setHoveredId: (id: string | null) => void;
  selectedIdsOfKind: (kind: SelectableRef['kind']) => string[];
}

export function useSelection(): UseSelectionResult {
  const [selected, setSelected] = useState<SelectableRef[]>([]);
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  const selectedKeys = useMemo(() => new Set(selected.map(refKey)), [selected]);

  const isSelected = useCallback(
    (ref: SelectableRef) => selectedKeys.has(refKey(ref)),
    [selectedKeys],
  );

  const select = useCallback((ref: SelectableRef) => setSelected([ref]), []);

  const toggleSelect = useCallback((ref: SelectableRef) => {
    setSelected((prev) => {
      const key = refKey(ref);
      const exists = prev.some((r) => refKey(r) === key);
      return exists ? prev.filter((r) => refKey(r) !== key) : [...prev, ref];
    });
  }, []);

  const selectMany = useCallback((refs: SelectableRef[]) => setSelected(refs), []);

  const clearSelection = useCallback(() => setSelected([]), []);

  const selectedIdsOfKind = useCallback(
    (kind: SelectableRef['kind']) => selected.filter((r) => r.kind === kind).map((r) => r.id),
    [selected],
  );

  return {
    selected,
    hoveredId,
    isSelected,
    select,
    toggleSelect,
    selectMany,
    clearSelection,
    setHoveredId,
    selectedIdsOfKind,
  };
}
