import { useState, type ChangeEvent } from 'react';

import { activityImageToJson, generateActivityCode } from '../../api/activityApi';
import { ApiError } from '../../api/client';
import { Modal } from '../common/Modal';
import { Button } from '../common/Button';
import { CodeViewer } from './CodeViewer';
import styles from './PipelineModal.module.css';

const LANGUAGES = ['python', 'java', 'javascript'] as const;

interface ActivityCodeModalProps {
  onClose: () => void;
}

export function ActivityCodeModal({ onClose }: ActivityCodeModalProps) {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [language, setLanguage] = useState<string>('python');
  const [functionName, setFunctionName] = useState('');
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [files, setFiles] = useState<Record<string, string> | null>(null);

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const next = event.target.files?.[0] ?? null;
    setError(null);
    setFile(next);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(next ? URL.createObjectURL(next) : null);
  };

  const handleGenerate = async () => {
    if (!file) return;
    setIsBusy(true);
    setError(null);
    try {
      const document = await activityImageToJson(file);
      const result = await generateActivityCode(document, language, functionName);
      setFiles(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to generate activity code');
    } finally {
      setIsBusy(false);
    }
  };

  if (files) {
    return <CodeViewer files={files} onClose={onClose} />;
  }

  return (
    <Modal
      title="Activity Diagram → Code"
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="primary" onClick={handleGenerate} disabled={!file || isBusy}>
            {isBusy ? 'Generating…' : 'Generate Function'}
          </Button>
        </>
      }
    >
      <div className={styles.form}>
        <div className={styles.field}>
          <span className={styles.label}>Activity-diagram image (PNG or JPEG)</span>
          <input type="file" accept="image/png,image/jpeg" onChange={handleFileChange} />
        </div>

        {previewUrl && <img className={styles.preview} src={previewUrl} alt="Selected diagram" />}

        <div className={styles.row}>
          <div className={styles.field}>
            <span className={styles.label}>Target language</span>
            <select
              className={styles.select}
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
          <div className={styles.field}>
            <span className={styles.label}>Function name (optional)</span>
            <input
              className={styles.input}
              value={functionName}
              placeholder="generated_function"
              onChange={(e) => setFunctionName(e.target.value)}
            />
          </div>
        </div>

        {error && <div className={styles.error}>{error}</div>}
      </div>
    </Modal>
  );
}
