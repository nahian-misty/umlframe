import { useState } from 'react';

import type { ImplementResult } from '../../api/implementApi';
import styles from './CodeViewer.module.css';

interface CodeViewerProps {
  files: Record<string, string>;
  /** Present when the bodies were written by a language model. */
  aiReport?: Omit<ImplementResult, 'files'> | null;
  onClose: () => void;
}

export function CodeViewer({ files, aiReport = null, onClose }: CodeViewerProps) {
  const filenames = Object.keys(files);
  const [activeFile, setActiveFile] = useState(filenames[0] ?? '');
  const content = files[activeFile] ?? '';

  const handleCopy = () => {
    void navigator.clipboard.writeText(content);
  };

  const handleDownload = () => {
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = activeFile;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className={styles.backdrop} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <strong>Generated Code</strong>
          <button className={styles.closeButton} onClick={onClose} type="button" title="Close">
            ×
          </button>
        </div>
        {aiReport && (
          <div className={styles.aiBanner} role="note">
            <strong>AI-written method bodies — review before use.</strong> Implemented{' '}
            {aiReport.implemented.length} of {aiReport.implemented.length + aiReport.skipped.length}{' '}
            methods
            {aiReport.models.length > 0 && <> using {aiReport.models.join(', ')}</>}.
            {aiReport.skipped.length > 0 && (
              <details className={styles.aiSkipped}>
                <summary>{aiReport.skipped.length} kept as stubs</summary>
                <ul>
                  {aiReport.skipped.map((skip) => (
                    <li key={skip.key}>
                      <code>{skip.key}</code>: {skip.reason}
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </div>
        )}
        <div className={styles.tabs}>
          {filenames.map((name) => (
            <button
              key={name}
              type="button"
              className={`${styles.tab} ${name === activeFile ? styles.tabActive : ''}`}
              onClick={() => setActiveFile(name)}
            >
              {name}
            </button>
          ))}
        </div>
        <div className={styles.actions}>
          <button className={styles.actionButton} onClick={handleCopy} type="button">
            Copy
          </button>
          <button className={styles.actionButton} onClick={handleDownload} type="button">
            Download file
          </button>
        </div>
        <pre className={styles.codePane}>
          <code>{content}</code>
        </pre>
      </div>
    </div>
  );
}
