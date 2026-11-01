import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { Badge } from '../components/Badge';
import { Trash2, Clock } from 'lucide-react';
import { NavBar } from '../components/NavBar';
import { Skeleton } from '../components/Skeleton';

export default function History() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: reviews, isLoading } = useQuery({
    queryKey: ['reviews'],
    queryFn: () => api.getReviews(),
  });

  const deleteReview = useMutation({
    mutationFn: (id: string) => api.deleteReview(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['reviews'] }),
  });

  if (isLoading) return <div className="min-h-screen bg-page"><NavBar/><main className="p-8 space-y-4"><Skeleton variant="title"/><Skeleton variant="card"/></main></div>;

  return (
    <div>
      <NavBar />
      <main className="p-8 max-w-7xl mx-auto">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-8"><h1 className="text-2xl font-bold uppercase tracking-wider text-secondary">
          History
        </h1>{import.meta.env.VITE_USE_MOCK === 'true' && <Badge variant="brand">Demo data</Badge>}</div>

      {reviews && reviews.length > 0 ? (
        <div className="bg-panel border border-border rounded-lg overflow-x-auto">
          <table className="w-full min-w-[760px]">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left p-4 text-secondary uppercase tracking-wider text-sm">Status</th>
                <th className="text-left p-4 text-secondary uppercase tracking-wider text-sm">Verdict</th>
                <th className="text-left p-4 text-secondary uppercase tracking-wider text-sm">Findings</th>
                <th className="text-left p-4 text-secondary uppercase tracking-wider text-sm">Time</th>
                <th className="text-left p-4 text-secondary uppercase tracking-wider text-sm">Date</th>
                <th className="text-right p-4 text-secondary uppercase tracking-wider text-sm">Actions</th>
              </tr>
            </thead>
            <tbody>
              {reviews.map((review) => (
                <tr key={review.id} className="border-b border-border hover:bg-page/50 transition-colors">
                  <td className="p-4">
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
                  </td>
                  <td className="p-4">
                    {review.verdict && (
                      <Badge variant={review.verdict === 'APPROVE' ? 'safe' : 'critical'}>
                        {review.verdict}
                      </Badge>
                    )}
                  </td>
                  <td className="p-4 text-sm">
                    C:{review.finding_counts.critical} H:{review.finding_counts.high} M:{review.finding_counts.medium} L:{review.finding_counts.low}
                  </td>
                  <td className="p-4 text-sm text-secondary flex items-center gap-1">
                    <Clock size={14} />
                    {review.duration_s}s
                  </td>
                  <td className="p-4 text-sm text-secondary">
                    {new Date(review.created_at).toLocaleString()}
                  </td>
                  <td className="p-4 text-right">
                    <button
                      onClick={() => navigate(`/app/reviews/${review.id}`)}
                      className="text-brand hover:underline mr-4"
                    >
                      View
                    </button>
                    <button
                      onClick={() => { if (window.confirm('Delete this review?')) deleteReview.mutate(review.id); }}
                      className="text-secondary hover:text-critical"
                    >
                      <Trash2 size={16} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="bg-panel border border-border rounded-lg p-8 text-center text-secondary">
          No reviews yet. Create your first review.
        </div>
      )}
      </main>
    </div>
  );
}
