export const GRID_SIZE = 20;

export const MIN_ZOOM = 0.25;
export const MAX_ZOOM = 2.5;
export const ZOOM_STEP = 0.1;
export const FIT_VIEW_PADDING = 48;


export const DEFAULT_CLASS_SIZE = { width: 260, height: 170 };
export const MIN_CLASS_SIZE = { width: 200, height: 100 };

export const DEFAULT_SHAPE_SIZE = { width: 120, height: 80 };
export const MIN_SHAPE_SIZE = { width: 20, height: 20 };

export const DUPLICATE_OFFSET = { x: 32, y: 32 };

export const DEFAULT_MULTIPLICITY = { source: '1', destination: '1' };

export const PNG_EXPORT_PADDING = 40;
export const PNG_EXPORT_PIXEL_RATIO = 2;

export const ACTIVITY_NODE_SIZES = {
  start: { width: 40, height: 40 },
  end: { width: 40, height: 40 },
  action: { width: 160, height: 60 },
  decision: { width: 160, height: 100 },
  fork: { width: 140, height: 12 },
  join: { width: 140, height: 12 },
} as const;
export const MIN_ACTIVITY_NODE_SIZE = { width: 20, height: 10 };
export const ACTIVITY_LAYOUT = {
  columnGap: 260,
  rowGap: 140,
  originX: 650,
  originY: 60,
} as const;
export const ACTIVITY_BACK_EDGE_OFFSET = 110;

export const MIN_SCROLLBAR_THUMB = 32;

export const WHEEL_ZOOM_SENSITIVITY = 0.001;
export const MIN_GRID_SCREEN_SPACING = 8;
export const GRID_COARSE_FACTOR = 5;
