import { createContext, useContext, type ReactNode } from 'react';

import { useDiagram, type UseDiagramResult } from '../hooks/useDiagram';

const DiagramContext = createContext<UseDiagramResult | null>(null);

export function DiagramProvider({ children }: { children: ReactNode }) {
  const diagram = useDiagram();
  return <DiagramContext.Provider value={diagram}>{children}</DiagramContext.Provider>;
}

export function useDiagramContext(): UseDiagramResult {
  const context = useContext(DiagramContext);
  if (!context) {
    throw new Error('useDiagramContext must be used within a DiagramProvider');
  }
  return context;
}
