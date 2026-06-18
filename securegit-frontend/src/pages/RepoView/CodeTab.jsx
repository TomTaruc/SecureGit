import React, { useState, useEffect } from 'react';
import { useOutletContext, useNavigate } from 'react-router-dom';
import FileTree from '../../components/code/FileTree';
import { Skeleton } from '../../components/ui/Spinner';
import EmptyState from '../../components/ui/EmptyState';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import * as projectsApi from '../../api/projects';

export default function CodeTab() {
  const { project, branch, username, projectName, branches, setBranch } = useOutletContext();
  const [entries, setEntries]     = useState([]);
  const [readme,  setReadme]      = useState(null);
  const [currentPath, setCurrentPath] = useState('');
  const [loading, setLoading]     = useState(true);
  const [commitInfo, setCommitInfo] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!project) return;
    setLoading(true);
    Promise.all([
      projectsApi.getTree(username, projectName, { branch, path: currentPath }),
      currentPath === '' ? projectsApi.getReadme(username, projectName, branch) : Promise.resolve(null),
    ]).then(([tree, readme]) => {
      setEntries(tree.data || []);
      if (readme) setReadme(readme.data?.content);
    }).finally(() => setLoading(false));
  }, [project, branch, currentPath, username, projectName]);

  if (!project) return null;

  return (
    <div>
      {/* Branch selector + last commit info */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 'var(--space-3)',
        marginBottom: 'var(--space-4)', flexWrap: 'wrap',
      }}>
        <select
          value={branch}
          onChange={e => { setBranch(e.target.value); setCurrentPath(''); }}
          style={{
            background: 'var(--color-surface-2)', border: 'var(--border)',
            borderRadius: 'var(--radius-md)', padding: '6px 12px',
            color: 'var(--color-text-primary)', fontSize: 'var(--font-size-sm)',
            fontFamily: 'var(--font-sans)', cursor: 'pointer',
          }}
        >
          {branches.map(b => (
            <option key={b.name} value={b.name}>{b.name}{b.is_default ? ' (default)' : ''}</option>
          ))}
        </select>
      </div>

      {/* File tree */}
      <div style={{ background: 'var(--color-surface)', border: 'var(--border)', borderRadius: 'var(--radius-md)', overflow: 'hidden', marginBottom: 'var(--space-5)' }}>
        {loading ? (
          <div style={{ padding: 'var(--space-4)' }}>
            {[1,2,3,4,5].map(i => <Skeleton key={i} height="36px" style={{ marginBottom: '4px' }} />)}
          </div>
        ) : entries.length === 0 ? (
          <EmptyState
            icon="📂"
            title="This repository is empty"
            description={`Push code via: git remote add origin ${project?.clone_url}`}
          />
        ) : (
          <FileTree
            entries={entries}
            username={username}
            projectName={projectName}
            branch={branch}
            currentPath={currentPath}
            onNavigate={setCurrentPath}
          />
        )}
      </div>

      {/* README */}
      {readme && (
        <div style={{
          background: 'var(--color-surface)', border: 'var(--border)',
          borderRadius: 'var(--radius-md)', padding: 'var(--space-6)',
        }}>
          <div style={{
            fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)',
            textTransform: 'uppercase', letterSpacing: '0.08em',
            marginBottom: 'var(--space-4)', paddingBottom: 'var(--space-3)',
            borderBottom: 'var(--border)',
          }}>
            README.md
          </div>
          <div className="markdown-body">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{readme}</ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
}
