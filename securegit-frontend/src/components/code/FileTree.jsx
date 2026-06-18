import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

const FolderIcon = () => (
  <svg width="14" height="14" viewBox="0 0 16 16" fill="none" style={{ flexShrink: 0 }}>
    <path d="M1.5 3.5A1 1 0 012.5 2.5H6l1.5 1.5H13.5A1 1 0 0114.5 5v7a1 1 0 01-1 1h-11a1 1 0 01-1-1V4" stroke="#6B6B6B" strokeWidth="1.2" strokeLinecap="round"/>
    <path d="M1.5 5.5h13" stroke="#6B6B6B" strokeWidth="1.2"/>
  </svg>
);

const FileIcon = () => (
  <svg width="14" height="14" viewBox="0 0 16 16" fill="none" style={{ flexShrink: 0 }}>
    <path d="M3.5 1.5H9.5L13 5.5V14.5A.5.5 0 0112.5 15H3.5A.5.5 0 013 14.5V2A.5.5 0 013.5 1.5Z" stroke="#555" strokeWidth="1.2"/>
    <path d="M9.5 1.5V5.5H13" stroke="#555" strokeWidth="1.2"/>
  </svg>
);

/**
 * FileTree — renders git ls-tree result as navigable table.
 * Entries format: [{name, type ('tree'|'blob'), size, hash}]
 */
export default function FileTree({
  entries = [],
  username,
  projectName,
  branch,
  currentPath = '',
  onNavigate, // (path) => void — for folder navigation
}) {
  const navigate = useNavigate();

  const breadcrumbs = currentPath ? ['root', ...currentPath.split('/')] : ['root'];

  const handleEntry = (entry) => {
    if (entry.type === 'tree') {
      const newPath = currentPath ? `${currentPath}/${entry.name}` : entry.name;
      if (onNavigate) onNavigate(newPath);
    } else {
      const filePath = currentPath ? `${currentPath}/${entry.name}` : entry.name;
      navigate(`/${username}/${projectName}/blob/${branch}/${filePath}`);
    }
  };

  return (
    <div>
      {/* Breadcrumb */}
      {currentPath && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 'var(--space-1)',
          padding: 'var(--space-2) var(--space-4)',
          fontSize: 'var(--font-size-sm)',
          borderBottom: 'var(--border)',
          color: 'var(--color-text-muted)',
        }}>
          {breadcrumbs.map((crumb, i) => (
            <React.Fragment key={i}>
              {i > 0 && <span style={{ color: 'var(--color-border-light)' }}>/</span>}
              <span
                style={{
                  cursor: i < breadcrumbs.length - 1 ? 'pointer' : 'default',
                  color: i < breadcrumbs.length - 1 ? 'var(--color-text-secondary)' : 'var(--color-text-primary)',
                }}
                onClick={() => {
                  if (i === 0) onNavigate && onNavigate('');
                  else {
                    const path = breadcrumbs.slice(1, i + 1).join('/');
                    onNavigate && onNavigate(path);
                  }
                }}
              >
                {crumb}
              </span>
            </React.Fragment>
          ))}
        </div>
      )}

      {/* Entries table */}
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <tbody>
          {entries.map((entry, i) => (
            <tr
              key={i}
              style={{
                borderBottom: 'var(--border)',
                cursor: 'pointer',
                transition: 'background var(--transition-fast)',
              }}
              onClick={() => handleEntry(entry)}
              onMouseEnter={(e) => e.currentTarget.style.background = 'var(--color-surface-2)'}
              onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
            >
              {/* Icon + name */}
              <td style={{
                padding: 'var(--space-2) var(--space-4)',
                width: '40%',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                  {entry.type === 'tree' ? <FolderIcon /> : <FileIcon />}
                  <span style={{
                    fontSize: 'var(--font-size-sm)',
                    color: entry.type === 'tree' ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
                    fontFamily: entry.type === 'blob' ? 'var(--font-mono)' : 'inherit',
                  }}>
                    {entry.name}
                  </span>
                </div>
              </td>

              {/* Size / time */}
              <td style={{
                padding: 'var(--space-2) var(--space-4)',
                fontSize: 'var(--font-size-xs)',
                color: 'var(--color-text-muted)',
                textAlign: 'right',
                whiteSpace: 'nowrap',
              }}>
                {entry.type === 'blob' && entry.size != null
                  ? `${entry.size < 1024 ? entry.size + ' B' : Math.round(entry.size / 1024) + ' KB'}`
                  : ''}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {entries.length === 0 && (
        <div style={{
          padding: 'var(--space-8)', textAlign: 'center',
          color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)',
        }}>
          Empty directory.
        </div>
      )}
    </div>
  );
}
