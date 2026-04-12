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

  handleGoHome = () => {
    if (typeof window !== "undefined") {
      window.location.href = "/";
    }
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="rounded-lg border border-error-border bg-error-surface px-6 py-8 text-center">
          <h2 className="text-lg font-semibold text-error-text mb-2">
            {this.props.fallbackTitle ?? "Ein Fehler ist aufgetreten"}
          </h2>
          <p className="text-sm text-muted-foreground mb-2">
            Bitte versuchen Sie es erneut. Besteht das Problem weiterhin, laden Sie die
            Startseite neu.
          </p>
          {this.state.error?.message && (
            <details className="mb-4 mx-auto max-w-md text-left">
              <summary className="cursor-pointer text-xs text-muted-foreground hover:text-foreground">
                Technische Details
              </summary>
              <pre className="mt-2 overflow-auto rounded bg-background/50 p-2 text-xs text-muted-foreground whitespace-pre-wrap">
                {this.state.error.message}
              </pre>
            </details>
          )}
          <div className="flex items-center justify-center gap-2">
            <button
              onClick={this.handleRetry}
              className="px-4 py-2 rounded-lg bg-accent hover:bg-accent-hover text-white text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-background"
            >
              Erneut versuchen
            </button>
            <button
              onClick={this.handleGoHome}
              className="px-4 py-2 rounded-lg border border-border text-foreground hover:bg-surface text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-background"
            >
              Zur Startseite
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
