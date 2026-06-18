import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import PageShell from '../components/layout/PageShell';
import Button from '../components/ui/Button';
import Input from '../components/ui/Input';
import Badge from '../components/ui/Badge';
import { Skeleton } from '../components/ui/Spinner';
import EmptyState from '../components/ui/EmptyState';
import { TimeAgo } from '../components/shared/SharedComponents';
import * as projectsApi from '../api/projects';

export default function ProjectsPage() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading]   = useState(true);
  const [search, setSearch]     = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    projectsApi.listProjects()
      .then(r => setProjects(r.data || []))
      .finally(() => setLoading(false));
  }, []);

  const filtered = projects.filter(p => p.project_name.toLowerCase().includes(search.toLowerCase()));

  return (
    <PageShell>
      <div style={{ maxWidth: '1000px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-6)' }}>
          <h1 style={{ fontSize: 'var(--font-size-2xl)', fontWeight: '600' }}>Projects</h1>
          <Button onClick={() => navigate('/projects/new')}>+ New Project</Button>
        </div>

        <div style={{ marginBottom: 'var(--space-5)' }}>
          <Input
            placeholder="Find a repository..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>

        <div style={{ background: 'var(--color-surface)', border: 'var(--border)', borderRadius: 'var(--radius-md)', overflow: 'hidden' }}>
          {loading ? (
            [1,2,3,4].map(i => (
              <div key={i} style={{ padding: 'var(--space-5)', borderBottom: 'var(--border)' }}>
                <Skeleton height="20px" width="30%" style={{ marginBottom: 'var(--space-2)' }} />
                <Skeleton height="14px" width="60%" />
              </div>
            ))
          ) : filtered.length === 0 ? (
            <EmptyState title="No projects found" description={search ? "Try a different search term" : "You don't have access to any projects yet."} />
          ) : (
            filtered.map((p, i) => (
              <div key={p.project_id} style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: 'var(--space-5)',
                borderBottom: i < filtered.length - 1 ? 'var(--border)' : 'none',
              }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', marginBottom: 'var(--space-2)' }}>
                    <Link to={`/${p.owner}/${p.project_name}`} style={{ fontSize: 'var(--font-size-lg)', fontWeight: '600', color: 'var(--color-text-primary)', textDecoration: 'none' }} onMouseEnter={e => e.currentTarget.style.textDecoration = 'underline'} onMouseLeave={e => e.currentTarget.style.textDecoration = 'none'}>
                      {p.owner} / {p.project_name}
                    </Link>
                    <Badge variant="default">🔒 {p.visibility}</Badge>
                  </div>
                  {p.description && <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)', marginBottom: 'var(--space-2)' }}>{p.description}</p>}
                  <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', display: 'flex', gap: 'var(--space-4)' }}>
                    <span>Updated <TimeAgo dateString={p.updated_at} /></span>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </PageShell>
  );
}
