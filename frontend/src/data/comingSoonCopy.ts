export interface ComingSoonEntry {
  featureName: string;
  description: string;
}

export const COMING_SOON: Record<string, ComingSoonEntry> = {
  'reverse-engineering': {
    featureName: 'Reverse Engineering',
    description:
      'Generating a UML class diagram or Activity Diagram from source code is a planned pipeline (source → AST → Unified UML JSON → Mermaid) but has no backend implementation yet. This card previews the intended feature.',
  },
  'activity-to-code': {
    featureName: 'Activity → Code',
    description:
      'Uploading an activity-diagram image and generating a standalone function with real if/while control-flow structure is planned (Milestone 9) but not yet implemented.',
  },
  'code-to-uml': {
    featureName: 'Code → UML',
    description:
      'Reconstructing a class diagram from source code via an AST parser is planned (Milestones 5/6) but not yet implemented.',
  },
  'code-to-activity': {
    featureName: 'Code → Activity',
    description:
      'Extracting a function’s control flow from source code and rendering it as an activity diagram is planned as an extension of the reverse-engineering pipeline (Milestone 6) but not yet implemented.',
  },
};

export type ComingSoonKey = keyof typeof COMING_SOON;
