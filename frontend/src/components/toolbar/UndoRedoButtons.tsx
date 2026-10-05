import { Redo2, Undo2 } from 'lucide-react';

import { Button } from '../common/Button';
import shared from './toolbarButtons.module.css';

interface UndoRedoButtonsProps {
  canUndo: boolean;
  canRedo: boolean;
  onUndo: () => void;
  onRedo: () => void;
}

export function UndoRedoButtons({ canUndo, canRedo, onUndo, onRedo }: UndoRedoButtonsProps) {
  return (
    <div className={shared.group}>
      <Button size="sm" icon={Undo2} disabled={!canUndo} onClick={onUndo} title="Undo (Ctrl/Cmd+Z)">
        Undo
      </Button>
      <Button
        size="sm"
        icon={Redo2}
        disabled={!canRedo}
        onClick={onRedo}
        title="Redo (Ctrl/Cmd+Shift+Z)"
      >
        Redo
      </Button>
    </div>
  );
}
