import type { ProjectType } from '../../api/projectsApi';
import { PIPELINE_TABS, type PipelineTabId } from './pipelineTabConfig';
import styles from './Tabs.module.css';

interface PipelineTabsProps {
  projectType: ProjectType;
  activeTab: PipelineTabId;
  onChange: (tab: PipelineTabId) => void;
}

export function PipelineTabs({ projectType, activeTab, onChange }: PipelineTabsProps) {
  return (
    <div className={styles.tabBar} role="tablist">
      {PIPELINE_TABS.filter((tab) => tab.projectType === projectType).map((tab) => (
        <button
          key={tab.id}
          type="button"
          role="tab"
          aria-selected={activeTab === tab.id}
          className={`${styles.tab} ${activeTab === tab.id ? styles.tabActive : ''}`}
          onClick={() => onChange(tab.id)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
