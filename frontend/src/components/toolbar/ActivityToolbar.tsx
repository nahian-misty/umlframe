import { useState, type ReactNode } from 'react';
import { Copy, Download, Magnet, Minus, Plus, RotateCcw, Trash2 } from 'lucide-react';

import { useActivityDiagramContext } from '../../context/ActivityDiagramContext';
import { exportCanvasAsPng } from '../../utils/pngExport';
import type { ActivityToolId } from '../../hooks/useActivityDiagram';
import { Button } from '../common/Button';
import { ActivityImageUploadButton } from './ActivityImageUploadButton';
import { ClearDiagramButton } from './ClearDiagramButton';
import { FitToContentButton } from './FitToContentButton';
import { UndoRedoButtons } from './UndoRedoButtons';
import { useToast } from '../common/ToastProvider';
import shared from './toolbarButtons.module.css';
import styles from './Toolbar.module.css';

const TOOLS: { id: ActivityToolId; label: string }[] = [
  { id: 'select', label: 'Select' },
  { id: 'pan', label: 'Pan' },
  { id: 'start', label: 'Start' },
  { id: 'action', label: 'Action' },
  { id: 'decision', label: 'Decision' },
  { id: 'end', label: 'End' },
  { id: 'fork', label: 'Fork' },
  { id: 'join', label: 'Join' },
  { id: 'connect', label: 'Connect' },
];

interface ActivityToolbarProps {
  children?: ReactNode;
}

/** Right-hand sidebar shared by both activity tabs: palette, view controls, export. */
export function ActivityToolbar({ children }: ActivityToolbarProps) {
  const activity = useActivityDiagramContext();
  const { showToast } = useToast();
  const [isExporting, setIsExporting] = useState(false);
  const hasSelection = activity.selectedNodeIds.length + activity.selectedEdgeIds.length > 0;
  const hasStart = activity.nodes.some((n) => n.type === 'start');

  const handleExport = async () => {
    const bounds = activity.getContentBounds();
    const node = activity.contentRef.current;
    if (!bounds || !node) return;
    setIsExporting(true);
    try {
      await exportCanvasAsPng(node, bounds, 'umlframe-activity-diagram.png');
      showToast('Activity diagram exported as PNG', 'success');
    } catch {
      showToast('Failed to export PNG', 'error');
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className={styles.toolbar}>
      <div className={styles.left}>
        <UndoRedoButtons
          canUndo={activity.canUndo}
          canRedo={activity.canRedo}
          onUndo={activity.undo}
          onRedo={activity.redo}
        />
        <div className={shared.group}>
          {TOOLS.map((tool) => (
            <Button
              key={tool.id}
              size="sm"
              active={activity.activeTool === tool.id}
              disabled={tool.id === 'start' && hasStart}
              onClick={() => {
                activity.armConnectSource(null);
                activity.setActiveTool(tool.id);
              }}
              title={
                tool.id === 'start' && hasStart
                  ? 'A diagram can only have one Start node'
                  : tool.label
              }
            >
              {tool.label}
            </Button>
          ))}
        </div>
        <p className={shared.hint}>
          Pick a node, click the canvas to place it. Use Connect: click a source then a target.
          Double-click a node or an edge label to edit it.
        </p>
        <div className={shared.group}>
          <Button
            size="sm"
            icon={Copy}
            disabled={activity.selectedNodeIds.length === 0}
            onClick={activity.duplicateSelected}
            title="Duplicate selection (Ctrl/Cmd+D)"
          >
            Duplicate
          </Button>
          <Button
            size="sm"
            icon={Trash2}
            disabled={!hasSelection}
            onClick={activity.deleteSelected}
            title="Delete selection (Delete)"
          >
            Delete
          </Button>
        </div>
      </div>
      <div className={shared.divider} />
      <div className={styles.right}>
        <div className={shared.group}>
          <Button size="sm" icon={Minus} onClick={activity.zoomOut} title="Zoom out" />
          <span>{Math.round(activity.zoom * 100)}%</span>
          <Button size="sm" icon={Plus} onClick={activity.zoomIn} title="Zoom in" />
          <Button size="sm" icon={RotateCcw} onClick={activity.resetView} title="Reset view">
            Reset
          </Button>
          <FitToContentButton canvas={activity} />
          <Button
            size="sm"
            icon={Magnet}
            active={activity.snapEnabled}
            onClick={activity.toggleSnap}
            title="Toggle snap-to-grid"
          >
            Snap
          </Button>
        </div>
        <ActivityImageUploadButton />
        <Button
          size="sm"
          icon={Download}
          disabled={activity.nodes.length === 0 || isExporting}
          onClick={() => void handleExport()}
          title="Export diagram as PNG"
        >
          {isExporting ? 'Exporting…' : 'Export PNG'}
        </Button>
        <ClearDiagramButton
          disabled={activity.nodes.length === 0}
          onClear={() => activity.clear({ undoable: true })}
        />
        {children}
      </div>
    </div>
  );
}
