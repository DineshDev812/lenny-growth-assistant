import { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error in React render tree:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center min-h-screen bg-[#FBF9F5] dark:bg-stone-950 text-stone-900 dark:text-stone-100 p-6 text-center">
          <div className="max-w-md w-full bg-white dark:bg-stone-900 border border-stone-200 dark:border-stone-800 rounded-2xl p-6 shadow-md">
            <h2 className="text-lg font-bold mb-2">Something went wrong</h2>
            <p className="text-sm text-stone-600 dark:text-stone-400 mb-4">
              An unexpected display error occurred. Click reload to restore your session.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white font-medium rounded-lg text-sm transition-colors cursor-pointer"
            >
              Reload Page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
