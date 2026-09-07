import { useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from 'react';

import { useDiagramContext } from '../../context/DiagramContext';
import { RelationshipEdge } from '../uml/RelationshipEdge';
import { RelationshipMarkerDefs } from '../uml/RelationshipMarkerDefs';
import { UmlClassBox } from '../uml/UmlClassBox';
import {
  CANVAS_HEIGHT,
  CANVAS_WIDTH,
  DEFAULT_CLASS_SIZE,
  DEFAULT_SHAPE_SIZE,
} from '../../utils/constants';
import { clamp, normalizeRect, rectsIntersect, snap, type Rect } from '../../utils/geometry';
import type { GenericShape, SelectableRef, ShapeKind, UmlClassState } from '../../types/diagram';
import { Grid } from './Grid';
import { SelectionOverlay, type ResizeHandle } from './SelectionOverlay';
import { ShapeRenderer } from './ShapeRenderer';
import styles from './Canvas.module.css';

const SHAPE_TOOLS: ShapeKind[] = ['rectangle', 'circle', 'diamond', 'line', 'arrow'];

function rectOf(item: {
  position: { x: number; y: number };
  size: { width: number; height: number };
}): Rect {
  return {
    x: item.position.x,
    y: item.position.y,
    width: item.size.width,
    height: item.size.height,
  };
}

export function Canvas() {
  const diagram = useDiagramContext();
  const viewportRef = useRef<HTMLDivElement>(null);
  const [marqueeRect, setMarqueeRect] = useState<Rect | null>(null);

  // The canvas is a bounded, finite page (CANVAS_WIDTH x CANVAS_HEIGHT) rather
  // than an infinitely pannable surface — pan is always clamped so the page
  // can't be scrolled away from entirely.
  const clampPan = (nextPan: { x: number; y: number }, zoom: number) => {
    const viewportRect = viewportRef.current?.getBoundingClientRect();
    if (!viewportRect) return nextPan;
    const scaledWidth = CANVAS_WIDTH * zoom;
    const scaledHeight = CANVAS_HEIGHT * zoom;
    const minX = Math.min(0, viewportRect.width - scaledWidth);
    const maxX = Math.max(0, viewportRect.width - scaledWidth);
    const minY = Math.min(0, viewportRect.height - scaledHeight);
    const maxY = Math.max(0, viewportRect.height - scaledHeight);
    return {
      x: clamp(nextPan.x, minX, maxX),
      y: clamp(nextPan.y, minY, maxY),
    };
  };

  // Native (non-passive) wheel listener so ctrl/cmd+wheel zoom can preventDefault
  // the browser's page-zoom gesture; React's onWheel is passive by default.
  useEffect(() => {
    const el = viewportRef.current;
    if (!el) return;

    const onWheelNative = (e: WheelEvent) => {
      e.preventDefault();
      if (e.ctrlKey || e.metaKey) {
        diagram.setZoom(diagram.zoom - e.deltaY * 0.001);
      } else {
        diagram.setPan(
          clampPan({ x: diagram.pan.x - e.deltaX, y: diagram.pan.y - e.deltaY }, diagram.zoom),
        );
      }
    };

    el.addEventListener('wheel', onWheelNative, { passive: false });
    return () => el.removeEventListener('wheel', onWheelNative);
  }, [diagram]);

  // Re-clamp whenever zoom changes (e.g. via the toolbar's zoom buttons, which
  // bypass the handlers above) or the viewport is resized.
  useEffect(() => {
    diagram.setPan(clampPan(diagram.pan, diagram.zoom));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [diagram.zoom]);

  useEffect(() => {
    const onResize = () => diagram.setPan(clampPan(diagram.pan, diagram.zoom));
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, [diagram]);

  const toCanvasPoint = (clientX: number, clientY: number) => {
    const viewportRect = viewportRef.current?.getBoundingClientRect();
    if (!viewportRect) return { x: 0, y: 0 };
    return {
      x: (clientX - viewportRect.left - diagram.pan.x) / diagram.zoom,
      y: (clientY - viewportRect.top - diagram.pan.y) / diagram.zoom,
    };
  };

  const handleViewportPointerDown = (e: ReactPointerEvent<HTMLDivElement>) => {
    if (e.button !== 0) return;

    if (diagram.activeTool === 'pan') {
      const startClientX = e.clientX;
      const startClientY = e.clientY;
      const startPan = diagram.pan;
      const onMove = (ev: PointerEvent) => {
        diagram.setPan(
          clampPan(
            {
              x: startPan.x + (ev.clientX - startClientX),
              y: startPan.y + (ev.clientY - startClientY),
            },
            diagram.zoom,
          ),
        );
      };
      const onUp = () => {
        window.removeEventListener('pointermove', onMove);
        window.removeEventListener('pointerup', onUp);
      };
      window.addEventListener('pointermove', onMove);
      window.addEventListener('pointerup', onUp);
      return;
    }

    const canvasPoint = toCanvasPoint(e.clientX, e.clientY);

    if (diagram.activeTool === 'uml-class') {
      diagram.addClass({
        x: snap(canvasPoint.x - DEFAULT_CLASS_SIZE.width / 2, diagram.snapEnabled),
        y: snap(canvasPoint.y - DEFAULT_CLASS_SIZE.height / 2, diagram.snapEnabled),
      });
      diagram.setActiveTool('select');
      return;
    }

    if (SHAPE_TOOLS.includes(diagram.activeTool as ShapeKind)) {
      const kind = diagram.activeTool as ShapeKind;
      diagram.addShape(kind, {
        x: snap(canvasPoint.x - DEFAULT_SHAPE_SIZE.width / 2, diagram.snapEnabled),
        y: snap(canvasPoint.y - DEFAULT_SHAPE_SIZE.height / 2, diagram.snapEnabled),
      });
      diagram.setActiveTool('select');
      return;
    }

    if (diagram.activeTool === 'relationship') {
      diagram.cancelPendingRelationship();
      return;
    }

    // select tool, empty background: start a marquee selection
    diagram.clearSelection();
    const start = canvasPoint;
    setMarqueeRect({ x: start.x, y: start.y, width: 0, height: 0 });

    const onMove = (ev: PointerEvent) => {
      const current = toCanvasPoint(ev.clientX, ev.clientY);
      setMarqueeRect(normalizeRect(start, current));
    };
    const onUp = (ev: PointerEvent) => {
      const current = toCanvasPoint(ev.clientX, ev.clientY);
      const finalRect = normalizeRect(start, current);
      if (finalRect.width > 2 || finalRect.height > 2) {
        const hitClasses = diagram.classes.filter((c) => rectsIntersect(finalRect, rectOf(c)));
        const hitShapes = diagram.shapes.filter((s) => rectsIntersect(finalRect, rectOf(s)));
        diagram.selectMany([
          ...hitClasses.map((c): SelectableRef => ({ kind: 'class', id: c.id })),
          ...hitShapes.map((s): SelectableRef => ({ kind: 'shape', id: s.id })),
        ]);
      }
      setMarqueeRect(null);
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
    };
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
  };

  const handleItemPointerDown = (
    kind: 'class' | 'shape',
    id: string,
    e: ReactPointerEvent<HTMLDivElement>,
  ) => {
    e.stopPropagation();

    if (diagram.activeTool === 'relationship') {
      if (kind !== 'class') return;
      if (diagram.pendingRelationshipSource == null) {
        diagram.armRelationshipSource(id);
      } else if (diagram.pendingRelationshipSource === id) {
        diagram.cancelPendingRelationship();
      } else {
        diagram.addRelationship(
          diagram.pendingRelationshipSource,
          id,
          diagram.activeRelationshipType ?? 'association',
        );
        diagram.cancelPendingRelationship();
      }
      return;
    }

    // Let clicks on form controls (name/attribute/method fields, modifier
    // chips, remove buttons) behave natively — edit/select text, toggle,
    // etc. — instead of being hijacked into a box selection/drag. Only
    // applies to the select tool: the relationship tool (handled above)
    // still needs a click anywhere on the box, including its name field, to
    // arm/complete a connection.
    const target = e.target as HTMLElement;
    if (target.closest('input, select, textarea, button')) return;

    if (diagram.activeTool !== 'select') return;

    const ref: SelectableRef = { kind, id };
    const alreadySelected = diagram.isSelected(ref);
    const additive = e.shiftKey || e.ctrlKey || e.metaKey;

    let effectiveSelection: SelectableRef[];
    if (additive) {
      effectiveSelection = alreadySelected
        ? diagram.selected.filter((r) => !(r.kind === kind && r.id === id))
        : [...diagram.selected, ref];
      diagram.selectMany(effectiveSelection);
    } else if (alreadySelected) {
      effectiveSelection = diagram.selected;
    } else {
      effectiveSelection = [ref];
      diagram.select(ref);
    }

    const classStarts = effectiveSelection
      .filter((r) => r.kind === 'class')
      .map((r) => diagram.classes.find((c) => c.id === r.id))
      .filter((c): c is UmlClassState => c != null)
      .map((c) => ({ id: c.id, x: c.position.x, y: c.position.y }));
    const shapeStarts = effectiveSelection
      .filter((r) => r.kind === 'shape')
      .map((r) => diagram.shapes.find((s) => s.id === r.id))
      .filter((s): s is GenericShape => s != null)
      .map((s) => ({ id: s.id, x: s.position.x, y: s.position.y }));

    const startClientX = e.clientX;
    const startClientY = e.clientY;

    const onMove = (ev: PointerEvent) => {
      const dx = (ev.clientX - startClientX) / diagram.zoom;
      const dy = (ev.clientY - startClientY) / diagram.zoom;
      if (classStarts.length) {
        diagram.moveClasses(
          classStarts.map((p) => ({
            id: p.id,
            x: snap(p.x + dx, diagram.snapEnabled),
            y: snap(p.y + dy, diagram.snapEnabled),
          })),
        );
      }
      if (shapeStarts.length) {
        diagram.moveShapes(
          shapeStarts.map((p) => ({
            id: p.id,
            x: snap(p.x + dx, diagram.snapEnabled),
            y: snap(p.y + dy, diagram.snapEnabled),
          })),
        );
      }
    };
    const onUp = () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
    };
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
  };

  const selectedSingle = diagram.selected.length === 1 ? diagram.selected[0] : null;
  const selectedRect: Rect | null = (() => {
    if (!selectedSingle) return null;
    if (selectedSingle.kind === 'class') {
      const c = diagram.classes.find((c) => c.id === selectedSingle.id);
      return c ? rectOf(c) : null;
    }
    if (selectedSingle.kind === 'shape') {
      const s = diagram.shapes.find((s) => s.id === selectedSingle.id);
      return s ? rectOf(s) : null;
    }
    return null;
  })();

  const handleResizeStart = (handle: ResizeHandle, e: ReactPointerEvent<HTMLDivElement>) => {
    if (!selectedSingle || !selectedRect) return;
    const startRect = selectedRect;
    const startClientX = e.clientX;
    const startClientY = e.clientY;

    const onMove = (ev: PointerEvent) => {
      const dx = (ev.clientX - startClientX) / diagram.zoom;
      const dy = (ev.clientY - startClientY) / diagram.zoom;
      let { x, y, width, height } = startRect;
      if (handle.includes('e')) width = startRect.width + dx;
      if (handle.includes('w')) {
        width = startRect.width - dx;
        x = startRect.x + dx;
      }
      if (handle.includes('s')) height = startRect.height + dy;
      if (handle.includes('n')) {
        height = startRect.height - dy;
        y = startRect.y + dy;
      }
      const size = {
        width: snap(width, diagram.snapEnabled),
        height: snap(height, diagram.snapEnabled),
      };
      const position = { x: snap(x, diagram.snapEnabled), y: snap(y, diagram.snapEnabled) };
      if (selectedSingle.kind === 'class') diagram.resizeClass(selectedSingle.id, size, position);
      else diagram.resizeShape(selectedSingle.id, size, position);
    };
    const onUp = () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
    };
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
  };

  return (
    <div
      ref={viewportRef}
      className={styles.viewport}
      data-active-tool={diagram.activeTool}
      onPointerDown={handleViewportPointerDown}
    >
      <div
        ref={diagram.contentRef}
        className={styles.content}
        style={{
          transform: `translate(${diagram.pan.x}px, ${diagram.pan.y}px) scale(${diagram.zoom})`,
        }}
      >
        <Grid />
        <svg className={styles.vectorLayer}>
          <RelationshipMarkerDefs />
          {diagram.relationships.map((rel) => {
            const source = diagram.classes.find((c) => c.id === rel.source);
            const destination = diagram.classes.find((c) => c.id === rel.destination);
            if (!source || !destination) return null;
            return (
              <RelationshipEdge
                key={rel.id}
                relationship={rel}
                sourceBox={rectOf(source)}
                destinationBox={rectOf(destination)}
                isSelected={diagram.isSelected({ kind: 'relationship', id: rel.id })}
                onSelect={() => diagram.select({ kind: 'relationship', id: rel.id })}
                onUpdateLabel={(label) => diagram.updateRelationship(rel.id, { label })}
                onUpdateMultiplicity={(which, value) =>
                  diagram.updateRelationship(rel.id, {
                    multiplicity: { ...rel.multiplicity, [which]: value },
                  })
                }
              />
            );
          })}
        </svg>

        {diagram.shapes.map((shape) => (
          <ShapeRenderer
            key={shape.id}
            shape={shape}
            isSelected={diagram.isSelected({ kind: 'shape', id: shape.id })}
            onPointerDown={(e) => handleItemPointerDown('shape', shape.id, e)}
          />
        ))}

        {diagram.classes.map((cls) => (
          <UmlClassBox
            key={cls.id}
            cls={cls}
            isSelected={diagram.isSelected({ kind: 'class', id: cls.id })}
            isPendingRelationshipSource={diagram.pendingRelationshipSource === cls.id}
            onPointerDownBox={(e) => handleItemPointerDown('class', cls.id, e)}
            onUpdate={(patch) => diagram.updateClass(cls.id, patch)}
          />
        ))}

        {selectedSingle && selectedRect && (
          <SelectionOverlay rect={selectedRect} onResizeStart={handleResizeStart} />
        )}

        {marqueeRect && (
          <div
            className={styles.marquee}
            style={{
              left: marqueeRect.x,
              top: marqueeRect.y,
              width: marqueeRect.width,
              height: marqueeRect.height,
            }}
          />
        )}
      </div>
    </div>
  );
}
