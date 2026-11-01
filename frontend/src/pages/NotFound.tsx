import { Link } from 'react-router-dom';
import { Home } from 'lucide-react';

export default function NotFound() {
  return (
    <div className="p-8 text-center">
      <h1 className="text-4xl font-bold mb-4 text-secondary">404</h1>
      <p className="text-secondary mb-8">Page not found</p>
      <Link
        to="/"
        className="bg-brand hover:bg-brand/90 text-white px-6 py-3 rounded-lg font-medium transition-colors inline-flex items-center gap-2"
      >
        <Home size={20} />
        Back to Home
      </Link>
    </div>
  );
}
