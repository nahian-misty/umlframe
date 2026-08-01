import { useCallback, useEffect, useRef, useState } from 'react';
import { Save } from 'lucide-react';
import { useParams } from 'react-router-dom';

import { Canvas } from '../components/canvas/Canvas';
import { Toolbar } from '../components/toolbar/Toolbar';
import { Button } from '../components/common/Button';
import { useToast } from '../components/common/ToastProvider';
import { useDiagramContext } from '../context/DiagramContext';
import { useAuthContext } from '../context/AuthContext';
import { useKeyboardShortcuts } from '../hooks/useKeyboardShortcuts';
import { ApiError } from '../api/client';
import * as projectsApi from '../api/projectsApi';
import styles from './EditorPage.module.css';

export function EditorPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { token } = useAuthContext();
  const diagram = useDiagramContext();
  const { showToast } = useToast();
  useKeyboardShortcuts(diagram);

  const [projectName, setProjectName] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const loadedProjectId = useRef<string | null>(null);

  useEffect(() => {
    if (!token || !projectId || loadedProjectId.current === projectId) return;
    setIsLoading(true);
    projectsApi
      .getProject(token, projectId)
      .then((project) => {
        setProjectName(project.name);
        diagram.loadDocument(project.document);
        loadedProjectId.current = projectId;
      })
      .catch((err) => {
        showToast(err instanceof ApiError ? err.message : 'Failed to load project.', 'error');
      })
      .finally(() => setIsLoading(false));
    // diagram intentionally excluded: loadDocument would otherwise re-run this
    // effect on every diagram mutation, since useDiagram returns a new object
    // each render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, projectId, showToast]);

  const handleSave = useCallback(async () => {
    if (!token || !projectId) return;
    setIsSaving(true);
    try {
      await projectsApi.updateProject(token, projectId, { document: diagram.toDocument() });
      showToast('Project saved.', 'success');
    } catch (err) {
      showToast(err instanceof ApiError ? err.message : 'Failed to save project.', 'error');
    } finally {
      setIsSaving(false);
    }
  }, [token, projectId, diagram, showToast]);

  const handleRename = useCallback(
    async (name: string) => {
      if (!token || !projectId || !name.trim() || name === projectName) return;
      try {
        await projectsApi.updateProject(token, projectId, { name: name.trim() });
      } catch (err) {
        showToast(err instanceof ApiError ? err.message : 'Failed to rename project.', 'error');
      }
    },
    [token, projectId, projectName, showToast],
  );

  if (isLoading) {
    return <div className={styles.loading}>Loading project…</div>;
  }

  return (
    <div className={styles.page}>
      <div className={styles.projectBar}>
        <input
          className={styles.projectNameInput}
          value={projectName}
          onChange={(e) => setProjectName(e.target.value)}
          onBlur={(e) => handleRename(e.target.value)}
        />
        <Button variant="primary" size="sm" icon={Save} onClick={handleSave} disabled={isSaving}>
          {isSaving ? 'Saving…' : 'Save'}
        </Button>
      </div>
      <div className={styles.editorBody}>
        <div className={styles.canvasArea}>
          <Canvas />
        </div>
        <Toolbar />
      </div>
    </div>
  );
}
