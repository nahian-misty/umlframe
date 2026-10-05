import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { useNavigate, type To } from 'react-router-dom';

import { Button } from '../components/common/Button';
import { Modal } from '../components/common/Modal';

export interface UnsavedChangesGuard {
  isDirty: boolean;
  /** Resolves true when the changes were persisted, false when saving failed. */
  save: () => Promise<boolean>;
}

interface UnsavedChangesContextValue {
  registerGuard: (guard: UnsavedChangesGuard | null) => void;
  /** Runs `proceed` now, or after the user resolves the unsaved-changes prompt. */
  requestLeave: (proceed: () => void) => void;
}

const UnsavedChangesContext = createContext<UnsavedChangesContextValue | null>(null);

export function UnsavedChangesProvider({ children }: { children: ReactNode }) {
  const guardRef = useRef<UnsavedChangesGuard | null>(null);
  const [pendingProceed, setPendingProceed] = useState<(() => void) | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const registerGuard = useCallback((guard: UnsavedChangesGuard | null) => {
    guardRef.current = guard;
  }, []);

  const requestLeave = useCallback((proceed: () => void) => {
    if (guardRef.current?.isDirty) {
      setPendingProceed(() => proceed);
    } else {
      proceed();
    }
  }, []);

  const closePrompt = () => setPendingProceed(null);

  const leaveWithoutSaving = () => {
    const proceed = pendingProceed;
    closePrompt();
    proceed?.();
  };

  const saveAndLeave = async () => {
    const guard = guardRef.current;
    if (!guard) return leaveWithoutSaving();
    setIsSaving(true);
    const saved = await guard.save();
    setIsSaving(false);
    if (saved) leaveWithoutSaving();
  };

  const value = useMemo(() => ({ registerGuard, requestLeave }), [registerGuard, requestLeave]);

  return (
    <UnsavedChangesContext.Provider value={value}>
      {children}
      {pendingProceed && (
        <Modal
          title="Unsaved changes"
          onClose={closePrompt}
          footer={
            <>
              <Button variant="ghost" onClick={closePrompt} disabled={isSaving}>
                Stay
              </Button>
              <Button variant="danger" onClick={leaveWithoutSaving} disabled={isSaving}>
                Leave without saving
              </Button>
              <Button variant="primary" onClick={() => void saveAndLeave()} disabled={isSaving}>
                {isSaving ? 'Saving…' : 'Save & leave'}
              </Button>
            </>
          }
        >
          <p>This project has changes that haven&apos;t been saved. Save them before leaving?</p>
        </Modal>
      )}
    </UnsavedChangesContext.Provider>
  );
}

function useUnsavedChangesContext(): UnsavedChangesContextValue {
  const context = useContext(UnsavedChangesContext);
  if (!context) {
    throw new Error('Unsaved-changes hooks must be used within an UnsavedChangesProvider');
  }
  return context;
}

/** Registers the current page's dirty state; also warns on tab close / reload while dirty. */
export function useRegisterUnsavedChanges(guard: UnsavedChangesGuard): void {
  const { registerGuard } = useUnsavedChangesContext();

  useEffect(() => {
    registerGuard(guard);
  }, [registerGuard, guard]);

  useEffect(() => () => registerGuard(null), [registerGuard]);

  useEffect(() => {
    if (!guard.isDirty) return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
    };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [guard.isDirty]);
}

/** `navigate`, but asks first when the open project has unsaved changes. */
export function useGuardedNavigate(): (to: To) => void {
  const navigate = useNavigate();
  const { requestLeave } = useUnsavedChangesContext();
  return useCallback((to: To) => requestLeave(() => navigate(to)), [requestLeave, navigate]);
}

/** Runs an arbitrary leave action (e.g. logout) behind the unsaved-changes prompt. */
export function useGuardedAction(): (action: () => void) => void {
  return useUnsavedChangesContext().requestLeave;
}
