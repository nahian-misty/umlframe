import { useEffect, useState } from 'react';
import { Code2 } from 'lucide-react';

import { useDiagramContext } from '../../context/DiagramContext';
import { fetchLanguages, generateCode } from '../../api/codegenApi';
import { ApiError } from '../../api/client';
import { Button } from '../common/Button';
import { useToast } from '../common/ToastProvider';
import { CodeViewer } from './CodeViewer';
import shared from './toolbarButtons.module.css';
import styles from './CodeGenPanel.module.css';

export function CodeGenPanel() {
  const diagram = useDiagramContext();
  const { showToast } = useToast();
  const [languages, setLanguages] = useState<string[]>([]);
  const [selectedLanguage, setSelectedLanguage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [files, setFiles] = useState<Record<string, string> | null>(null);
  const [isViewerOpen, setIsViewerOpen] = useState(false);

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

  const handleGenerate = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const document = diagram.toDocument();
      const result = await generateCode(document, selectedLanguage);
      setFiles(result);
      setIsViewerOpen(true);
      showToast('Code generated successfully', 'success');
    } catch (err) {
      const message = err instanceof ApiError ? err.message : 'Failed to generate code';
      setError(message);
      showToast(message, 'error');
    } finally {
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
        {isLoading ? 'Generating…' : 'Generate Code'}
      </Button>
      {error && (
        <span className={styles.error} title={error}>
          {error}
        </span>
      )}

      {isViewerOpen && files && <CodeViewer files={files} onClose={() => setIsViewerOpen(false)} />}
    </div>
  );
}
