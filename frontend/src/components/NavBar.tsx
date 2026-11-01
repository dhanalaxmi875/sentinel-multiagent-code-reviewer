import { Link, useLocation } from 'react-router-dom';
import { Clock, FileText, Shield } from 'lucide-react';

export function NavBar() {
  const location = useLocation();
  const isActive = (path: string) => location.pathname === path;

  return (
    <nav className="bg-panel border-b border-border">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex flex-wrap items-center justify-between min-h-16 py-2 gap-2">
          <div className="flex items-center gap-8">
            <Link to="/app" className="text-brand font-bold text-lg">
              SentinelCode
            </Link>
            <div className="flex items-center gap-1">
              <Link
                to="/app"
                className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive('/app')
                    ? 'bg-brand/10 text-brand'
                    : 'text-secondary hover:text-text'
                }`}
              >
                <Shield size={16} />
                Dashboard
              </Link>
              <Link
                to="/app/new"
                className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive('/app/new')
                    ? 'bg-brand/10 text-brand'
                    : 'text-secondary hover:text-text'
                }`}
              >
                <FileText size={16} />
                New Review
              </Link>
              <Link
                to="/app/history"
                className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive('/app/history')
                    ? 'bg-brand/10 text-brand'
                    : 'text-secondary hover:text-text'
                }`}
              >
                <Clock size={16} />
                History
              </Link>
            </div>
          </div>
          <Link
            to="/"
            className="text-secondary hover:text-text text-sm transition-colors"
          >
            ← Back to Home
          </Link>
        </div>
      </div>
    </nav>
  );
}
