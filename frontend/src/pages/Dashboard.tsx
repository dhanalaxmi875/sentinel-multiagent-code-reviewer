import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import { Shield, Clock, AlertTriangle, CheckCircle } from 'lucide-react';
import { Link } from 'react-router-dom';
import { NavBar } from '../components/NavBar';
import { Badge } from '../components/Badge';

export default function Dashboard() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['stats'],
    queryFn: () => api.getStats(),
  });

  const { data: reviews } = useQuery({
    queryKey: ['reviews'],
    queryFn: () => api.getReviews(),
  });

  if (isLoading) {
    return (
      <div>
        <NavBar />
        <div className="p-8 text-secondary">Loading...</div>
      </div>
    );
  }

  return (
    <div>
      <NavBar />
      <div className="p-8">
        <h1 className="text-2xl font-bold mb-8 uppercase tracking-wider text-secondary">
          Dashboard
        </h1>

        {/* KPI Cards */}
        <div className="grid md:grid-cols-4 gap-6 mb-8">
        <div className="bg-panel border border-border rounded-lg p-6">
          <div className="flex items-center gap-3 mb-2">
            <Shield className="w-5 h-5 text-brand" />
            <span className="text-secondary text-sm uppercase tracking-wider">Reviews Run</span>
          </div>
          <div className="text-3xl font-bold">{stats?.total_reviews ?? 0}</div>
        </div>

        <div className="bg-panel border border-border rounded-lg p-6">
          <div className="flex items-center gap-3 mb-2">
            <AlertTriangle className="w-5 h-5 text-critical" />
            <span className="text-secondary text-sm uppercase tracking-wider">Critical</span>
          </div>
          <div className="text-3xl font-bold text-critical">{stats?.finding_counts.critical ?? 0}</div>
        </div>

        <div className="bg-panel border border-border rounded-lg p-6">
          <div className="flex items-center gap-3 mb-2">
            <CheckCircle className="w-5 h-5 text-safe" />
            <span className="text-secondary text-sm uppercase tracking-wider">Approve</span>
          </div>
          <div className="text-3xl font-bold text-safe">{stats?.verdict_split.approve ?? 0}</div>
        </div>

        <div className="bg-panel border border-border rounded-lg p-6">
          <div className="flex items-center gap-3 mb-2">
            <Clock className="w-5 h-5 text-brand" />
            <span className="text-secondary text-sm uppercase tracking-wider">Avg Time</span>
          </div>
          <div className="text-3xl font-bold">{stats?.avg_review_time_s ?? 0}s</div>
        </div>
      </div>

      {/* Recent Reviews */}
      <div className="bg-panel border border-border rounded-lg p-6">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-lg font-bold uppercase tracking-wider text-secondary">
            Recent Reviews
          </h2>
          <Link to="/app/history" className="text-brand hover:underline text-sm">
            View All
          </Link>
        </div>
        {reviews && reviews.length > 0 ? (
          <div className="space-y-3">
            {reviews.slice(0, 5).map((review) => (
              <Link
                key={review.id}
                to={`/app/reviews/${review.id}`}
                className="block bg-page border border-border rounded-lg p-4 hover:border-brand transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Badge
                      variant={
                        review.status === 'done'
                          ? 'safe'
                          : review.status === 'failed'
                          ? 'critical'
                          : 'brand'
                      }
                    >
                      {review.status}
                    </Badge>
                    {review.verdict && (
                      <Badge variant={review.verdict === 'APPROVE' ? 'safe' : 'critical'}>
                        {review.verdict}
                      </Badge>
                    )}
                  </div>
                  <span className="text-secondary text-sm">
                    {new Date(review.created_at).toLocaleDateString()}
                  </span>
                </div>
                <div className="mt-2 text-sm text-secondary">
                  C:{review.finding_counts.critical} H:{review.finding_counts.high} M:{review.finding_counts.medium} L:{review.finding_counts.low}
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <p className="text-secondary text-sm">No reviews yet. Create your first review.</p>
        )}
      </div>
      </div>
    </div>
  );
}
