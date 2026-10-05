import { useCallback, useEffect, useMemo, useRef, useState, type KeyboardEvent } from 'react';
import { ArrowLeft, Keyboard, Save } from 'lucide-react';
import { useParams } from 'react-router-dom';

import { ActivityToCodeTab } from '../components/editor/ActivityToCodeTab';
import { CodeToActivityTab } from '../components/editor/CodeToActivityTab';
import { CodeToUmlTab } from '../components/editor/CodeToUmlTab';
import { PipelineTabs } from '../components/editor/PipelineTabs';
import { firstTabFor, type PipelineTabId } from '../components/editor/pipelineTabConfig';
import { ShortcutsModal } from '../components/editor/ShortcutsModal';
import { UmlToCodeTab } from '../components/editor/UmlToCodeTab';
import { Button } from '../components/common/Button';
import { useToast } from '../components/common/ToastProvider';
import { useActivityDiagramContext } from '../context/ActivityDiagramContext';
import { useDiagramContext } from '../context/DiagramContext';
import { useAuthContext } from '../context/AuthContext';
import { useGuardedNavigate, useRegisterUnsavedChanges } from '../context/UnsavedChangesContext';
import { useActivityShortcuts } from '../hooks/useActivityShortcuts';
import { useKeyboardShortcuts } from '../hooks/useKeyboardShortcuts';
import { hasOverlappingNodes } from '../utils/activityLayout';
import { schemaProblems } from '../utils/activityValidation';
import { ApiError } from '../api/client';
import * as projectsApi from '../api/projectsApi';
import { EMPTY_CODE_INPUTS, type CodeInputs, type ProjectType } from '../api/projectsApi';
import styles from './EditorPage.module.css';

const AUTO_SAVE_STORAGE_KEY = 'umlframe.autoSave';
const AUTO_SAVE_DELAY_MS = 2000;

/** The last state known to be on the server, one snapshot string per saved part. */
interface SavedSnapshots {
  uml: string;
  activity: string;
  code: string;
}

function readAutoSavePreference(): boolean {
  try {
    return localStorage.getItem(AUTO_SAVE_STORAGE_KEY) === 'true';
  } catch {
    return false;
  }
}

function writeAutoSavePreference(enabled: boolean): void {
  try {
    localStorage.setItem(AUTO_SAVE_STORAGE_KEY, String(enabled));
  } catch {
    // Preference just won't persist; auto save still works for this session.
  }
}

