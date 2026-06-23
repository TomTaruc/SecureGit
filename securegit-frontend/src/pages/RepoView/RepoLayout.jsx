import React, { useEffect, useState } from 'react';
import { Outlet, NavLink, useParams, useNavigate } from 'react-router-dom';
import PageShell from '../../components/layout/PageShell';
import Badge from '../../components/ui/Badge';
import { CopyButton } from '../../components/shared/SharedComponents';
import { Skeleton } from '../../components/ui/Spinner';
import * as projectsApi from '../../api/projects';
import * as branchesApi from '../../api/branches';

export default function RepoLayout() {
  const { username, projectName } = useParams();
  const [project, setProject]     = useState(null);
  const [branches, setBranches]   = useState([]);
  const [branch, setBranch]       = useState('main');
  const [loading, setLoading]     = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    Promise.all([
      projectsApi.getProject(username, projectName),
      branchesApi.listBranches(username, projectName),
    ]).then(([p, b]) => {
      setProject(p.data);
      setBranches(b.data || []);
      setBranch(p.data.default_branch || 'main');
    }).catch(() => navigate('/404'))
      .finally(() => setLoading(false));
  }, [username, projectName]);

  const tabs = [
    { label: 'Code',     to: `/${username}/${projectName}` },
    { label: 'Commits',  to: `/${username}/${projectName}/commits` },
    { label: 'Branches', to: `/${username}/${projectName}/branches` },
    { label: 'Access',   to: `/${username}/${projectName}/access`, show: project?.can_manage_collaborators },
    { label: 'Merge',    to: `/${username}/${projectName}/merge`, show: project?.can_push },
    { label: 'Protection', to: `/${username}/${projectName}/protection`, show: project?.can_manage_settings },
    { label: 'Webhooks',   to: `/${username}/${projectName}/webhooks`, show: project?.can_manage_settings },
  ].filter(t => t.show === undefined || t.show);

  return (
    <PageShell>
      <div style={{ width: '100%', maxWidth: 'none' }}>
        {/* Repo header */}
        <div style={{ marginBottom: 'var(--space-4)' }}>
          {loading ? (
            <Skeleton height="24px" width="300px" />
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', flexWrap: 'wrap' }}>
              <h1 style={{ fontSize: 'var(--font-size-xl)', fontWeight: '600' }}>
                <span style={{ color: 'var(--color-text-muted)' }}>{username}</span>
                <span style={{ color: 'var(--color-border-light)', margin: '0 var(--space-2)' }}>/</span>
                {projectName}
              </h1>
              <Badge variant="default">🔒 {project?.visibility}</Badge>
              {/* Clone URL */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginLeft: 'auto', minWidth: 0, maxWidth: '100%', flexWrap: 'wrap' }}>
                <code style={{
                  fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)',
                  background: 'var(--color-surface-2)', padding: '4px 10px',
                  borderRadius: 'var(--radius-sm)', border: 'var(--border)',
                  color: 'var(--color-text-secondary)',
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                }}>
                  {project?.clone_url}
                </code>
                <CopyButton text={project?.clone_url || ''} label="Clone via SSH" />
              </div>
            </div>
          )}
        </div>

        {/* Sub-navigation tabs */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: '2px',
          borderBottom: 'var(--border)',
          marginBottom: 'var(--space-5)',
        }}>
          {tabs.map(tab => (
            <RepoTab key={tab.label} to={tab.to} label={tab.label} />
          ))}
        </div>

        {/* Branch selector (passed via context to children) */}
        {!loading && (
          <Outlet context={{ project, branches, branch, setBranch, username, projectName }} />
        )}
      </div>
    </PageShell>
  );
}

function RepoTab({ to, label }) {
  return (
    <NavLink
      to={to}
      end
      style={({ isActive }) => ({
        padding: 'var(--space-2) var(--space-4)',
        fontSize: 'var(--font-size-sm)',
        fontWeight: '500',
        color: isActive ? 'var(--color-text-primary)' : 'var(--color-text-muted)',
        borderBottom: isActive ? '2px solid var(--color-text-primary)' : '2px solid transparent',
        textDecoration: 'none',
        transition: 'color var(--transition-fast)',
        marginBottom: '-1px',
      })}
    >
      {label}
    </NavLink>
  );
}
