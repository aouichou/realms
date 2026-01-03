"use client";

import { Component, ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("ErrorBoundary caught an error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4">
          <div className="max-w-md text-center space-y-4">
            <div className="text-6xl mb-4">⚠️</div>
            <h1 className="text-3xl font-display text-primary-900">
              Something Went Wrong
            </h1>
            <p className="text-narrative font-body text-neutral-500">
              The mystical forces have been disrupted. Please refresh the page to continue your adventure.
            </p>
            <div className="mt-6 space-y-3">
              <button
                onClick={() => window.location.reload()}
                className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-primary-900 px-6 py-3 text-base font-body font-semibold text-white transition-all hover:bg-accent-600 hover:scale-105 shadow-lg"
              >
                Refresh Page
              </button>
              <button
                onClick={() => (window.location.href = "/")}
                className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-secondary-600 px-6 py-3 text-base font-body font-semibold text-white transition-all hover:bg-accent-400 hover:text-primary-900"
              >
                Return Home
              </button>
            </div>
            {this.state.error && process.env.NODE_ENV === "development" && (
              <details className="mt-6 text-left text-sm text-neutral-500 bg-neutral-100 p-4 rounded-lg">
                <summary className="cursor-pointer font-semibold">
                  Error Details (Development)
                </summary>
                <pre className="mt-2 overflow-auto text-xs">
                  {this.state.error.toString()}
                </pre>
              </details>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
