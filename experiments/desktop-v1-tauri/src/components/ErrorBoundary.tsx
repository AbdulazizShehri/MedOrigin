import { Component, type ReactNode } from 'react';

interface BoundaryState {
  failed: boolean;
}

export class ErrorBoundary extends Component<{ children: ReactNode }, BoundaryState> {
  state: BoundaryState = { failed: false };

  static getDerivedStateFromError(): BoundaryState {
    return { failed: true };
  }

  render() {
    if (this.state.failed) {
      return (
        <main className="work" role="alert">
          <div className="error-box">
            <strong>Render failure</strong>
            <p>
              Something failed to render. No data was changed, no capability was enabled, and nothing was sent anywhere.
              Restart the preview; if the failure persists, record the exact steps and report it through the normal
              engineering channel.
            </p>
          </div>
        </main>
      );
    }
    return this.props.children;
  }
}
