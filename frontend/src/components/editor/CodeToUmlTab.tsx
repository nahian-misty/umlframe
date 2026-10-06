import { useState } from 'react';

import { ApiError } from '../../api/client';
import type { CodeToUmlInput } from '../../api/projectsApi';
import { reverseToJson, REVERSE_LANGUAGES, type ReverseLanguage } from '../../api/reverseApi';
import { useDiagramContext } from '../../context/DiagramContext';
import { Canvas } from '../canvas/Canvas';
import { Button } from '../common/Button';
import { useToast } from '../common/ToastProvider';
import { Toolbar } from '../toolbar/Toolbar';
import form from '../toolbar/PipelineModal.module.css';
import styles from './Tabs.module.css';

interface CodeToUmlTabProps {
  input: CodeToUmlInput;
  onInputChange: (input: CodeToUmlInput) => void;
  /** Called after a successful parse, so the host can save the code together with the diagram. */
  onParsed: () => void;
}

export function CodeToUmlTab({ input, onInputChange, onParsed }: CodeToUmlTabProps) {
  const diagram = useDiagramContext();
  const { showToast } = useToast();
  const { source, language } = input;
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmed, setConfirmed] = useState(false);

  const hasExistingContent =
    diagram.classes.length > 0 || diagram.relationships.length > 0 || diagram.shapes.length > 0;
  const needsConfirmation = hasExistingContent && !confirmed;

  const runReverse = async () => {
    setIsBusy(true);
    setError(null);
    try {
      diagram.loadDocument(await reverseToJson(source, language), { undoable: true });
      setConfirmed(false);
      onParsed();
      showToast('Diagram reconstructed from source', 'success');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to parse source');
    } finally {
      setIsBusy(false);
    }
  };

  const handleGenerate = () => {
    if (needsConfirmation) {
      setConfirmed(true);
      return;
    }
    void runReverse();
  };

  return (
    <div className={styles.workspace}>
      <div className={styles.sourcePanel}>
        <h2 className={styles.panelTitle}>Code → UML Class Diagram</h2>
        <div className={form.field}>
          <span className={form.label}>Source language</span>
          <select
            className={form.select}
            value={language}
            onChange={(e) => onInputChange({ ...input, language: e.target.value as ReverseLanguage })}
          >
            {REVERSE_LANGUAGES.map((lang) => (
              <option key={lang} value={lang}>
                {lang}
              </option>
            ))}
          </select>
        </div>
        <div className={form.field}>
          <span className={form.label}>Source code</span>
          <textarea
            className={`${form.textarea} ${styles.sourceTextarea}`}
            value={source}
            spellCheck={false}
            placeholder={
              'class User:\n    def __init__(self, email: str) -> None:\n        self.email = email'
            }
            onChange={(e) => {
              onInputChange({ ...input, source: e.target.value });
              setConfirmed(false);
            }}
          />
        </div>
        {needsConfirmation && (
          <div className={form.warning}>
            This will replace the current diagram. Click “Replace &amp; Load” again to confirm.
          </div>
        )}
        {error && <div className={form.error}>{error}</div>}
        <Button variant="primary" onClick={handleGenerate} disabled={!source.trim() || isBusy}>
          {isBusy ? 'Parsing…' : needsConfirmation ? 'Replace & Load' : 'Parse & Load'}
        </Button>
      </div>
      <div className={styles.canvasArea}>
        <Canvas />
      </div>
      <Toolbar />
    </div>
  );
}
