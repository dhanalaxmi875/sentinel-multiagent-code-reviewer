import { Component, ReactNode } from "react";
import { AlertCircle, Home } from "lucide-react";
import { Link } from "react-router-dom";

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
    console.error("ErrorBoundary caught an error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="grid min-h-screen place-items-center p-4">
          <div className="glass-panel w-full max-w-md rounded-[28px] p-8 text-center">
            <AlertCircle className="mx-auto mb-4 h-14 w-14 text-critical" />
            <h1 className="text-2xl font-bold mb-4 text-text">
              Something went wrong
            </h1>
            <p className="text-secondary mb-6">
              {this.state.error?.message || "An unexpected error occurred"}
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
