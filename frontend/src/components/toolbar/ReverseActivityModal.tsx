import { useState } from 'react';

import { reverseToControlFlow, REVERSE_LANGUAGES, type ReverseLanguage } from '../../api/reverseApi';
import { activityJsonToMermaid } from '../../api/mermaidApi';
import { ApiError } from '../../api/client';
import { Modal } from '../common/Modal';
import { Button } from '../common/Button';
import { MermaidRenderer } from './MermaidRenderer';
import styles from './PipelineModal.module.css';

interface ReverseActivityModalProps {
  onClose: () => void;
}

export function ReverseActivityModal({ onClose }: ReverseActivityModalProps) {
  const [source, setSource] = useState('');
  const [language, setLanguage] = useState<ReverseLanguage>('python');
  const [className, setClassName] = useState('');
  const [methodName, setMethodName] = useState('');
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mermaidSource, setMermaidSource] = useState<string | null>(null);

  const runExtract = async () => {
    setIsBusy(true);
    setError(null);
    try {
      const controlFlow = await reverseToControlFlow(source, language, className, methodName);
      setMermaidSource(await activityJsonToMermaid(controlFlow));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to extract control flow');
    } finally {
      setIsBusy(false);
    }
  };

  const canRun = source.trim() && className.trim() && methodName.trim() && !isBusy;

  return (
    <Modal
      title="Code → Activity Diagram"
      onClose={onClose}
      wide
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Close
          </Button>
          <Button variant="primary" onClick={() => void runExtract()} disabled={!canRun}>
            {isBusy ? 'Extracting…' : 'Extract Control Flow'}
          </Button>
        </>
      }
    >
      <div className={styles.form}>
        <div className={styles.row}>
          <div className={styles.field}>
            <span className={styles.label}>Language</span>
            <select
              className={styles.select}
              value={language}
              onChange={(e) => setLanguage(e.target.value as ReverseLanguage)}
            >
              {REVERSE_LANGUAGES.map((lang) => (
                <option key={lang} value={lang}>
                  {lang}
                </option>
              ))}
            </select>
          </div>
          <div className={styles.field}>
            <span className={styles.label}>Class name</span>
            <input
              className={styles.input}
              value={className}
              onChange={(e) => setClassName(e.target.value)}
            />
          </div>
          <div className={styles.field}>
            <span className={styles.label}>Method name</span>
            <input
              className={styles.input}
              value={methodName}
              onChange={(e) => setMethodName(e.target.value)}
            />
          </div>
        </div>

        <div className={styles.field}>
          <span className={styles.label}>Source code</span>
          <textarea
            className={styles.textarea}
            value={source}
            spellCheck={false}
            onChange={(e) => setSource(e.target.value)}
          />
        </div>

        {error && <div className={styles.error}>{error}</div>}
        {mermaidSource && <MermaidRenderer source={mermaidSource} />}
      </div>
    </Modal>
  );
}
