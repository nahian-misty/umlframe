import { useState } from 'react';
import { Eraser } from 'lucide-react';

import { Button } from '../common/Button';
import { Modal } from '../common/Modal';

interface ClearDiagramButtonProps {
  disabled: boolean;
  onClear: () => void;
}

/** Clears a whole canvas, but only after confirming: there is no undo. */
export function ClearDiagramButton({ disabled, onClear }: ClearDiagramButtonProps) {
  const [isConfirming, setIsConfirming] = useState(false);

  const confirm = () => {
    setIsConfirming(false);
    onClear();
  };

  return (
    <>
      <Button
        size="sm"
        variant="danger"
        icon={Eraser}
        disabled={disabled}
        onClick={() => setIsConfirming(true)}
        title="Remove everything from the diagram"
      >
        Clear diagram
      </Button>
      {isConfirming && (
        <Modal
          title="Clear diagram"
          onClose={() => setIsConfirming(false)}
          footer={
            <>
              <Button variant="secondary" onClick={() => setIsConfirming(false)}>
                Cancel
              </Button>
              <Button variant="danger" onClick={confirm}>
                Clear everything
              </Button>
            </>
          }
        >
          <p>This removes everything from the diagram. It can&apos;t be undone.</p>
        </Modal>
      )}
    </>
  );
}
