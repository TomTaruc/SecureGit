import React from 'react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ error, errorInfo });
    console.error("ErrorBoundary caught an error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 'var(--space-8)', background: 'var(--color-surface)', border: '1px solid var(--color-error)', borderRadius: 'var(--radius-md)' }}>
          <h2 style={{ color: 'var(--color-error-text)', marginBottom: 'var(--space-4)' }}>Something went wrong.</h2>
          <p style={{ marginBottom: 'var(--space-4)' }}>An unexpected error occurred while rendering this component.</p>
          <details style={{ whiteSpace: 'pre-wrap', color: 'var(--color-text-muted)', fontSize: 'var(--font-size-xs)', overflowX: 'auto', background: 'var(--color-surface-2)', padding: 'var(--space-3)' }}>
            {this.state.error && this.state.error.toString()}
            <br />
            {this.state.errorInfo && this.state.errorInfo.componentStack}
          </details>
        </div>
      );
    }
    return this.props.children;
  }
}
