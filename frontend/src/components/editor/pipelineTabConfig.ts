import type { ProjectType } from '../../api/projectsApi';

export type PipelineTabId = 'uml-code' | 'code-uml' | 'activity-code' | 'code-activity';

export const PIPELINE_TABS: { id: PipelineTabId; label: string; projectType: ProjectType }[] = [
  { id: 'uml-code', label: 'UML → Code', projectType: 'uml' },
  { id: 'code-uml', label: 'Code → UML', projectType: 'uml' },
  { id: 'activity-code', label: 'Activity → Code', projectType: 'activity' },
  { id: 'code-activity', label: 'Code → Activity', projectType: 'activity' },
];

export function firstTabFor(projectType: ProjectType): PipelineTabId {
  return PIPELINE_TABS.find((tab) => tab.projectType === projectType)!.id;
}
