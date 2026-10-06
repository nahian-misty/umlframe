import { useEffect, useRef, useState } from 'react';

import { activityJsonToImage } from '../../api/activityApi';
import { ApiError } from '../../api/client';
import type { CodeToActivityInput } from '../../api/projectsApi';
import { activityJsonToMermaid } from '../../api/mermaidApi';
import {
  methodKey,
  reverseToControlFlows,
  REVERSE_LANGUAGES,
  type MethodControlFlow,
  type ReverseLanguage,
} from '../../api/reverseApi';
import { useActivityDiagramContext } from '../../context/ActivityDiagramContext';
import { downloadDataUrl } from '../../utils/pngExport';
import { ActivityCanvas } from '../canvas/ActivityCanvas';
import { Button } from '../common/Button';
import { useToast } from '../common/ToastProvider';
import { ActivityToolbar } from '../toolbar/ActivityToolbar';
import { MermaidRenderer } from '../toolbar/MermaidRenderer';
import form from '../toolbar/PipelineModal.module.css';
import styles from './Tabs.module.css';

interface CodeToActivityTabProps {
  input: CodeToActivityInput;
  onInputChange: (input: CodeToActivityInput) => void;
  /** Called after a successful extraction, so the host can save the code with the diagram. */
  onParsed: () => void;
}

export function CodeToActivityTab({ input, onInputChange, onParsed }: CodeToActivityTabProps) {
  const activity = useActivityDiagramContext();
  const { showToast } = useToast();
  const { source, language, className, methodName } = input;
  const [methods, setMethods] = useState<MethodControlFlow[]>([]);
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mermaidSource, setMermaidSource] = useState<string | null>(null);
  const [isMermaidOpen, setIsMermaidOpen] = useState(false);

  const selectedKey = className && methodName ? methodKey({ className, methodName }) : '';
  const canRun = source.trim() !== '' && !isBusy;

  const showMethod = (method: MethodControlFlow) => {
    if (!method.controlFlow) return;
    activity.loadDocument(method.controlFlow, { layout: true, undoable: true });
    setMermaidSource(null);
    setIsMermaidOpen(false);
  };

  const runExtract = async () => {
    setIsBusy(true);
    setError(null);
    try {
      const found = await reverseToControlFlows(source, language);
      setMethods(found);
      const first = found.find((m) => m.controlFlow) ?? found[0];
      onInputChange({ ...input, className: first.className, methodName: first.methodName });
      setError(first.error);
      showMethod(first);
      onParsed();
      showToast(
        found.length === 1
          ? 'Control flow loaded onto the canvas'
          : `Found ${found.length} methods — pick one to view its diagram`,
        'success',
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to extract control flow');
    } finally {
      setIsBusy(false);
    }
  };

  const handleSelect = (key: string) => {
    const method = methods.find((m) => methodKey(m) === key);
    if (!method) return;
    onInputChange({ ...input, className: method.className, methodName: method.methodName });
    setError(method.error);
    showMethod(method);
  };

  // A reopened project has its code and last diagram but not the method list; rebuild the
  // list quietly (the canvas already shows the saved diagram, so nothing is reloaded).
  const restoreAttempted = useRef(false);
  useEffect(() => {
    if (restoreAttempted.current || methods.length > 0 || !source.trim()) return;
    restoreAttempted.current = true;
    reverseToControlFlows(source, language)
      .then(setMethods)
      .catch(() => undefined);
  }, [methods.length, source, language]);

  const toggleMermaid = async () => {
    if (isMermaidOpen) {
      setIsMermaidOpen(false);
      return;
    }
    setError(null);
    try {
      setMermaidSource(await activityJsonToMermaid(activity.toDocument()));
      setIsMermaidOpen(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to render the Mermaid preview');
    }
  };

  const downloadReimportablePng = async () => {
    setError(null);
    try {
      downloadDataUrl(
        await activityJsonToImage(activity.toDocument()),
        'activity-diagram-reimportable.png',
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to render a re-importable image');
    }
  };

  const hasDiagram = activity.nodes.length > 0;

  return (
    <div className={styles.workspace}>
      <div className={styles.sourcePanel}>
        <h2 className={styles.panelTitle}>Code → Activity Diagram</h2>
        <div className={form.row}>
          <div className={form.field}>
            <span className={form.label}>Language</span>
            <select
              className={form.select}
              value={language}
              onChange={(e) => {
                setMethods([]);
                onInputChange({ ...input, language: e.target.value as ReverseLanguage });
              }}
            >
              {REVERSE_LANGUAGES.map((lang) => (
                <option key={lang} value={lang}>
                  {lang}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className={form.field}>
          <span className={form.label}>Source code</span>
          <textarea
            className={`${form.textarea} ${styles.sourceTextarea}`}
            value={source}
            spellCheck={false}
            onChange={(e) => {
              setMethods([]);
              onInputChange({ ...input, source: e.target.value });
            }}
          />
        </div>
        {error && <div className={form.error}>{error}</div>}
        <Button variant="primary" onClick={() => void runExtract()} disabled={!canRun}>
          {isBusy ? 'Extracting…' : 'Extract Control Flow'}
        </Button>
        {methods.length > 0 && (
          <div className={form.field}>
            <span className={form.label}>Method ({methods.length} found)</span>
            <select
              className={form.select}
              value={selectedKey}
              onChange={(e) => handleSelect(e.target.value)}
            >
              {methods.map((m) => (
                <option key={methodKey(m)} value={methodKey(m)} disabled={!m.controlFlow}>
                  {methodKey(m)}
                  {m.error ? ' (unsupported)' : ''}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      <div className={styles.canvasArea}>
        <ActivityCanvas />
        {isMermaidOpen && mermaidSource && (
          <div className={styles.drawer}>
            <div className={styles.drawerHeader}>
              <span>Mermaid preview (read-only)</span>
              <Button size="sm" variant="ghost" onClick={() => setIsMermaidOpen(false)}>
                Close
              </Button>
            </div>
            <div className={styles.drawerBody}>
              <MermaidRenderer source={mermaidSource} filename="activity-diagram.png" />
            </div>
          </div>
        )}
      </div>

      <ActivityToolbar>
        <h3 className={styles.sectionTitle}>Preview &amp; export</h3>
        <Button size="sm" disabled={!hasDiagram} onClick={() => void toggleMermaid()}>
          {isMermaidOpen ? 'Hide Mermaid preview' : 'Mermaid preview'}
        </Button>
        <Button size="sm" disabled={!hasDiagram} onClick={() => void downloadReimportablePng()}>
          Download re-importable PNG
        </Button>
      </ActivityToolbar>
    </div>
  );
}
