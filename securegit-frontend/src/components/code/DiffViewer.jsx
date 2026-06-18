import React, { useState } from 'react';

/**
 * DiffViewer — renders structured diff JSON from /api/commits/{hash}/diff
 * Accepts: fileDiffs = [{filename, changeType, linesAdded, linesDeleted, hunks}]
 */
export default function DiffViewer({ fileDiffs = [] }) {
  if (!fileDiffs.length) {
    return (
      <div style={{ padding: 'var(--space-8)', textAlign: 'center', color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>
        No changes in this commit.
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
      {fileDiffs.map((file, i) => (
        <FileDiffPanel key={i} file={file} />
      ))}
    </div>
  );
}

function FileDiffPanel({ file }) {
  const [collapsed, setCollapsed] = useState(false);

  const changeColor = {
    added:    'var(--color-success-text)',
    deleted:  'var(--color-error-text)',
    modified: 'var(--color-text-secondary)',
    renamed:  'var(--color-warning-text)',
  }[file.changeType || file.change_type] || 'var(--color-text-secondary)';

  return (
    <div style={{
      border: 'var(--border)',
      borderRadius: 'var(--radius-md)',
      overflow: 'hidden',
      fontFamily: 'var(--font-mono)',
      fontSize: 'var(--font-size-sm)',
    }}>
      {/* File header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: 'var(--space-2) var(--space-4)',
        background: 'var(--color-surface-2)',
        borderBottom: collapsed ? 'none' : 'var(--border)',
        gap: 'var(--space-4)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', flex: 1, minWidth: 0 }}>
          <span style={{ color: changeColor, fontSize: '10px', fontWeight: 'bold', flexShrink: 0 }}>
            {(file.changeType || file.change_type || 'modified').toUpperCase()}
          </span>
          <span style={{
            color: 'var(--color-text-primary)',
            fontWeight: '500',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>
            {file.filename || file.name}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)', flexShrink: 0 }}>
          <span style={{ color: 'var(--color-success-text)', fontSize: 'var(--font-size-xs)' }}>
            +{file.linesAdded ?? file.lines_added ?? 0}
          </span>
          <span style={{ color: 'var(--color-error-text)', fontSize: 'var(--font-size-xs)' }}>
            -{file.linesDeleted ?? file.lines_deleted ?? 0}
          </span>
          <button
            onClick={() => setCollapsed(!collapsed)}
            style={{
              background: 'none', border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-sm)', padding: '2px 8px',
              color: 'var(--color-text-muted)', cursor: 'pointer', fontSize: '11px',
              fontFamily: 'var(--font-sans)',
            }}
          >
            {collapsed ? 'Expand' : 'Collapse'}
          </button>
        </div>
      </div>

      {/* Diff hunks */}
      {!collapsed && (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', tableLayout: 'fixed', borderCollapse: 'collapse' }}>
            <colgroup>
              <col style={{ width: '50px' }} />
              <col style={{ width: '50px' }} />
              <col />
            </colgroup>
            <tbody>
              {(file.hunks || []).map((hunk, hi) => (
                <React.Fragment key={hi}>
                  {/* Hunk header */}
                  <tr style={{ background: 'var(--color-diff-hunk)' }}>
                    <td colSpan={2} style={{ padding: '3px 8px', userSelect: 'none' }} />
                    <td style={{ padding: '3px 8px', color: 'var(--color-diff-hunk-text)', fontSize: 'var(--font-size-xs)' }}>
                      {hunk.header}
                    </td>
                  </tr>
                  {/* Lines */}
                  {(hunk.lines || []).map((line, li) => {
                    const isAdd = line.type === 'add';
                    const isDel = line.type === 'del';
                    const rowBg = isAdd ? 'var(--color-diff-add)' : isDel ? 'var(--color-diff-del)' : 'var(--color-surface)';
                    const cellBg = isAdd ? 'var(--color-diff-add-line)' : isDel ? 'var(--color-diff-del-line)' : 'transparent';
                    const prefix = isAdd ? '+' : isDel ? '-' : ' ';

                    return (
                      <tr key={li} style={{ background: rowBg }}>
                        <td style={{
                          padding: '1px 8px', textAlign: 'right',
                          color: 'var(--color-text-muted)', userSelect: 'none',
                          fontSize: '11px', verticalAlign: 'top',
                          borderRight: '1px solid var(--color-border)',
                        }}>
                          {!isAdd ? (line.lineNo ?? li + 1) : ''}
                        </td>
                        <td style={{
                          padding: '1px 8px', textAlign: 'right',
                          color: 'var(--color-text-muted)', userSelect: 'none',
                          fontSize: '11px', verticalAlign: 'top',
                          borderRight: '1px solid var(--color-border)',
                        }}>
                          {!isDel ? (line.lineNo ?? li + 1) : ''}
                        </td>
                        <td style={{
                          padding: '1px 8px',
                          background: cellBg,
                          color: isAdd
                            ? 'var(--color-text-primary)'
                            : isDel ? 'var(--color-text-secondary)' : 'var(--color-text-primary)',
                          whiteSpace: 'pre-wrap',
                          wordBreak: 'break-all',
                        }}>
                          <span style={{
                            userSelect: 'none', marginRight: '8px',
                            color: isAdd ? 'var(--color-success)' : isDel ? 'var(--color-error)' : 'transparent',
                          }}>
                            {prefix}
                          </span>
                          {line.content}
                        </td>
                      </tr>
                    );
                  })}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
