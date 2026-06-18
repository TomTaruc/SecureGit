import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import PageShell from '../components/layout/PageShell';
import Button from '../components/ui/Button';
import Badge from '../components/ui/Badge';
import { Skeleton } from '../components/ui/Spinner';
import { TimeAgo } from '../components/shared/SharedComponents';
import EmptyState from '../components/ui/EmptyState';
import * as dashboardApi from '../api/dashboard';
import * as projectsApi from '../api/projects';
import useAuthStore from '../store/authStore';

function StatCard({ label, value, loading }) {
  return (
    <div style={{
      background: 'var(--color-surface)',
      border: 'var(--border)',
      borderRadius: 'var(--radius-md)',
      padding: 'var(--space-5) var(--space-6)',
    }}>
      {loading ? (
        <>
          <Skeleton height="28px" width="60px" style={{ marginBottom: 'var(--space-2)' }} />
          <Skeleton height="12px" width="80px" />
        </>
      ) : (
        <>
          <div style={{ fontFamily: 'var(--font-mono)', fontWeight: '700', fontSize: '28px', color: 'var(--color-text-primary)', marginBottom: 'var(--space-1)' }}>
            {value ?? '—'}
          </div>
          <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
            {label}
          </div>
        </>
      )}
    </div>
  );
}

const activityDots = {
  'push':         { color: 'var(--color-success)', label: '↑' },
  'auth.login':   { color: 'var(--color-text-muted)', label: '→' },
  'project.create': { color: 'var(--color-text-secondary)', label: '+' },
  'ssh_key.add':  { color: 'var(--color-warning)', label: '⚷' },
};

function DashboardSidebar({ projects, loading }) {
  const navigate = useNavigate();
  const displayProjects = projects.slice(0, 8);

  return (
    <div style={{ padding: '0 var(--space-3)' }}>
      <SidebarSection label="YOUR PROJECTS">
        {loading ? (
          [1,2,3].map(i => <Skeleton key={i} height="28px" style={{ marginBottom: '4px' }} />)
        ) : displayProjects.length === 0 ? (
          <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', padding: 'var(--space-2) var(--space-3)', display: 'block' }}>
            No projects yet
          </span>
        ) : (
          displayProjects.map(p => (
            <Link
              key={p.project_id}
              to={`/${p.owner}/${p.project_name}`}
              style={{
                display: 'block', padding: 'var(--space-2) var(--space-3)',
                fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)',
                borderRadius: 'var(--radius-md)', textDecoration: 'none',
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              }}
              onMouseEnter={e => e.currentTarget.style.background = 'var(--color-surface-2)'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
            >
              {p.project_name}
            </Link>
          ))
        )}
        {projects.length > 8 && (
          <Link to="/projects" style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', padding: 'var(--space-1) var(--space-3)', display: 'block' }}>
            View all {projects.length} →
          </Link>
        )}
      </SidebarSection>

      <SidebarSection label="QUICK ACTIONS">
        <SidebarAction to="/projects/new">+ New Project</SidebarAction>
        <SidebarAction to="/settings/ssh-keys">Manage SSH Keys</SidebarAction>
        <SidebarAction to="/settings/account">Account Settings</SidebarAction>
      </SidebarSection>
    </div>
  );
}

function SidebarSection({ label, children }) {
  return (
    <div style={{ marginBottom: 'var(--space-6)' }}>
      <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', padding: 'var(--space-2) var(--space-3)', marginBottom: 'var(--space-1)' }}>
        {label}
      </div>
      {children}
    </div>
  );
}

function SidebarAction({ to, children }) {
  return (
    <Link to={to} style={{
      display: 'block', padding: 'var(--space-2) var(--space-3)',
      fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)',
      borderRadius: 'var(--radius-md)', textDecoration: 'none',
    }}
    onMouseEnter={e => { e.currentTarget.style.background = 'var(--color-surface-2)'; e.currentTarget.style.color = 'var(--color-text-primary)'; }}
    onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--color-text-muted)'; }}
    >
      {children}
    </Link>
  );
}

