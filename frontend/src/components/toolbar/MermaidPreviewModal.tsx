import { useEffect, useState } from 'react';

import { useDiagramContext } from '../../context/DiagramContext';
import { jsonToMermaid } from '../../api/mermaidApi';
import { ApiError } from '../../api/client';
import { Button } from '../common/Button';
import { Modal } from '../common/Modal';
import { MermaidRenderer } from './MermaidRenderer';
import styles from './MermaidPreviewModal.module.css';

interface MermaidPreviewModalProps {
  onClose: () => void;
}

export function MermaidPreviewModal({ onClose }: MermaidPreviewModalProps) {
  const diagram = useDiagramContext();

  const [error, setError] = useState<string | null>(null);
  const [source, setSource] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let cancelled = false;

    jsonToMermaid(diagram.toDocument())
      .then((diagramText) => {
        if (!cancelled) setSource(diagramText);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : 'Failed to load diagram preview');
        }
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleCopy = () => {
    if (!source) return;
    navigator.clipboard.writeText(source).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };

  return (
    <Modal
      title="Diagram Preview"
      onClose={onClose}
      wide
      footer={
        <Button size="sm" onClick={handleCopy} disabled={!source}>
          {copied ? 'Copied!' : 'Copy Mermaid Source'}
        </Button>
      }
    >
      {error ? <p className={styles.error}>{error}</p> : <MermaidRenderer source={source} />}
    </Modal>
  );
}