export function EditorPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { token } = useAuthContext();
  const diagram = useDiagramContext();
  const activity = useActivityDiagramContext();
  const { showToast } = useToast();
  const guardedNavigate = useGuardedNavigate();
  const [activeTab, setActiveTab] = useState<PipelineTabId>('uml-code');
  const isActivityTab = activeTab === 'activity-code' || activeTab === 'code-activity';
  useKeyboardShortcuts(diagram, !isActivityTab);
  useActivityShortcuts(activity, isActivityTab);

  const [projectType, setProjectType] = useState<ProjectType>('uml');
  const [projectName, setProjectName] = useState('');
  const [savedName, setSavedName] = useState('');
  const [codeInputs, setCodeInputs] = useState<CodeInputs>(EMPTY_CODE_INPUTS);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [autoSave, setAutoSave] = useState(readAutoSavePreference);
  const [saved, setSaved] = useState<SavedSnapshots | null>(null);
  const [isShortcutsOpen, setIsShortcutsOpen] = useState(false);
  const loadedProjectId = useRef<string | null>(null);

  const toUmlDocument = diagram.toDocument;
  const umlSnapshot = useMemo(() => JSON.stringify(toUmlDocument()), [toUmlDocument]);
  const toActivityDocument = activity.toDocument;
  const activitySnapshot = useMemo(
    () => JSON.stringify(toActivityDocument()),
    [toActivityDocument],
  );
  const codeSnapshot = useMemo(() => JSON.stringify(codeInputs), [codeInputs]);

  const isDirty =
    saved !== null &&
    (saved.uml !== umlSnapshot || saved.activity !== activitySnapshot || saved.code !== codeSnapshot);

  useEffect(() => {
    if (!token || !projectId || loadedProjectId.current === projectId) return;
    setIsLoading(true);
    setSaved(null);
    projectsApi
      .getProject(token, projectId)
      .then((project) => {
        setProjectType(project.projectType);
        setActiveTab(firstTabFor(project.projectType));
        setProjectName(project.name);
        setSavedName(project.name);
        setCodeInputs(project.codeInputs);
        diagram.loadDocument(project.document);
        if (project.activityDocument) {
          activity.loadDocument(project.activityDocument, {
            layout: hasOverlappingNodes(project.activityDocument),
          });
        } else activity.clear();
        loadedProjectId.current = projectId;
      })
      .catch((err) => {
        showToast(err instanceof ApiError ? err.message : 'Failed to load project.', 'error');
      })
      .finally(() => setIsLoading(false));
    // diagram/activity intentionally excluded: loadDocument would otherwise re-run
    // this effect on every mutation, since both hooks return a new object each render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, projectId, showToast]);

  // Once the loaded project has rendered, whatever the canvases now serialize to is the
  // baseline: loading normalizes documents (layout, defaults), which is not a user edit.
  useEffect(() => {
    if (isLoading || saved !== null || loadedProjectId.current !== projectId) return;
    setSaved({ uml: umlSnapshot, activity: activitySnapshot, code: codeSnapshot });
  }, [isLoading, saved, projectId, umlSnapshot, activitySnapshot, codeSnapshot]);

  const persist = useCallback(
    async (silent: boolean): Promise<boolean> => {
      if (!token || !projectId) return false;
      setIsSaving(true);
      try {
        const umlDocument = toUmlDocument();
        const activityDocument = toActivityDocument();
        // The backend rejects an activity document that has no single Start or no End, which
        // an unfinished drawing often lacks; save everything else and say so instead of
        // failing the whole save. That part stays "unsaved" until it becomes valid.
        const activityProblems = schemaProblems(activityDocument);
        const hasActivity = activityDocument.nodes.length > 0;
        const saveActivity = hasActivity && activityProblems.length === 0;
        await projectsApi.updateProject(token, projectId, {
          document: umlDocument,
          codeInputs,
          ...(saveActivity ? { activity_document: activityDocument } : {}),
        });
        setSaved((prev) => ({
          uml: JSON.stringify(umlDocument),
          code: JSON.stringify(codeInputs),
          activity:
            saveActivity || !hasActivity
              ? JSON.stringify(activityDocument)
              : (prev?.activity ?? JSON.stringify(activityDocument)),
        }));
        if (hasActivity && !saveActivity) {
          if (!silent) showToast(`Saved. Activity diagram not saved: ${activityProblems[0]}`, 'error');
        } else if (!silent) {
          showToast('Project saved.', 'success');
        }
        return true;
      } catch (err) {
        showToast(err instanceof ApiError ? err.message : 'Failed to save project.', 'error');
        return false;
      } finally {
        setIsSaving(false);
      }
    },
    [token, projectId, toUmlDocument, toActivityDocument, codeInputs, showToast],
  );

  const handleSave = useCallback(() => persist(false), [persist]);

  const guard = useMemo(() => ({ isDirty, save: handleSave }), [isDirty, handleSave]);
  useRegisterUnsavedChanges(guard);

  // Debounced auto save: re-armed by every edit, so it fires once the user pauses. A failed
  // save is not retried until the next edit (no retry loop against a down server).
  const persistRef = useRef(persist);
  persistRef.current = persist;
  useEffect(() => {
    if (!autoSave || !isDirty) return;
    const timer = window.setTimeout(() => void persistRef.current(true), AUTO_SAVE_DELAY_MS);
    return () => window.clearTimeout(timer);
    // isDirty is derived from the three snapshots; depending on them re-arms the timer per edit.
  }, [autoSave, isDirty, umlSnapshot, activitySnapshot, codeSnapshot]);

  // Ctrl/Cmd+S works everywhere (even inside a text field); "?" only outside one.
  const saveRef = useRef(handleSave);
  saveRef.current = handleSave;
  useEffect(() => {
    const onKeyDown = (event: globalThis.KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
        event.preventDefault();
        void saveRef.current();
        return;
      }
      const target = event.target;
      const isTyping =
        target instanceof HTMLElement &&
        (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable);
      if (event.key === '?' && !isTyping) {
        event.preventDefault();
        setIsShortcutsOpen(true);
      }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, []);

  const handleAutoSaveToggle = (enabled: boolean) => {
    setAutoSave(enabled);
    writeAutoSavePreference(enabled);
  };

  const handleRename = useCallback(async () => {
    const name = projectName.trim();
    if (!token || !projectId) return;
    if (!name) {
      setProjectName(savedName);
      return;
    }
    if (name === savedName) {
      setProjectName(name);
      return;
    }
    try {
      const updated = await projectsApi.updateProject(token, projectId, { name });
      setSavedName(updated.name);
      setProjectName(updated.name);
      showToast('Project renamed.', 'success');
    } catch (err) {
      setProjectName(savedName);
      showToast(err instanceof ApiError ? err.message : 'Failed to rename project.', 'error');
    }
  }, [token, projectId, projectName, savedName, showToast]);

  const handleNameKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') {
      event.currentTarget.blur();
    } else if (event.key === 'Escape') {
      setProjectName(savedName);
      event.currentTarget.blur();
    }
  };

  if (isLoading) {
    return <div className={styles.loading}>Loading project…</div>;
  }

  return (
    <div className={styles.page}>
      <div className={styles.projectBar}>
        <Button
          size="sm"
          variant="ghost"
          icon={ArrowLeft}
          onClick={() => guardedNavigate('/dashboard')}
        >
          Projects
        </Button>
        <input
          className={styles.projectNameInput}
          value={projectName}
          aria-label="Project name"
          maxLength={255}
          onChange={(e) => setProjectName(e.target.value)}
          onBlur={() => void handleRename()}
          onKeyDown={handleNameKeyDown}
        />
        <span className={styles.saveStatus} role="status">
          {isSaving ? 'Saving…' : isDirty ? 'Unsaved changes' : 'All changes saved'}
        </span>
        <label className={styles.autoSaveToggle}>
          <input
            type="checkbox"
            checked={autoSave}
            onChange={(e) => handleAutoSaveToggle(e.target.checked)}
          />
          Auto save
        </label>
        <Button
          size="sm"
          variant="ghost"
          icon={Keyboard}
          onClick={() => setIsShortcutsOpen(true)}
          title="Keyboard shortcuts (?)"
          aria-label="Keyboard shortcuts"
        />
        <Button
          variant="primary"
          size="sm"
          icon={Save}
          onClick={() => void handleSave()}
          disabled={isSaving}
        >
          {isSaving ? 'Saving…' : 'Save'}
        </Button>
        {isShortcutsOpen && <ShortcutsModal onClose={() => setIsShortcutsOpen(false)} />}
      </div>
      <PipelineTabs projectType={projectType} activeTab={activeTab} onChange={setActiveTab} />
      <div className={styles.editorBody}>
        {activeTab === 'uml-code' && <UmlToCodeTab />}
        {activeTab === 'code-uml' && (
          <CodeToUmlTab
            input={codeInputs.codeToUml}
            onInputChange={(codeToUml) => setCodeInputs((prev) => ({ ...prev, codeToUml }))}
          />
        )}
        {activeTab === 'activity-code' && <ActivityToCodeTab />}
        {activeTab === 'code-activity' && (
          <CodeToActivityTab
            input={codeInputs.codeToActivity}
            onInputChange={(codeToActivity) =>
              setCodeInputs((prev) => ({ ...prev, codeToActivity }))
            }
          />
        )}
      </div>
    </div>
  );
}
