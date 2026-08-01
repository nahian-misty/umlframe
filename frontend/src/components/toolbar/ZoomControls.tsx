import { Magnet, Minus, Plus, RotateCcw } from 'lucide-react';

import { useDiagramContext } from '../../context/DiagramContext';
import { Button } from '../common/Button';
import shared from './toolbarButtons.module.css';

export function ZoomControls() {
  const diagram = useDiagramContext();

  return (
    <div className={shared.group}>
      <Button size="sm" icon={Minus} onClick={diagram.zoomOut} title="Zoom out" />
      <span>{Math.round(diagram.zoom * 100)}%</span>
      <Button size="sm" icon={Plus} onClick={diagram.zoomIn} title="Zoom in" />
      <Button size="sm" icon={RotateCcw} onClick={diagram.resetView} title="Reset view">
        Reset
      </Button>
      <Button
        size="sm"
        icon={Magnet}
        active={diagram.snapEnabled}
        onClick={diagram.toggleSnap}
        title="Toggle snap-to-grid"
      >
        Snap
      </Button>
    </div>
  );
}
