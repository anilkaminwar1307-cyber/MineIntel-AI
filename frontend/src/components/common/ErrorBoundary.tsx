import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw, LayoutDashboard, Bug } from 'lucide-react';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallbackTitle?: string;
  fallbackMessage?: string;
  onReset?: () => void;
  isCompact?: boolean;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('MineIntel ErrorBoundary caught an unhandled display error:', error, errorInfo);
    this.setState({ errorInfo });
  }

  handleRetry = (): void => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  handleReturnToOverview = (): void => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    if (window.location.hash !== '#/overview' && window.location.hash !== '#overview') {
      window.location.hash = '#/overview';
    }
    // Also dispatch popstate so any listeners re-render
    window.dispatchEvent(new Event('popstate'));
  };

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.isCompact) {
        return (
          <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg text-slate-600 text-xs flex items-center justify-between gap-3 my-2">
            <div className="flex items-center space-x-2">
              <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0" />
              <span>{this.props.fallbackMessage || 'Chart unavailable for this result.'}</span>
            </div>
            <button
              type="button"
              onClick={this.handleRetry}
              className="inline-flex items-center space-x-1 px-2.5 py-1 text-[11px] font-semibold text-slate-700 bg-white border border-slate-300 rounded hover:bg-slate-100 transition-colors"
            >
              <RefreshCw className="w-3 h-3" />
              <span>Retry</span>
            </button>
          </div>
        );
      }

      return (
        <div className="min-h-[400px] flex items-center justify-center p-6">
          <div className="max-w-md w-full bg-white rounded-xl border border-slate-200 shadow-md p-6 text-center space-y-4">
            <div className="w-12 h-12 bg-amber-50 border border-amber-200 rounded-full flex items-center justify-center mx-auto text-amber-600">
              <AlertTriangle className="w-6 h-6" />
            </div>

            <div className="space-y-1.5">
              <h3 className="text-base font-bold text-slate-900">
                {this.props.fallbackTitle || 'MineIntel encountered a display error.'}
              </h3>
              <p className="text-xs text-slate-500 leading-relaxed">
                {this.props.fallbackMessage ||
                  'A view component encountered an issue during rendering. Verified facts in the Evidence Ledger remain completely safe.'}
              </p>
            </div>

            {this.state.error && (
              <div className="text-left bg-slate-50 border border-slate-200 rounded p-2.5 max-h-24 overflow-y-auto text-[11px] font-mono text-slate-600">
                <span className="font-bold text-rose-700 block mb-0.5">Details:</span>
                {this.state.error.message || String(this.state.error)}
              </div>
            )}

            <div className="flex items-center justify-center space-x-3 pt-2">
              <button
                type="button"
                onClick={this.handleRetry}
                className="inline-flex items-center space-x-1.5 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold border border-slate-300 transition-colors"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Retry</span>
              </button>

              <button
                type="button"
                onClick={this.handleReturnToOverview}
                className="inline-flex items-center space-x-1.5 px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors"
              >
                <LayoutDashboard className="w-3.5 h-3.5 text-amber-400" />
                <span>Return to Overview</span>
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
