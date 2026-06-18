import React from 'react';
import Button from './Button';

export default function Pagination({ page, totalPages, onPage }) {
  if (totalPages <= 1) return null;

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 'var(--space-3)',
      justifyContent: 'center', padding: 'var(--space-4) 0',
    }}>
      <Button
        variant="ghost" size="sm"
        disabled={page <= 1}
        onClick={() => onPage(page - 1)}
      >
        ← Newer
      </Button>
      <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)' }}>
        Page {page} of {totalPages}
      </span>
      <Button
        variant="ghost" size="sm"
        disabled={page >= totalPages}
        onClick={() => onPage(page + 1)}
      >
        Older →
      </Button>
    </div>
  );
}
