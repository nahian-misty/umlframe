import { useState } from 'react';
import { ImagePlus } from 'lucide-react';

import { Button } from '../common/Button';
import { ActivityImageUploadModal } from './ActivityImageUploadModal';

export function ActivityImageUploadButton() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <Button
        size="sm"
        icon={ImagePlus}
        onClick={() => setIsOpen(true)}
        title="Upload an activity diagram image and parse it into this editor"
      >
        Upload Image
      </Button>
      {isOpen && <ActivityImageUploadModal onClose={() => setIsOpen(false)} />}
    </>
  );
}
