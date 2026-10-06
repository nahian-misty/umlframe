import { useEffect, useRef, useState } from 'react';
import { Code2 } from 'lucide-react';

import { useAuthContext } from '../../context/AuthContext';
import { useDiagramContext } from '../../context/DiagramContext';
import {
  readStoredChoice,
  readStoredText,
  writeStoredChoice,
  writeStoredText,
} from '../../utils/storedPreference';
import { fetchLanguages, generateCode } from '../../api/codegenApi';
import {
  fetchImplementAvailable,
  implementCode,
  type ImplementResult,
} from '../../api/implementApi';
import { ApiError } from '../../api/client';
import { Button } from '../common/Button';
import { useToast } from '../common/ToastProvider';
import { CodeViewer } from './CodeViewer';
import shared from './toolbarButtons.module.css';
import styles from './CodeGenPanel.module.css';

const AI_ENABLED_KEY = 'umlframe.codegen.ai';
const AI_NOTES_KEY = 'umlframe.codegen.aiNotes';
const AI_NOTES_MAX_LENGTH = 2000;
const AI_CHOICES = ['on', 'off'] as const;

export function CodeGenPanel() {
  const { token } = useAuthContext();
  const diagram = useDiagramContext();
  const { showToast } = useToast();
  const [languages, setLanguages] = useState<string[]>([]);
  const [selectedLanguage, setSelectedLanguage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [files, setFiles] = useState<Record<string, string> | null>(null);
  const [isViewerOpen, setIsViewerOpen] = useState(false);
  const [aiAvailable, setAiAvailable] = useState(false);
  const [useAi, setUseAi] = useState(
    () => readStoredChoice(AI_ENABLED_KEY, AI_CHOICES, 'off') === 'on',
  );
  const [aiNotes, setAiNotes] = useState(() => readStoredText(AI_NOTES_KEY));
  const [aiReport, setAiReport] = useState<Omit<ImplementResult, 'files'> | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    fetchLanguages()
      .then((langs) => {
        setLanguages(langs);
        setSelectedLanguage(
          (prev) => prev || (langs.includes('python') ? 'python' : langs[0]) || '',
        );
      })
      .catch((err: unknown) => {
        setError(err instanceof ApiError ? err.message : 'Failed to load languages');
      });
  }, []);

  useEffect(() => {
    if (!token) return;
    let isCurrent = true;
    fetchImplementAvailable(token).then((available) => {
      if (isCurrent) setAiAvailable(available);
    });
    return () => {
      isCurrent = false;
    };
  }, [token]);

  const aiActive = useAi && aiAvailable;

  const handleToggleAi = (enabled: boolean) => {
    setUseAi(enabled);
    writeStoredChoice(AI_ENABLED_KEY, enabled ? 'on' : 'off');
  };

  const handleNotesChange = (notes: string) => {
    setAiNotes(notes);
    writeStoredText(AI_NOTES_KEY, notes);
  };

  const handleCancel = () => abortRef.current?.abort();

  const handleGenerate = async () => {
    setIsLoading(true);
    setError(null);
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const document = diagram.toDocument();
      if (aiActive && token) {
        const { files: generated, ...report } = await implementCode(
          token,
          document,
          selectedLanguage,
          aiNotes,
          controller.signal,
        );
        setFiles(generated);
        setAiReport(report);
        showToast(
          report.skipped.length === 0
            ? `Implemented ${report.implemented.length} methods`
            : `Implemented ${report.implemented.length} methods, ${report.skipped.length} kept as stubs`,
          report.implemented.length > 0 ? 'success' : 'info',
        );
      } else {
        setFiles(await generateCode(document, selectedLanguage));
        setAiReport(null);
        showToast('Code generated successfully', 'success');
      }
      setIsViewerOpen(true);
    } catch (err) {
      if (controller.signal.aborted) {
        showToast('Cancelled', 'info');
        return;
      }
      const message = err instanceof ApiError ? err.message : 'Failed to generate code';
      setError(message);
      showToast(message, 'error');
    } finally {
      abortRef.current = null;
      setIsLoading(false);
    }
  };

  const hasClasses = diagram.classes.length > 0;

  return (
    <div className={shared.group}>
      <select
        className={styles.select}
        value={selectedLanguage}
        onChange={(e) => setSelectedLanguage(e.target.value)}
        disabled={languages.length === 0}
      >
        {languages.length === 0 && <option>Loading…</option>}
        {languages.map((lang) => (
          <option key={lang} value={lang}>
            {lang}
          </option>
        ))}
      </select>
      <Button
        size="sm"
        variant="primary"
        icon={Code2}
        disabled={!hasClasses || isLoading || !selectedLanguage}
        onClick={handleGenerate}
        title={
          hasClasses ? 'Generate source code from this diagram' : 'Add at least one class first'
        }
      >
        {isLoading ? (aiActive ? 'Implementing…' : 'Generating…') : 'Generate Code'}
      </Button>
      {isLoading && aiActive && (
        <Button size="sm" variant="ghost" onClick={handleCancel}>
          Cancel
        </Button>
      )}
      <label
        className={styles.aiToggle}
        title={
          aiAvailable
            ? 'Ask a language model to write the method bodies'
            : 'Not available: no LLM is configured on the server'
        }
      >
        <input
          type="checkbox"
          checked={useAi && aiAvailable}
          disabled={!aiAvailable || isLoading}
          onChange={(e) => handleToggleAi(e.target.checked)}
        />
        Implement methods with AI
      </label>
      {aiActive && (
        <label className={styles.aiNotes}>
          <span>How should the methods be implemented? (optional)</span>
          <textarea
            value={aiNotes}
            maxLength={AI_NOTES_MAX_LENGTH}
            disabled={isLoading}
            rows={3}
            placeholder="e.g. keep state in memory, validate arguments and raise ValueError on bad input"
            onChange={(e) => handleNotesChange(e.target.value)}
          />
          <small>
            Your diagram (class names, members, relationships) and these notes are sent to
            OpenRouter. Review the generated code before using it.
          </small>
        </label>
      )}
      {error && (
        <span className={styles.error} title={error}>
          {error}
        </span>
      )}

      {isViewerOpen && files && (
        <CodeViewer files={files} aiReport={aiReport} onClose={() => setIsViewerOpen(false)} />
      )}
    </div>
  );
}
