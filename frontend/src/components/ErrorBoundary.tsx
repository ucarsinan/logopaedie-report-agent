"use client";

import React from "react";

interface Props {
  children: React.ReactNode;
  fallbackTitle?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="rounded-lg border border-error-border bg-error-surface px-6 py-8 text-center">
          <h2 className="text-lg font-semibold text-error-text mb-2">
            {this.props.fallbackTitle ?? "Ein Fehler ist aufgetreten"}
          </h2>
          <p className="text-sm text-muted-foreground mb-4">
            {this.state.error?.message ?? "Unbekannter Fehler"}
          </p>
          <button
            onClick={this.handleRetry}
            className="px-4 py-2 rounded-lg bg-accent hover:bg-accent-hover text-white text-sm font-medium transition-colors"
          >
            Erneut versuchen
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
