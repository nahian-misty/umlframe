import { useState, type ChangeEvent } from 'react';

import { activityImageToJson, generateActivityCode } from '../../api/activityApi';
import { ApiError } from '../../api/client';
import { useActivityDiagramContext } from '../../context/ActivityDiagramContext';
import { codegenProblems } from '../../utils/activityValidation';
import { ActivityCanvas } from '../canvas/ActivityCanvas';
import { Button } from '../common/Button';
import { useToast } from '../common/ToastProvider';
import { ActivityToolbar } from '../toolbar/ActivityToolbar';
import { CodeViewer } from '../toolbar/CodeViewer';
import form from '../toolbar/PipelineModal.module.css';
import styles from './Tabs.module.css';

const LANGUAGES = ['python', 'java', 'javascript'] as const;

export function ActivityToCodeTab() {
  const activity = useActivityDiagramContext();
  const { showToast } = useToast();
  const [language, setLanguage] = useState<string>('python');
  const [functionName, setFunctionName] = useState('');
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [files, setFiles] = useState<Record<string, string> | null>(null);

  const problems = activity.nodes.length > 0 ? codegenProblems(activity.toDocument()) : [];

  const handleImage = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    setIsBusy(true);
    setError(null);
    try {
      activity.loadDocument(await activityImageToJson(file), { layout: true, undoable: true });
      showToast('Activity diagram loaded from image', 'success');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to read the image');
    } finally {
      setIsBusy(false);
    }
  };

  const handleGenerate = async () => {
    setIsBusy(true);
    setError(null);
    try {
      setFiles(await generateActivityCode(activity.toDocument(), language, functionName));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to generate activity code');
    } finally {
      setIsBusy(false);
    }
  };

  return (
    <div className={styles.workspace}>
      <div className={styles.canvasArea}>
        <ActivityCanvas />
      </div>
      <ActivityToolbar>
        <h3 className={styles.sectionTitle}>Generate code</h3>
        <div className={form.field}>
          <span className={form.label}>Load from image (PNG or JPEG)</span>
          <input
            type="file"
            accept="image/png,image/jpeg"
            disabled={isBusy}
            onChange={(e) => void handleImage(e)}
          />
        </div>
        <div className={form.field}>
          <span className={form.label}>Target language</span>
          <select
            className={form.select}
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
          >
            {LANGUAGES.map((lang) => (
              <option key={lang} value={lang}>
                {lang}
              </option>
            ))}
          </select>
        </div>
        <div className={form.field}>
          <span className={form.label}>Function name (optional)</span>
          <input
            className={form.input}
            value={functionName}
            placeholder="generated_function"
            onChange={(e) => setFunctionName(e.target.value)}
          />
        </div>
        {problems.length > 0 && (
          <ul className={styles.problems}>
            {problems.map((problem) => (
              <li key={problem}>{problem}</li>
            ))}
          </ul>
        )}
        {error && <div className={form.error}>{error}</div>}
        <Button
          variant="primary"
          onClick={() => void handleGenerate()}
          disabled={activity.nodes.length === 0 || problems.length > 0 || isBusy}
        >
          {isBusy ? 'Working…' : 'Generate Function'}
        </Button>
      </ActivityToolbar>
      {files && <CodeViewer files={files} onClose={() => setFiles(null)} />}
    </div>
  );
}
