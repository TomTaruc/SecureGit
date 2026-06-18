import React from 'react';
import Button from './Button';

/* Empty state for lists/sections */
export default function EmptyState({ icon = '📂', title, description, action, actionLabel }) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      padding: 'var(--space-16) var(--space-8)',
      textAlign: 'center',
      gap: 'var(--space-4)',
    }}>
      <span style={{ fontSize: '40px', opacity: 0.4 }}>{icon}</span>
      <div>
        <p style={{
          fontSize: 'var(--font-size-md)',
          fontWeight: '500',
          color: 'var(--color-text-secondary)',
          marginBottom: 'var(--space-2)',
        }}>
          {title}
        </p>
        {description && (
          <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)' }}>
            {description}
          </p>
        )}
      </div>
      {action && (
        <Button variant="secondary" size="md" onClick={action}>
          {actionLabel}
        </Button>
      )}
    </div>
  );
}
