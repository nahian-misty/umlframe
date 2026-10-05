import { useCssColors } from '../../hooks/useCssColors';

/** Shared <marker> definitions referenced by every RelationshipEdge's line. Render once per canvas. */
const MARKER_COLOR_VARS = { text: '--color-text', surface: '--color-surface' };
const MARKER_STROKE = 1.5;

export function RelationshipMarkerDefs() {
  const colors = useCssColors(MARKER_COLOR_VARS);
  return (
    <defs>
      <marker
        id="arrow-open"
        viewBox="0 0 10 10"
        refX="9"
        refY="5"
        markerWidth="9"
        markerHeight="9"
        orient="auto"
      >
        <path d="M1,1 L9,5 L1,9" fill="none" stroke={colors.text} strokeWidth={MARKER_STROKE} />
      </marker>
      <marker
        id="triangle-hollow"
        viewBox="0 0 12 12"
        refX="11"
        refY="6"
        markerWidth="12"
        markerHeight="12"
        orient="auto"
      >
        <path
          d="M1,1 L11,6 L1,11 Z"
          fill={colors.surface}
          stroke={colors.text}
          strokeWidth={MARKER_STROKE}
        />
      </marker>
      <marker
        id="diamond-hollow"
        viewBox="0 0 12 12"
        refX="1"
        refY="6"
        markerWidth="12"
        markerHeight="12"
        orient="auto"
      >
        <path
          d="M1,6 L6,1 L11,6 L6,11 Z"
          fill={colors.surface}
          stroke={colors.text}
          strokeWidth={MARKER_STROKE}
        />
      </marker>
      <marker
        id="diamond-filled"
        viewBox="0 0 12 12"
        refX="1"
        refY="6"
        markerWidth="12"
        markerHeight="12"
        orient="auto"
      >
        <path
          d="M1,6 L6,1 L11,6 L6,11 Z"
          fill={colors.text}
          stroke={colors.text}
          strokeWidth={MARKER_STROKE}
        />
      </marker>
    </defs>
  );
}
