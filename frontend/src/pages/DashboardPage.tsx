import { useEffect, useMemo, useState, type CSSProperties, type FormEvent } from 'react';
import { FolderPlus, LayoutGrid, Search, Trash2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

import { Button } from '../components/common/Button';
import { Modal } from '../components/common/Modal';
import { useToast } from '../components/common/ToastProvider';
import { ProjectThumbnail } from '../components/dashboard/ProjectThumbnail';
import { useAuthContext } from '../context/AuthContext';
import { ApiError } from '../api/client';
import * as projectsApi from '../api/projectsApi';
import type { ProjectSummary } from '../api/projectsApi';
import styles from './DashboardPage.module.css';

type SortBy = 'updated' | 'name';

function formatUpdatedAt(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

function formatClassCount(count: number): string {
  return `${count} class${count === 1 ? '' : 'es'}`;
}

export function DashboardPage() {
  const { token, user } = useAuthContext();
  const { showToast } = useToast();
  const navigate = useNavigate();

  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [pendingDeleteId, setPendingDeleteId] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<SortBy>('updated');

  const visibleProjects = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    const filtered = query
      ? projects.filter((p) => p.name.toLowerCase().includes(query))
      : projects;
    return [...filtered].sort((a, b) =>
      sortBy === 'name'
        ? a.name.localeCompare(b.name)
        : b.updatedAt.localeCompare(a.updatedAt),
    );
  }, [projects, searchQuery, sortBy]);

  useEffect(() => {
    if (!token) return;
    projectsApi
      .listProjects(token)
      .then(setProjects)
      .catch((err) => {
        showToast(err instanceof ApiError ? err.message : 'Failed to load projects.', 'error');
      })
      .finally(() => setIsLoading(false));
  }, [token, showToast]);

  const handleCreateProject = async (event: FormEvent) => {
    event.preventDefault();
    if (!token || !newProjectName.trim()) return;
    setIsCreating(true);
    try {
      const project = await projectsApi.createProject(token, newProjectName.trim());
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
      setProjects((prev) => prev.filter((p) => p.id !== id));
      showToast('Project deleted.', 'success');
    } catch (err) {
      showToast(err instanceof ApiError ? err.message : 'Failed to delete project.', 'error');
    } finally {
      setPendingDeleteId(null);
    }
  };

  return (
    <div className={styles.page}>
      <div className={styles.intro}>
        <div>
          <h1 className={styles.title}>Welcome{user ? `, ${user.email}` : ''}</h1>
          <p className={styles.subtitle}>Pick a project to open, or start a new one.</p>
        </div>
        <Button variant="primary" icon={FolderPlus} onClick={() => setIsCreateModalOpen(true)}>
          New Project
        </Button>
      </div>

      {isLoading && <p className={styles.stateMessage}>Loading your projects…</p>}

      {!isLoading && projects.length === 0 && (
        <div className={styles.emptyState}>
          <LayoutGrid size={28} />
          <p>You don&apos;t have any projects yet.</p>
          <Button variant="primary" icon={FolderPlus} onClick={() => setIsCreateModalOpen(true)}>
            Create your first project
          </Button>
        </div>
      )}

      {!isLoading && projects.length > 0 && (
        <div className={styles.toolbar}>
          <label className={styles.searchField}>
            <Search size={14} />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search projects…"
            />
          </label>
          <select
            className={styles.sortSelect}
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as SortBy)}
            aria-label="Sort projects"
          >
            <option value="updated">Last updated</option>
            <option value="name">Name</option>
          </select>
        </div>
      )}

      {!isLoading && projects.length > 0 && visibleProjects.length === 0 && (
        <p className={styles.stateMessage}>No projects match “{searchQuery}”.</p>
      )}

      {!isLoading && visibleProjects.length > 0 && (
        <div className={styles.grid}>
          {visibleProjects.map((project, i) => (
            <div key={project.id} className={styles.card} style={{ '--i': i } as CSSProperties}>
              <button
                type="button"
                className={styles.cardOpenArea}
                onClick={() => navigate(`/editor/${project.id}`)}
              >
                <ProjectThumbnail classBoxes={project.classBoxes} />
                <span className={styles.cardTitle}>{project.name}</span>
                <span className={styles.cardMeta}>
                  {formatClassCount(project.classCount)} · Updated {formatUpdatedAt(project.updatedAt)}
                </span>
              </button>
              <button
                type="button"
                className={styles.cardDeleteButton}
                aria-label={`Delete ${project.name}`}
                onClick={() => setPendingDeleteId(project.id)}
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
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
