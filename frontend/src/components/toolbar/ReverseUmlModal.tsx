import { useState } from 'react';

import { useDiagramContext } from '../../context/DiagramContext';
import { reverseToJson, REVERSE_LANGUAGES, type ReverseLanguage } from '../../api/reverseApi';
import { ApiError } from '../../api/client';
import { Modal } from '../common/Modal';
import { Button } from '../common/Button';
import { useToast } from '../common/ToastProvider';
import styles from './PipelineModal.module.css';

interface ReverseUmlModalProps {
  onClose: () => void;
}

export function ReverseUmlModal({ onClose }: ReverseUmlModalProps) {
  const diagram = useDiagramContext();
  const { showToast } = useToast();
  const [source, setSource] = useState('');
  const [language, setLanguage] = useState<ReverseLanguage>('python');
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
      const document = await reverseToJson(source, language);
      diagram.loadDocument(document);
      showToast('Diagram reconstructed from source', 'success');
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to parse source');
    } finally {
      setIsBusy(false);
    }
  };

  const handlePrimary = () => {
    if (needsConfirmation) {
      setConfirmed(true);
      return;
    }
    void runReverse();
  };

  return (
    <Modal
      title="Code → UML Class Diagram"
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handlePrimary}
            disabled={!source.trim() || isBusy}
          >
            {isBusy
              ? 'Parsing…'
              : needsConfirmation
                ? 'Replace & Load'
                : 'Parse & Load'}
          </Button>
        </>
      }
    >
      <div className={styles.form}>
        <div className={styles.field}>
          <span className={styles.label}>Source language</span>
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
          <span className={styles.label}>Source code</span>
          <textarea
            className={styles.textarea}
            value={source}
            spellCheck={false}
            placeholder={'class User:\n    def __init__(self, email: str) -> None:\n        self.email = email'}
            onChange={(e) => setSource(e.target.value)}
          />
        </div>

        {needsConfirmation && (
          <div className={styles.warning}>
            This will replace your current diagram. Click “Replace &amp; Load” again to confirm.
          </div>
        )}

        {error && <div className={styles.error}>{error}</div>}
      </div>
    </Modal>
  );
}
