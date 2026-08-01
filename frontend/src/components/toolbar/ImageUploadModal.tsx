import { useState, type ChangeEvent } from 'react';

import { useDiagramContext } from '../../context/DiagramContext';
import { imageToJson } from '../../api/imageApi';
import { ApiError } from '../../api/client';
import { Modal } from '../common/Modal';
import { Button } from '../common/Button';
import { useToast } from '../common/ToastProvider';
import styles from './ImageUploadModal.module.css';

interface ImageUploadModalProps {
  onClose: () => void;
}

export function ImageUploadModal({ onClose }: ImageUploadModalProps) {
  const diagram = useDiagramContext();
  const { showToast } = useToast();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmed, setConfirmed] = useState(false);

  const hasExistingContent =
    diagram.classes.length > 0 || diagram.relationships.length > 0 || diagram.shapes.length > 0;
  const needsConfirmation = hasExistingContent && !confirmed;

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    setError(null);
    setConfirmed(false);
    setSelectedFile(file);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(file ? URL.createObjectURL(file) : null);
  };

  const performUpload = async () => {
    if (!selectedFile) return;
    setIsUploading(true);
    setError(null);
    try {
      const document = await imageToJson(selectedFile);
      diagram.loadDocument(document);
      showToast('Diagram loaded from image', 'success');
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to process image');
    } finally {
      setIsUploading(false);
    }
  };

  const handlePrimaryClick = () => {
    if (needsConfirmation) {
      setConfirmed(true);
      return;
    }
    void performUpload();
  };

  return (
    <Modal
      title="Upload UML Diagram Image"
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handlePrimaryClick}
            disabled={!selectedFile || isUploading}
          >
            {isUploading ? 'Processing…' : needsConfirmation ? 'Replace & Load' : 'Upload & Load'}
          </Button>
        </>
      }
    >
      <input type="file" accept="image/png,image/jpeg" onChange={handleFileChange} />

      {previewUrl && (
        <img className={styles.preview} src={previewUrl} alt="Selected diagram preview" />
      )}

      {needsConfirmation && selectedFile && (
        <div className={styles.warning}>
          This will replace your current diagram. Click "Replace &amp; Load" again to confirm.
        </div>
      )}

      {error && <div className={styles.error}>{error}</div>}
    </Modal>
  );
}
