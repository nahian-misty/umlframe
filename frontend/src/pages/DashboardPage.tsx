import { useEffect, useState, type CSSProperties, type FormEvent } from 'react';
import { ChevronLeft, ChevronRight, FolderPlus, LayoutGrid, Search, Trash2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

import { Button } from '../components/common/Button';
import { Modal } from '../components/common/Modal';
import { useToast } from '../components/common/ToastProvider';
import { EditableProjectName } from '../components/dashboard/EditableProjectName';
import { ProjectThumbnail } from '../components/dashboard/ProjectThumbnail';
import { useAuthContext } from '../context/AuthContext';
import { readStoredChoice, writeStoredChoice } from '../utils/storedPreference';
import { ApiError } from '../api/client';
import * as projectsApi from '../api/projectsApi';
import {
  PROJECT_TYPE_LABELS,
  PROJECTS_PAGE_SIZE,
  type ProjectSort,
  type ProjectSummary,
  type ProjectType,
} from '../api/projectsApi';
import styles from './DashboardPage.module.css';

const SEARCH_DEBOUNCE_MS = 300;

function formatUpdatedAt(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

const PROJECT_TYPES: ProjectType[] = ['uml', 'activity'];
const SORT_OPTIONS: ProjectSort[] = ['updated', 'name'];
const LIST_TYPE_STORAGE_KEY = 'umlframe.dashboard.listType';
const SORT_STORAGE_KEY = 'umlframe.dashboard.sort';

const LIST_TITLES: Record<ProjectType, string> = {
  uml: 'UML Class Diagrams',
  activity: 'Activity Diagrams',
};

function formatSize(project: ProjectSummary): string {
  if (project.projectType === 'activity') {
    return `${project.nodeCount} node${project.nodeCount === 1 ? '' : 's'}`;
  }
  return `${project.classCount} class${project.classCount === 1 ? '' : 'es'}`;
}

export function DashboardPage() {
  const { token, user } = useAuthContext();
  const { showToast } = useToast();
  const navigate = useNavigate();

  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [hasLoaded, setHasLoaded] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectType, setNewProjectType] = useState<ProjectType>('uml');
  const [listType, setListType] = useState<ProjectType>(() =>
    readStoredChoice(LIST_TYPE_STORAGE_KEY, PROJECT_TYPES, 'uml'),
  );
  const [counts, setCounts] = useState<Record<ProjectType, number> | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [pendingDeleteId, setPendingDeleteId] = useState<number | null>(null);
  const [searchInput, setSearchInput] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<ProjectSort>(() =>
    readStoredChoice(SORT_STORAGE_KEY, SORT_OPTIONS, 'updated'),
  );
  const [page, setPage] = useState(0);

  const pageCount = Math.max(1, Math.ceil(total / PROJECTS_PAGE_SIZE));
  const firstShown = total === 0 ? 0 : page * PROJECTS_PAGE_SIZE + 1;
  const lastShown = page * PROJECTS_PAGE_SIZE + projects.length;
  const isSearching = searchQuery.trim() !== '';

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setSearchQuery(searchInput);
      setPage(0);
    }, SEARCH_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [searchInput]);

  useEffect(() => {
    if (!token) return;
    let isCurrent = true;
    Promise.all(
      PROJECT_TYPES.map((type) => projectsApi.listProjects(token, { projectType: type, limit: 1 })),
    )
      .then(([uml, activity]) => {
        if (isCurrent) setCounts({ uml: uml.total, activity: activity.total });
      })
      .catch(() => undefined); // counts are decoration; the list below reports real errors
    return () => {
      isCurrent = false;
    };
  }, [token, reloadKey]);

  useEffect(() => {
    if (!token) return;
    let isCurrent = true;
    projectsApi
      .listProjects(token, {
        search: searchQuery,
        projectType: listType,
        sort: sortBy,
        limit: PROJECTS_PAGE_SIZE,
        offset: page * PROJECTS_PAGE_SIZE,
      })
      .then((result) => {
        if (!isCurrent) return;
        const lastPage = Math.max(0, Math.ceil(result.total / PROJECTS_PAGE_SIZE) - 1);
        if (page > lastPage) {
          setPage(lastPage); // e.g. the last card on this page was just deleted
          return;
        }
        setProjects(result.projects);
        setTotal(result.total);
        setHasLoaded(true);
      })
      .catch((err) => {
        if (!isCurrent) return;
        showToast(err instanceof ApiError ? err.message : 'Failed to load projects.', 'error');
        setHasLoaded(true);
      });
    return () => {
      isCurrent = false;
    };
  }, [token, searchQuery, listType, sortBy, page, reloadKey, showToast]);

  const handleCreateProject = async (event: FormEvent) => {
    event.preventDefault();
    if (!token || !newProjectName.trim()) return;
    setIsCreating(true);
    try {
      const project = await projectsApi.createProject(token, newProjectName.trim(), newProjectType);
      navigate(`/editor/${project.id}`);
    } catch (err) {
      showToast(err instanceof ApiError ? err.message : 'Failed to create project.', 'error');
      setIsCreating(false);
    }
  };

  const handleDeleteProject = async (id: number) => {
    if (!token) return;
    try {
      await projectsApi.deleteProject(token, id);
      setReloadKey((key) => key + 1);
      showToast('Project deleted.', 'success');
    } catch (err) {
      showToast(err instanceof ApiError ? err.message : 'Failed to delete project.', 'error');
    } finally {
      setPendingDeleteId(null);
    }
  };

  const openCreateModal = () => {
    setNewProjectType(listType);
    setIsCreateModalOpen(true);
  };

  const switchList = (type: ProjectType) => {
    if (type === listType) return;
    setListType(type);
    writeStoredChoice(LIST_TYPE_STORAGE_KEY, type);
    setPage(0);
    setHasLoaded(false);
  };

  const handleRenameProject = async (project: ProjectSummary, name: string) => {
    if (!token) return;
    try {
      await projectsApi.updateProject(token, project.id, { name });
      setReloadKey((key) => key + 1);
      showToast('Project renamed.', 'success');
    } catch (err) {
      showToast(err instanceof ApiError ? err.message : 'Failed to rename project.', 'error');
    }
  };

  return (
    <div className={styles.page}>
      <div className={styles.intro}>
        <div>
          <h1 className={styles.title}>Welcome{user ? `, ${user.username}` : ''}</h1>
          <p className={styles.subtitle}>Pick a project to open, or start a new one. UML class diagrams and activity diagrams are kept in separate lists.</p>
        </div>
        <Button variant="primary" icon={FolderPlus} onClick={openCreateModal}>
          New Project
        </Button>
      </div>

      <div className={styles.listTabs} role="tablist" aria-label="Project type">
        {PROJECT_TYPES.map((type) => (
          <button
            key={type}
            type="button"
            role="tab"
            aria-selected={listType === type}
            className={`${styles.listTab} ${listType === type ? styles.listTabActive : ''}`}
            onClick={() => switchList(type)}
          >
            {LIST_TITLES[type]}
            {counts && <span className={styles.listTabCount}>{counts[type]}</span>}
          </button>
        ))}
      </div>

      {!hasLoaded && <p className={styles.stateMessage}>Loading your projects…</p>}

      {hasLoaded && total === 0 && !isSearching && (
        <div className={styles.emptyState}>
          <LayoutGrid size={28} />
          <p>You don&apos;t have any {LIST_TITLES[listType].toLowerCase()} projects yet.</p>
          <Button variant="primary" icon={FolderPlus} onClick={openCreateModal}>
            Create your first {PROJECT_TYPE_LABELS[listType].toLowerCase()} project
          </Button>
        </div>
      )}

      {hasLoaded && (total > 0 || isSearching) && (
        <div className={styles.toolbar}>
          <label className={styles.searchField}>
            <Search size={14} />
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Search projects…"
            />
          </label>
          <select
            className={styles.sortSelect}
            value={sortBy}
            onChange={(e) => {
              const next = e.target.value as ProjectSort;
              setSortBy(next);
              writeStoredChoice(SORT_STORAGE_KEY, next);
              setPage(0);
            }}
            aria-label="Sort projects"
          >
            <option value="updated">Last updated</option>
            <option value="name">Name</option>
          </select>
        </div>
      )}

      {hasLoaded && total === 0 && isSearching && (
        <p className={styles.stateMessage}>No projects match “{searchQuery.trim()}”.</p>
      )}

      {hasLoaded && projects.length > 0 && (
        <div className={styles.grid}>
          {projects.map((project, i) => (
            <div key={project.id} className={styles.card} style={{ '--i': i } as CSSProperties}>
              <div
                className={styles.cardOpenArea}
                onClick={() => navigate(`/editor/${project.id}`)}
              >
                <button
                  type="button"
                  className={styles.cardThumbnailButton}
                  aria-label={`Open ${project.name}`}
                >
                  <ProjectThumbnail classBoxes={project.classBoxes} />
                </button>
                <div className={styles.cardTitle} onClick={(e) => e.stopPropagation()}>
                  <EditableProjectName
                    name={project.name}
                    onRename={(name) => handleRenameProject(project, name)}
                  />
                </div>
                <span className={styles.cardMeta}>
                  {formatSize(project)} · Updated {formatUpdatedAt(project.updatedAt)}
                </span>
              </div>
              <div className={styles.cardActions}>
                <button
                  type="button"
                  className={styles.cardDeleteButton}
                  aria-label={`Delete ${project.name}`}
                  title="Delete"
                  onClick={() => setPendingDeleteId(project.id)}
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {hasLoaded && total > PROJECTS_PAGE_SIZE && (
        <nav className={styles.pagination} aria-label="Project pages">
          <span className={styles.paginationSummary}>
            {firstShown}–{lastShown} of {total}
          </span>
          <Button
            size="sm"
            variant="ghost"
            icon={ChevronLeft}
            disabled={page === 0}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
          >
            Previous
          </Button>
          <span className={styles.paginationSummary}>
            Page {page + 1} of {pageCount}
          </span>
          <Button
            size="sm"
            variant="ghost"
            icon={ChevronRight}
            iconPosition="right"
            disabled={page >= pageCount - 1}
            onClick={() => setPage((p) => Math.min(pageCount - 1, p + 1))}
          >
            Next
          </Button>
        </nav>
      )}

      {isCreateModalOpen && (
        <Modal title="New Project" onClose={() => setIsCreateModalOpen(false)}>
          <form className={styles.createForm} onSubmit={handleCreateProject}>
            <label className={styles.createFormField}>
              <span>Project name</span>
              <input
                autoFocus
                type="text"
                value={newProjectName}
                onChange={(e) => setNewProjectName(e.target.value)}
                placeholder="My UML Project"
              />
            </label>
            <label className={styles.createFormField}>
              <span>Diagram type</span>
              <select
                value={newProjectType}
                onChange={(e) => setNewProjectType(e.target.value as ProjectType)}
              >
                {PROJECT_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {PROJECT_TYPE_LABELS[type]}
                  </option>
                ))}
              </select>
            </label>
            <Button type="submit" variant="primary" disabled={isCreating || !newProjectName.trim()}>
              {isCreating ? 'Creating…' : 'Create'}
            </Button>
          </form>
        </Modal>
      )}

      {pendingDeleteId !== null && (
        <Modal
          title="Delete Project"
          onClose={() => setPendingDeleteId(null)}
          footer={
            <>
              <Button variant="secondary" onClick={() => setPendingDeleteId(null)}>
                Cancel
              </Button>
              <Button variant="danger" onClick={() => handleDeleteProject(pendingDeleteId)}>
                Delete
              </Button>
            </>
          }
        >
          <p>Are you sure you want to delete this project? This cannot be undone.</p>
        </Modal>
      )}
    </div>
  );
}
