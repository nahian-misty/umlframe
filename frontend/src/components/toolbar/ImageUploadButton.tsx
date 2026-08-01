import { useState } from 'react';
import { ImagePlus } from 'lucide-react';

import { Button } from '../common/Button';
import { ImageUploadModal } from './ImageUploadModal';

export function ImageUploadButton() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <Button
        size="sm"
        icon={ImagePlus}
        onClick={() => setIsOpen(true)}
        title="Upload a UML diagram image and parse it into this editor"
      >
        Upload Image
      </Button>
      {isOpen && <ImageUploadModal onClose={() => setIsOpen(false)} />}
    </>
  );
}
