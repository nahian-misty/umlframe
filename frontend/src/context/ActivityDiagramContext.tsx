import { createContext, useContext, type ReactNode } from 'react';

import { useActivityDiagram, type UseActivityDiagramResult } from '../hooks/useActivityDiagram';

const ActivityDiagramContext = createContext<UseActivityDiagramResult | null>(null);

export function ActivityDiagramProvider({ children }: { children: ReactNode }) {
  const activity = useActivityDiagram();
  return (
    <ActivityDiagramContext.Provider value={activity}>{children}</ActivityDiagramContext.Provider>
  );
}

export function useActivityDiagramContext(): UseActivityDiagramResult {
  const context = useContext(ActivityDiagramContext);
  if (!context) {
    throw new Error('useActivityDiagramContext must be used within an ActivityDiagramProvider');
  }
  return context;
}
