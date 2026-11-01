import { Component, ReactNode } from 'react';
import { AlertCircle, Home } from 'lucide-react';
import { Link } from 'react-router-dom';

interface Props {
  children: ReactNode;
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
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-page flex items-center justify-center p-4">
          <div className="bg-panel border border-border rounded-lg p-8 max-w-md w-full text-center">
            <AlertCircle className="w-16 h-16 text-critical mx-auto mb-4" />
            <h1 className="text-2xl font-bold mb-4 text-text">Something went wrong</h1>
            <p className="text-secondary mb-6">
              {this.state.error?.message || 'An unexpected error occurred'}
            </p>
            <Link
              to="/"
              className="inline-flex items-center gap-2 bg-brand hover:bg-brand/90 text-white px-6 py-3 rounded-lg font-medium transition-colors"
            >
              <Home size={20} />
              Go to Home
            </Link>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
