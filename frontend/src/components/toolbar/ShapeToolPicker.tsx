import { Copy, Trash2 } from 'lucide-react';

import { useDiagramContext } from '../../context/DiagramContext';
import type { ToolId } from '../../types/diagram';
import { Button } from '../common/Button';
import shared from './toolbarButtons.module.css';

const TOOLS: { id: ToolId; label: string }[] = [
  { id: 'select', label: 'Select' },
  { id: 'pan', label: 'Pan' },
  { id: 'uml-class', label: 'UML Class' },
  { id: 'rectangle', label: 'Rectangle' },
  { id: 'circle', label: 'Circle' },
  { id: 'diamond', label: 'Diamond' },
  { id: 'line', label: 'Line' },
  { id: 'arrow', label: 'Arrow' },
];

export function ShapeToolPicker() {
  const diagram = useDiagramContext();
  const hasSelection = diagram.selected.length > 0;

  return (
    <div className={shared.group}>
      {TOOLS.map((tool) => (
        <Button
          key={tool.id}
          size="sm"
          active={diagram.activeTool === tool.id}
          onClick={() => diagram.setActiveTool(tool.id)}
          title={tool.label}
        >
          {tool.label}
        </Button>
      ))}
      <div className={shared.divider} />
      <Button
        size="sm"
        icon={Copy}
        disabled={!hasSelection}
        onClick={() => diagram.duplicateSelected()}
        title="Duplicate selection (Ctrl/Cmd+D)"
      >
        Duplicate
      </Button>
      <Button
        size="sm"
        icon={Trash2}
        disabled={!hasSelection}
        onClick={() => diagram.deleteSelected()}
        title="Delete selection (Del)"
      >
        Delete
      </Button>
    </div>
  );
}
