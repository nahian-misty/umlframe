import { useEffect, useId, useRef, useState } from 'react';
import mermaid from 'mermaid';

import { useTheme } from '../../hooks/useTheme';
import styles from './MermaidPreviewModal.module.css';

interface MermaidRendererProps {
  /** Mermaid diagram source text, or null while it is still loading. */
  source: string | null;
}

/**
 * Presentational: renders Mermaid source text to inline SVG in the viewer's
 * theme. Shared by the class-diagram preview and the Code -> Activity flow.
 */
export function MermaidRenderer({ source }: MermaidRendererProps) {
  const { resolvedTheme } = useTheme();
  const renderId = useId().replace(/:/g, '-');
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!source || !containerRef.current) return;
    let cancelled = false;

    mermaid.initialize({
      startOnLoad: false,
      theme: resolvedTheme === 'dark' ? 'dark' : 'default',
    });
    mermaid
      .render(`mermaid-render-${renderId}`, source)
      .then(({ svg }) => {
        if (!cancelled && containerRef.current) containerRef.current.innerHTML = svg;
      })
      .catch(() => {
        if (!cancelled) setError('Failed to render diagram');
      });

    return () => {
      cancelled = true;
    };
  }, [source, resolvedTheme, renderId]);

  if (error) return <p className={styles.error}>{error}</p>;
  if (!source) return <p className={styles.status}>Loading preview…</p>;
  return <div className={styles.diagramContainer} ref={containerRef} />;
}
