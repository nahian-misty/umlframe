import { useRef, useState, type PointerEvent as ReactPointerEvent } from 'react';

import { useActivityDiagramContext } from '../../context/ActivityDiagramContext';
import { useViewportNavigation } from '../../hooks/useViewportNavigation';
import { ActivityEdgeView, ActivityMarkerDefs } from '../activity/ActivityEdgeView';
import { ActivityNodeView } from '../activity/ActivityNodeView';
import { ACTIVITY_NODE_SIZES } from '../../utils/constants';
import { normalizeRect, rectsIntersect, snap, type Rect } from '../../utils/geometry';
import type { ActivityNode, ActivityNodeType } from '../../types/activity';
import { CanvasScrollbars } from './CanvasScrollbars';
import { InfiniteGrid } from './InfiniteGrid';
import { SelectionOverlay, type ResizeHandle } from './SelectionOverlay';
import styles from './Canvas.module.css';

const NODE_TOOLS: ActivityNodeType[] = ['start', 'end', 'action', 'decision', 'fork', 'join'];

function rectOf(node: ActivityNode): Rect {
  return {
    x: node.position.x,
    y: node.position.y,
    width: node.size.width,
    height: node.size.height,
  };
}

/** Editable activity-diagram surface; the UML counterpart is Canvas.tsx. */
export function ActivityCanvas() {
  const activity = useActivityDiagramContext();
  const viewportRef = useRef<HTMLDivElement>(null);
  const [marqueeRect, setMarqueeRect] = useState<Rect | null>(null);

  const { toCanvasPoint, startPanDrag } = useViewportNavigation(viewportRef, activity);

  const trackPointer = (onMove: (e: PointerEvent) => void, onUp?: (e: PointerEvent) => void) => {
    const handleUp = (e: PointerEvent) => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', handleUp);
      onUp?.(e);
    };
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', handleUp);
  };

  const handleViewportPointerDown = (e: ReactPointerEvent<HTMLDivElement>) => {
    if (e.button === 1) {
      e.preventDefault();
      startPanDrag(e);
      return;
    }
    if (e.button !== 0) return;
    const tool = activity.activeTool;

    if (tool === 'pan') {
      startPanDrag(e);
      return;
    }

    const point = toCanvasPoint(e.clientX, e.clientY);

    if (NODE_TOOLS.includes(tool as ActivityNodeType)) {
      const type = tool as ActivityNodeType;
      const size = ACTIVITY_NODE_SIZES[type];
      activity.addNode(type, {
        x: snap(point.x - size.width / 2, activity.snapEnabled),
        y: snap(point.y - size.height / 2, activity.snapEnabled),
      });
      return;
    }

    if (tool === 'connect') {
      activity.armConnectSource(null);
      return;
    }

    activity.clearSelection();
    setMarqueeRect({ x: point.x, y: point.y, width: 0, height: 0 });
    trackPointer(
      (ev) => setMarqueeRect(normalizeRect(point, toCanvasPoint(ev.clientX, ev.clientY))),
      (ev) => {
        const finalRect = normalizeRect(point, toCanvasPoint(ev.clientX, ev.clientY));
        if (finalRect.width > 2 || finalRect.height > 2) {
          activity.selectNodes(
            activity.nodes.filter((n) => rectsIntersect(finalRect, rectOf(n))).map((n) => n.id),
          );
        }
        setMarqueeRect(null);
      },
    );
  };

  const handleNodePointerDown = (node: ActivityNode, e: ReactPointerEvent<HTMLDivElement>) => {
    e.stopPropagation();
    if ((e.target as HTMLElement).closest('input')) return;

    if (activity.activeTool === 'connect') {
      const source = activity.pendingConnectSource;
      if (source == null) {
        activity.armConnectSource(node.id);
      } else if (source === node.id) {
        activity.armConnectSource(null);
      } else {
        activity.addEdge(source, node.id);
        activity.armConnectSource(null);
      }
      return;
    }
    if (activity.activeTool !== 'select') return;

    const additive = e.shiftKey || e.ctrlKey || e.metaKey;
    const alreadySelected = activity.selectedNodeIds.includes(node.id);
    let selection: string[];
    if (additive) {
      selection = alreadySelected
        ? activity.selectedNodeIds.filter((id) => id !== node.id)
        : [...activity.selectedNodeIds, node.id];
    } else {
      selection = alreadySelected ? activity.selectedNodeIds : [node.id];
    }
    activity.selectNodes(selection);

    const starts = activity.nodes
      .filter((n) => selection.includes(n.id))
      .map((n) => ({ id: n.id, x: n.position.x, y: n.position.y }));
    trackPointer((ev) => {
      const dx = (ev.clientX - e.clientX) / activity.zoom;
      const dy = (ev.clientY - e.clientY) / activity.zoom;
      activity.moveNodes(
        starts.map((s) => ({
          id: s.id,
          x: snap(s.x + dx, activity.snapEnabled),
          y: snap(s.y + dy, activity.snapEnabled),
        })),
      );
    });
  };

  const selectedNode =
    activity.selectedNodeIds.length === 1 && activity.selectedEdgeIds.length === 0
      ? (activity.nodes.find((n) => n.id === activity.selectedNodeIds[0]) ?? null)
      : null;

  const handleResizeStart = (handle: ResizeHandle, e: ReactPointerEvent<HTMLDivElement>) => {
    if (!selectedNode) return;
    const startRect = rectOf(selectedNode);
    trackPointer((ev) => {
      const dx = (ev.clientX - e.clientX) / activity.zoom;
      const dy = (ev.clientY - e.clientY) / activity.zoom;
      let { x, y, width, height } = startRect;
      if (handle.includes('e')) width += dx;
      if (handle.includes('w')) {
        width -= dx;
        x += dx;
      }
      if (handle.includes('s')) height += dy;
      if (handle.includes('n')) {
        height -= dy;
        y += dy;
      }
      activity.resizeNode(
        selectedNode.id,
        { width: snap(width, activity.snapEnabled), height: snap(height, activity.snapEnabled) },
        { x: snap(x, activity.snapEnabled), y: snap(y, activity.snapEnabled) },
      );
    });
  };

  const nodeById = new Map(activity.nodes.map((n) => [n.id, n]));

  return (
    <div
      ref={viewportRef}
      className={styles.viewport}
      data-active-tool={activity.activeTool}
      onPointerDown={handleViewportPointerDown}
    >
      <InfiniteGrid pan={activity.pan} zoom={activity.zoom} />
      <div
        ref={activity.contentRef}
        className={styles.content}
        style={{
          transform: `translate(${activity.pan.x}px, ${activity.pan.y}px) scale(${activity.zoom})`,
        }}
      >
        <svg className={styles.vectorLayer}>
          <ActivityMarkerDefs />
          {activity.edges.map((edge) => {
            const source = nodeById.get(edge.source);
            const target = nodeById.get(edge.target);
            if (!source || !target) return null;
            return (
              <ActivityEdgeView
                key={edge.id}
                edge={edge}
                source={source}
                target={target}
                isSelected={activity.selectedEdgeIds.includes(edge.id)}
                onSelect={() => activity.selectEdge(edge.id)}
                onUpdateLabel={(label) => activity.updateEdgeLabel(edge.id, label)}
              />
            );
          })}
        </svg>

        {activity.nodes.map((node) => (
          <ActivityNodeView
            key={node.id}
            node={node}
            isSelected={activity.selectedNodeIds.includes(node.id)}
            isPendingConnectSource={activity.pendingConnectSource === node.id}
            onPointerDown={(e) => handleNodePointerDown(node, e)}
            onUpdateLabel={(label) => activity.updateNodeLabel(node.id, label)}
          />
        ))}

        {selectedNode && (
          <SelectionOverlay rect={rectOf(selectedNode)} onResizeStart={handleResizeStart} />
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
      <CanvasScrollbars
        viewportRef={viewportRef}
        pan={activity.pan}
        zoom={activity.zoom}
        contentBounds={activity.getContentBounds()}
        onPan={activity.setPan}
      />
    </div>
  );
}
