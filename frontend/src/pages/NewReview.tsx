import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { FileText, Upload } from 'lucide-react';
import { NavBar } from '../components/NavBar';
import { validateDiff, MAX_DIFF_CHARS } from '../utils/diffValidation';
import { Badge } from '../components/Badge';
import { Toast } from '../components/Toast';

export default function NewReview() {
  const navigate = useNavigate();
  const [diff, setDiff] = useState('');
  const [filePaths, setFilePaths] = useState('');
  const [error, setError] = useState('');
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  const { data: samples } = useQuery({
    queryKey: ['samples'],
    queryFn: () => api.getSamples(),
  });

  const createReview = useMutation({
    mutationFn: (req: { diff_text: string; file_paths?: string[] }) => api.createReview(req),
    onSuccess: (data) => {
      navigate(`/app/reviews/${data.id}`);
    },
    onError: (submissionError) => setToast({ message: submissionError.message, type: 'error' }),
  });

  const handleSubmit = () => {
    setError('');
    const validationError = validateDiff(diff);
    if (validationError) {
      setError(validationError);
      return;
    }
    createReview.mutate({
      diff_text: diff,
      file_paths: filePaths ? filePaths.split(',').map(p => p.trim()) : undefined,
    });
  };

  return (
    <div>
      <NavBar />
      <div className="p-8 max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold mb-8 uppercase tracking-wider text-secondary">
          New Review
        </h1>

      <div className="bg-panel border border-border rounded-lg p-6 mb-6">
        <div className="flex justify-between items-center mb-4">
          <p className="text-secondary text-sm">
            Your diff is sent to the configured review server for analysis and stored with your review until you delete it.
          </p>
          <label className="flex items-center gap-2 text-brand hover:text-brand/80 cursor-pointer text-sm">
            <Upload size={16} />
            <span>Upload .diff file</span>
            <input
              type="file"
              accept=".diff,.patch,.txt"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) {
                  const reader = new FileReader();
                  reader.onload = (event) => {
                    setDiff(event.target?.result as string);
                  };
                  reader.readAsText(file);
                }
              }}
            />
          </label>
        </div>
        <textarea
          aria-label="Unified diff"
          maxLength={MAX_DIFF_CHARS}
          value={diff}
          onChange={(e) => setDiff(e.target.value)}
          placeholder="Paste your unified diff here..."
          className="w-full h-64 bg-page border border-border rounded-lg p-4 font-mono text-sm text-text placeholder-secondary focus:outline-none focus:border-brand"
        />
        <div className="flex justify-between mt-2 text-sm text-secondary">
          <span aria-live="polite">{diff.length.toLocaleString()} / {MAX_DIFF_CHARS.toLocaleString()} characters</span>
          {error && <span className="text-critical">{error}</span>}
        </div>
      </div>

      <div className="bg-panel border border-border rounded-lg p-6 mb-6">
        <label className="block text-sm text-secondary mb-2">File Paths (optional, comma-separated)</label>
        <input
          type="text"
          value={filePaths}
          onChange={(e) => setFilePaths(e.target.value)}
          placeholder="src/api.py, src/db.py"
          className="w-full bg-page border border-border rounded-lg p-3 font-mono text-sm text-text placeholder-secondary focus:outline-none focus:border-brand"
        />
      </div>

      <div className="bg-panel border border-border rounded-lg p-6 mb-6">
        <div className="flex items-center gap-2 mb-4">
          <FileText className="w-5 h-5 text-brand" />
          <span className="font-semibold">Built-in Samples</span>
        </div>
        {samples?.map((sample) => (
          <button
            key={sample.id}
            onClick={() => { setDiff(sample.diff_text); setToast({ message: `${sample.name} loaded`, type: 'success' }); }}
            className="block w-full text-left p-3 bg-page border border-border rounded hover:border-brand transition-colors mb-2"
          >
            <div className="font-medium">{sample.name}</div>
            <div className="text-sm text-secondary">{sample.description}</div>
          </button>
        ))}
        {samples?.length === 0 && <p className="text-sm text-secondary">No sample diffs are available.</p>}
        {import.meta.env.VITE_USE_MOCK === 'true' && <div className="mt-3"><Badge variant="brand">Demo data</Badge></div>}
      </div>

      <button
        onClick={handleSubmit}
        disabled={createReview.isPending}
        className="bg-brand hover:bg-brand/90 text-white px-6 py-3 rounded-lg font-medium transition-colors disabled:opacity-50"
      >
        {createReview.isPending ? 'Creating...' : 'Submit Review'}
      </button>
      {createReview.isError && <p role="alert" className="mt-3 text-critical">{createReview.error.message}</p>}
      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
      </div>
    </div>
  );
}