export default function DashboardPage() {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const [stats, setStats]       = useState(null);
  const [activity, setActivity] = useState([]);
  const [projects, setProjects] = useState([]);
  const [loading, setLoading]   = useState(true);

  useEffect(() => {
    Promise.all([
      dashboardApi.getStats(),
      dashboardApi.getActivity(20),
      projectsApi.listProjects(),
    ]).then(([s, a, p]) => {
      setStats(s.data);
      setActivity(a.data);
      setProjects(p.data);
    }).finally(() => setLoading(false));
  }, []);

  return (
    <PageShell sidebar={<DashboardSidebar projects={projects} loading={loading} />}>
      <div style={{ maxWidth: '900px' }}>
        <h1 style={{ fontSize: 'var(--font-size-xl)', fontWeight: '600', marginBottom: 'var(--space-6)' }}>
          Dashboard
        </h1>

        {/* Stats grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 'var(--space-4)', marginBottom: 'var(--space-8)' }}>
          <StatCard label="Projects"      value={stats?.total_projects} loading={loading} />
          <StatCard label="Commits Today" value={stats?.commits_today}  loading={loading} />
          <StatCard label="Active Users"  value={stats?.active_users}   loading={loading} />
          <StatCard label="SSH Keys"      value={stats?.ssh_keys_count} loading={loading} />
        </div>

        {/* Projects list */}
        <div style={{ marginBottom: 'var(--space-8)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-4)' }}>
            <h2 style={{ fontSize: 'var(--font-size-md)', fontWeight: '600' }}>Your Projects</h2>
            <Button variant="secondary" size="sm" onClick={() => navigate('/projects/new')}>
              + New Project
            </Button>
          </div>

          <div style={{ background: 'var(--color-surface)', border: 'var(--border)', borderRadius: 'var(--radius-md)', overflow: 'hidden' }}>
            {loading ? (
              [1,2,3].map(i => (
                <div key={i} style={{ padding: 'var(--space-4) var(--space-5)', borderBottom: 'var(--border)', display: 'flex', gap: 'var(--space-4)' }}>
                  <div style={{ flex: 1 }}><Skeleton height="16px" width="40%" style={{ marginBottom: '8px' }} /><Skeleton height="12px" width="70%" /></div>
                  <Skeleton height="16px" width="80px" />
                </div>
              ))
            ) : projects.length === 0 ? (
              <EmptyState title="No projects yet" description="Create your first repository to get started." action={() => navigate('/projects/new')} actionLabel="+ New Project" />
            ) : (
              projects.map(p => (
                <div key={p.project_id} style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: 'var(--space-4) var(--space-5)',
                  borderBottom: 'var(--border)',
                }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
                      <Link to={`/${p.owner}/${p.project_name}`} style={{ fontWeight: '500', fontSize: 'var(--font-size-md)', color: 'var(--color-text-primary)', textDecoration: 'none' }}>
                        {p.project_name}
                      </Link>
                      <Badge variant="default">
                        🔒 {p.visibility}
                      </Badge>
                    </div>
                    {p.description && (
                      <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)', marginTop: 'var(--space-1)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {p.description}
                      </p>
                    )}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)', flexShrink: 0 }}>
                    <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                      ● {p.default_branch || 'main'}
                    </span>
                    <TimeAgo dateString={p.updated_at} />
                    <Button variant="ghost" size="sm" onClick={() => navigate(`/${p.owner}/${p.project_name}`)}>View</Button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Recent activity */}
        <div>
          <h2 style={{ fontSize: 'var(--font-size-sm)', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--color-text-muted)', marginBottom: 'var(--space-4)' }}>
            Recent Activity
          </h2>
          <div style={{ background: 'var(--color-surface)', border: 'var(--border)', borderRadius: 'var(--radius-md)', overflow: 'hidden' }}>
            {activity.length === 0 ? (
              <div style={{ padding: 'var(--space-6)', textAlign: 'center', color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>
                No recent activity.
              </div>
            ) : (
              activity.map(e => {
                const dot = activityDots[e.action] || { color: 'var(--color-text-muted)', label: '·' };
                return (
                  <div key={e.log_id} style={{
                    display: 'flex', alignItems: 'center', gap: 'var(--space-3)',
                    padding: 'var(--space-3) var(--space-5)',
                    borderBottom: 'var(--border)',
                  }}>
                    <span style={{ color: dot.color, width: '16px', textAlign: 'center', flexShrink: 0, fontSize: 'var(--font-size-sm)' }}>{dot.label}</span>
                    <span style={{ fontSize: 'var(--font-size-sm)', flex: 1 }}>
                      <strong style={{ color: 'var(--color-text-primary)' }}>{e.actor}</strong>
                      <span style={{ color: 'var(--color-text-secondary)' }}> {e.action.replace('.', ' ')} </span>
                      {e.detail && <span style={{ color: 'var(--color-text-muted)' }}>{e.detail}</span>}
                    </span>
                    <TimeAgo dateString={e.occurred_at} />
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </PageShell>
  );
}
