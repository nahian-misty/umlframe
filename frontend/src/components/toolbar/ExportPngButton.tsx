import { useState } from 'react';
import { Download } from 'lucide-react';

import { useDiagramContext } from '../../context/DiagramContext';
import { exportCanvasAsPng } from '../../utils/pngExport';
import { Button } from '../common/Button';
import { useToast } from '../common/ToastProvider';

export function ExportPngButton() {
  const diagram = useDiagramContext();
  const { showToast } = useToast();
  const [isExporting, setIsExporting] = useState(false);
  const hasContent = diagram.classes.length > 0 || diagram.shapes.length > 0;

  const handleExport = async () => {
    const bounds = diagram.getContentBounds();
    const node = diagram.contentRef.current;
    if (!bounds || !node) return;
    setIsExporting(true);
    try {
      await exportCanvasAsPng(node, bounds, 'umlframe-diagram.png');
      showToast('Diagram exported as PNG', 'success');
    } catch {
      showToast('Failed to export PNG', 'error');
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <Button
      size="sm"
      icon={Download}
      disabled={!hasContent || isExporting}
      onClick={handleExport}
      title="Export diagram as PNG"
    >
      {isExporting ? 'Exporting…' : 'Export PNG'}
    </Button>
  );
}
