import React from 'react';

const variants = {
  primary:   { bg: '#FFFFFF', color: '#0D0D0D', border: 'none', hoverBg: '#E0E0E0' },
  secondary: { bg: '#1A1A1A', color: '#F5F5F5', border: '1px solid #2E2E2E', hoverBg: '#222222' },
  ghost:     { bg: 'transparent', color: '#9E9E9E', border: '1px solid #2E2E2E', hoverBg: '#1A1A1A' },
  danger:    { bg: 'transparent', color: '#C97272', border: '1px solid #8B2C2C', hoverBg: '#2E1515' },
};

const sizes = {
  sm: { padding: '4px 10px', fontSize: '12px', height: '28px' },
  md: { padding: '7px 14px', fontSize: '14px', height: '34px' },
  lg: { padding: '10px 20px', fontSize: '14px', height: '40px' },
};

export default function Button({
  children,
  variant = 'primary',
  size = 'md',
  fullWidth = false,
  disabled = false,
  loading = false,
  onClick,
  type = 'button',
  style = {},
  ...props
}) {
  const v = variants[variant] || variants.primary;
  const s = sizes[size] || sizes.md;

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled || loading}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '6px',
        width: fullWidth ? '100%' : undefined,
        padding: s.padding,
        height: s.height,
        fontSize: s.fontSize,
        fontFamily: 'var(--font-sans)',
        fontWeight: '500',
        lineHeight: 1,
        borderRadius: 'var(--radius-md)',
        border: v.border,
        background: v.bg,
        color: v.color,
        cursor: disabled || loading ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1,
        transition: 'background var(--transition-fast), opacity var(--transition-fast)',
        whiteSpace: 'nowrap',
        userSelect: 'none',
        ...style,
      }}
      onMouseEnter={(e) => {
        if (!disabled && !loading) e.currentTarget.style.background = v.hoverBg;
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = v.bg;
      }}
      {...props}
    >
      {loading ? (
        <>
          <span style={{
            display: 'inline-block', width: '12px', height: '12px',
            border: '2px solid currentColor', borderTopColor: 'transparent',
            borderRadius: '50%', animation: 'spin 0.6s linear infinite',
          }} />
          {children}
        </>
      ) : children}
    </button>
  );
}
