import React, { forwardRef } from 'react';

const Input = forwardRef(function Input({
  label,
  error,
  hint,
  prefix,
  id,
  style = {},
  containerStyle = {},
  type = 'text',
  textarea = false,
  rows = 4,
  ...props
}, ref) {
  const inputStyle = {
    display: 'block',
    width: '100%',
    padding: prefix ? '7px 12px 7px 10px' : '7px 12px',
    fontSize: 'var(--font-size-md)',
    fontFamily: 'var(--font-sans)',
    color: 'var(--color-text-primary)',
    background: 'var(--color-surface-2)',
    border: error ? '1px solid var(--color-error)' : '1px solid var(--color-border)',
    borderRadius: 'var(--radius-md)',
    outline: 'none',
    transition: 'border-color var(--transition-fast)',
    resize: textarea ? 'vertical' : undefined,
    lineHeight: '1.5',
    ...style,
  };

  const InputEl = textarea ? 'textarea' : 'input';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', ...containerStyle }}>
      {label && (
        <label
          htmlFor={id}
          style={{
            fontSize: 'var(--font-size-sm)',
            fontWeight: '500',
            color: 'var(--color-text-secondary)',
          }}
        >
          {label}
        </label>
      )}
      <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
        {prefix && (
          <span style={{
            position: 'absolute', left: '12px',
            color: 'var(--color-text-muted)',
            fontSize: 'var(--font-size-md)',
            pointerEvents: 'none',
          }}>
            {prefix}
          </span>
        )}
        <InputEl
          ref={ref}
          id={id}
          type={textarea ? undefined : type}
          rows={textarea ? rows : undefined}
          style={inputStyle}
          onFocus={(e) => { e.target.style.borderColor = '#555555'; }}
          onBlur={(e) => { e.target.style.borderColor = error ? 'var(--color-error)' : 'var(--color-border)'; }}
          {...props}
        />
      </div>
      {hint && !error && (
        <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>{hint}</span>
      )}
      {error && (
        <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-error-text)' }}>{error}</span>
      )}
    </div>
  );
});

export default Input;
