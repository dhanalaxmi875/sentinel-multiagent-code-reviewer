import { useQuery, useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { Badge } from '../components/Badge';
import { Trash2, Clock } from 'lucide-react';
import { NavBar } from '../components/NavBar';

export default function History() {
  const navigate = useNavigate();
  const { data: reviews, isLoading } = useQuery({
    queryKey: ['reviews'],
    queryFn: () => api.getReviews(),
  });

  const deleteReview = useMutation({
    mutationFn: (id: string) => api.deleteReview(id),
    onSuccess: () => {
      // Refetch will happen automatically
    },
  });

  if (isLoading) return <div className="p-8 text-secondary">Loading...</div>;

  return (
    <div>
      <NavBar />
      <div className="p-8">
        <h1 className="text-2xl font-bold mb-8 uppercase tracking-wider text-secondary">
          History
        </h1>

      {reviews && reviews.length > 0 ? (
        <div className="bg-panel border border-border rounded-lg overflow-hidden">
          <table className="w-full">
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
                      onClick={() => deleteReview.mutate(review.id)}
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
      </div>
    </div>
  );
}
