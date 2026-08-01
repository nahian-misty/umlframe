import { Modal } from '../common/Modal';
import { Button } from '../common/Button';
import styles from './ComingSoonModal.module.css';

interface ComingSoonModalProps {
  featureName: string;
  description: string;
  onClose: () => void;
}

export function ComingSoonModal({ featureName, description, onClose }: ComingSoonModalProps) {
  return (
    <Modal
      title={`${featureName} — Not Yet Implemented`}
      onClose={onClose}
      footer={
        <Button variant="primary" onClick={onClose}>
          Close
        </Button>
      }
    >
      <p className={styles.body}>{description}</p>
    </Modal>
  );
}
