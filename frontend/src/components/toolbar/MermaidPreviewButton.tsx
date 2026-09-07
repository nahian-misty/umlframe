import { useState } from 'react';
import { GitBranch } from 'lucide-react';

import { useDiagramContext } from '../../context/DiagramContext';
import { Button } from '../common/Button';
import { MermaidPreviewModal } from './MermaidPreviewModal';

export function MermaidPreviewButton() {
  const diagram = useDiagramContext();
  const [isOpen, setIsOpen] = useState(false);
  const hasClasses = diagram.classes.length > 0;

  return (
    <>
      <Button
        size="sm"
        icon={GitBranch}
        disabled={!hasClasses}
        onClick={() => setIsOpen(true)}
        title={hasClasses ? 'Preview this diagram as Mermaid' : 'Add at least one class first'}
      >
        Preview Diagram
      </Button>
      {isOpen && <MermaidPreviewModal onClose={() => setIsOpen(false)} />}
    </>
  );
}
