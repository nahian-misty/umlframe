import { useEffect, useState } from 'react';

function readColors<K extends string>(vars: Record<K, string>): Record<K, string> {
  const style = getComputedStyle(document.documentElement);
  const result = {} as Record<K, string>;
  for (const key of Object.keys(vars) as K[]) {
    result[key] = style.getPropertyValue(vars[key]).trim();
  }
  return result;
}

/**
 * Resolves CSS custom properties to literal colors. SVG drawn on the canvas is
 * rasterized by html-to-image, which loses `var()` references, classes and
 * inline styles on SVG elements; only literal presentation attributes survive.
 * Re-reads whenever the theme changes.
 */
export function useCssColors<K extends string>(vars: Record<K, string>): Record<K, string> {
  const [colors, setColors] = useState(() => readColors(vars));

  useEffect(() => {
    const refresh = () => setColors(readColors(vars));
    refresh();
    const observer = new MutationObserver(refresh);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-theme', 'class'],
    });
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    media.addEventListener('change', refresh);
    return () => {
      observer.disconnect();
      media.removeEventListener('change', refresh);
    };
    // vars is a module-level constant at every call site.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return colors;
}
