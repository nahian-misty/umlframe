import { useEffect, useId, useRef, useState } from 'react';
import mermaid from 'mermaid';
import { Download } from 'lucide-react';

import { useTheme } from '../../hooks/useTheme';
import { exportNodeAsPng } from '../../utils/pngExport';
import { Button } from '../common/Button';
import styles from './MermaidPreviewModal.module.css';

interface MermaidRendererProps {
  /** Mermaid diagram source text, or null while it is still loading. */
  source: string | null;
  /** Download filename offered once the diagram has rendered. */
  filename?: string;
}

/**
 * Presentational: renders Mermaid source text to inline SVG in the viewer's
 * theme. Shared by the class-diagram preview and the Code -> Activity flow.
 */
export function MermaidRenderer({ source, filename = 'diagram.png' }: MermaidRendererProps) {
  const { resolvedTheme } = useTheme();
  const renderId = useId().replace(/:/g, '-');
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [rendered, setRendered] = useState(false);

  useEffect(() => {
    if (!source || !containerRef.current) return;
    let cancelled = false;
    setRendered(false);

    mermaid.initialize({
      startOnLoad: false,
      theme: resolvedTheme === 'dark' ? 'dark' : 'default',
    });
    mermaid
      .render(`mermaid-render-${renderId}`, source)
      .then(({ svg }) => {
        if (!cancelled && containerRef.current) {
          containerRef.current.innerHTML = svg;
          setRendered(true);
        }
      })
      .catch(() => {
        if (!cancelled) setError('Failed to render diagram');
      });

    return () => {
      cancelled = true;
    };
  }, [source, resolvedTheme, renderId]);

  const handleDownload = () => {
    if (!containerRef.current) return;
    const backgroundColor = getComputedStyle(document.documentElement)
      .getPropertyValue('--color-surface')
      .trim() || '#ffffff';
    void exportNodeAsPng(containerRef.current, filename, backgroundColor);
  };

  if (error) return <p className={styles.error}>{error}</p>;
  if (!source) return <p className={styles.status}>Loading preview…</p>;
  return (
    <div>
      {rendered && (
        <div className={styles.actions}>
          <Button size="sm" icon={Download} onClick={handleDownload}>
            Download PNG
          </Button>
        </div>
      )}
      <div className={styles.diagramContainer} ref={containerRef} />
    </div>
  );
}
