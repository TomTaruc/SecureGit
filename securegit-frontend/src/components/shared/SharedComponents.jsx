import React from 'react';

export function Avatar({ username = '', size = 32 }) {
  const initials = username.slice(0, 2).toUpperCase();
  // Deterministic gray shade from username
  const shade = (username.charCodeAt(0) || 65) % 3;
  const bgs = ['#2A2A2A', '#222222', '#1E1E1E'];

  return (
    <div style={{
      width: `${size}px`, height: `${size}px`,
      borderRadius: '50%',
      background: bgs[shade],
      border: '1px solid var(--color-border)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: `${Math.round(size * 0.38)}px`,
      fontFamily: 'var(--font-mono)',
      fontWeight: '600',
      color: 'var(--color-text-secondary)',
      flexShrink: 0,
      userSelect: 'none',
    }}>
      {initials}
    </div>
  );
}

export function CopyButton({ text, label = 'Copy' }) {
  const [copied, setCopied] = React.useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* fallback: select text */
    }
  };

  return (
    <button
      onClick={handleCopy}
      title="Copy to clipboard"
      style={{
        display: 'inline-flex', alignItems: 'center', gap: '4px',
        padding: '3px 10px',
        fontSize: 'var(--font-size-xs)',
        fontFamily: 'var(--font-sans)',
        fontWeight: '500',
        border: 'var(--border)',
        borderRadius: 'var(--radius-sm)',
        background: copied ? 'var(--color-success-bg)' : 'var(--color-surface-2)',
        color: copied ? 'var(--color-success-text)' : 'var(--color-text-muted)',
        cursor: 'pointer',
        transition: 'all var(--transition-fast)',
        whiteSpace: 'nowrap',
      }}
    >
      {copied ? '✓ Copied' : label}
    </button>
  );
}

export function TimeAgo({ dateString }) {
  if (!dateString) return null;
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now - date;
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHr  = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHr  / 24);

  let text;
  if (diffSec < 60)       text = 'just now';
  else if (diffMin < 60)  text = `${diffMin}m ago`;
  else if (diffHr  < 24)  text = `${diffHr}h ago`;
  else if (diffDay < 30)  text = `${diffDay}d ago`;
  else                    text = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

  return (
    <time dateTime={dateString} title={date.toLocaleString()} style={{ color: 'var(--color-text-muted)' }}>
      {text}
    </time>
  );
}
