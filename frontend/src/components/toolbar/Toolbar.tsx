import { useDiagramContext } from '../../context/DiagramContext';
import { ClearDiagramButton } from './ClearDiagramButton';
import { CodeGenPanel } from './CodeGenPanel';
import { ExportPngButton } from './ExportPngButton';
import { ImageUploadButton } from './ImageUploadButton';
import { MermaidPreviewButton } from './MermaidPreviewButton';
import { RelationshipPicker } from './RelationshipPicker';
import { UndoRedoButtons } from './UndoRedoButtons';
import { ShapeToolPicker } from './ShapeToolPicker';
import { ZoomControls } from './ZoomControls';
import shared from './toolbarButtons.module.css';
import styles from './Toolbar.module.css';

export function Toolbar() {
  const diagram = useDiagramContext();
  const isEmpty =
    diagram.classes.length === 0 &&
    diagram.relationships.length === 0 &&
    diagram.shapes.length === 0;

  return (
    <div className={styles.toolbar}>
      <div className={styles.left}>
        <UndoRedoButtons
          canUndo={diagram.canUndo}
          canRedo={diagram.canRedo}
          onUndo={diagram.undo}
          onRedo={diagram.redo}
        />
        <div className={shared.divider} />
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
        <ClearDiagramButton disabled={isEmpty} onClear={diagram.clear} />
        <CodeGenPanel />
        <MermaidPreviewButton />
      </div>
    </div>
  );
}
