import { CodeGenPanel } from './CodeGenPanel';
import { ExportPngButton } from './ExportPngButton';
import { ImageUploadButton } from './ImageUploadButton';
import { MermaidPreviewButton } from './MermaidPreviewButton';
import { RelationshipPicker } from './RelationshipPicker';
import { ShapeToolPicker } from './ShapeToolPicker';
import { ZoomControls } from './ZoomControls';
import shared from './toolbarButtons.module.css';
import styles from './Toolbar.module.css';

export function Toolbar() {
  return (
    <div className={styles.toolbar}>
      <div className={styles.left}>
        <ShapeToolPicker />
        <div className={shared.divider} />
        <RelationshipPicker />
      </div>
      <div className={shared.divider} />
      <div className={styles.right}>
        <ZoomControls />
        <div className={shared.divider} />
        <ImageUploadButton />
        <ExportPngButton />
        <CodeGenPanel />
        <MermaidPreviewButton />
      </div>
    </div>
  );
}
