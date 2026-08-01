import { useState } from 'react';

import styles from './CodeViewer.module.css';

interface CodeViewerProps {
  files: Record<string, string>;
  onClose: () => void;
}

export function CodeViewer({ files, onClose }: CodeViewerProps) {
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
