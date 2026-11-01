/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { Badge } from '../components/Badge';
import { NavBar } from '../components/NavBar';
import { Tabs } from '../components/Tabs';
import { Clock, Trash2, AlertCircle, RefreshCw, Download, Copy, Search } from 'lucide-react';
import type { Review, Finding } from '../api/types';

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';

export default function ReviewResult() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('findings');
  const [searchTerm, setSearchTerm] = useState('');
  const [severityFilter, setSeverityFilter] = useState('');

  const { data: review, isLoading, error } = useQuery({
    queryKey: ['review', id],
    queryFn: () => api.getReview(id!),
    refetchInterval: (data) => {
      if (!data) return false;
      if (data.status === 'queued' || data.status === 'running') return 2000;
      return false;
    },
  } as any);

  const deleteReview = async () => {
    if (confirm('Delete this review?')) {
      await api.deleteReview(id!);
      navigate('/app/history');
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const exportMarkdown = () => {
    if (!review) return;
    const reviewData = review as Review;
    const md = reviewData.report_md || '# Review Report\n\nNo report available.';
    const blob = new Blob([md], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `review-${id}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (isLoading) return <div className="p-8 text-secondary">Loading...</div>;
  if (error) return <div className="p-8 text-critical">Error loading review</div>;
  if (!review) return <div className="p-8 text-secondary">Review not found</div>;

  const reviewData = review as Review;
  const isRunning = reviewData.status === 'queued' || reviewData.status === 'running';

  const filteredFindings = reviewData.findings
    .filter((f: Finding) => f.status === 'kept')
    .filter((f: Finding) => {
      if (severityFilter && f.severity !== severityFilter) return false;
      if (searchTerm && !f.title.toLowerCase().includes(searchTerm.toLowerCase())) return false;
      return true;
    });

  return (
    <div>
      <NavBar />
      <div className="p-8">
        <div className="flex justify-between items-start mb-8">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-2xl font-bold uppercase tracking-wider text-secondary">
                Review {id!.slice(0, 8)}
              </h1>
              {USE_MOCK && (
                <Badge variant="brand">Demo data</Badge>
              )}
            </div>
            <div className="flex items-center gap-4">
              <Badge variant={reviewData.verdict === 'APPROVE' ? 'safe' : 'critical'}>
                {reviewData.verdict || 'Pending'}
              </Badge>
              {isRunning && (
                <span className="flex items-center gap-2 text-brand">
                  <span className="w-2 h-2 bg-brand rounded-full animate-pulse" />
                  Running
                </span>
              )}
              {reviewData.duration_s && (
                <span className="text-secondary flex items-center gap-1">
                  <Clock size={16} />
                  {reviewData.duration_s}s
                </span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            {reviewData.status === 'failed' && (
              <button
                onClick={() => navigate(0)}
                className="flex items-center gap-2 text-brand hover:text-brand/80 transition-colors"
              >
                <RefreshCw size={20} />
                Retry
              </button>
            )}
            {reviewData.status === 'done' && (
              <button
                onClick={exportMarkdown}
                className="flex items-center gap-2 text-brand hover:text-brand/80 transition-colors"
              >
                <Download size={20} />
                Export
              </button>
            )}
            <button
              onClick={deleteReview}
              className="text-secondary hover:text-critical transition-colors"
            >
              <Trash2 size={20} />
            </button>
          </div>
        </div>

      {reviewData.status === 'failed' && (
        <div className="bg-critical/10 border border-critical/30 rounded-lg p-4 mb-6 text-critical">
          <div className="flex items-center gap-2 mb-2">
            <AlertCircle size={20} />
            <span className="font-semibold">Review Failed</span>
          </div>
          <p>{reviewData.error}</p>
        </div>
      )}

      {isRunning && (
        <div className="bg-panel border border-border rounded-lg p-6 mb-6">
          <h2 className="text-lg font-bold mb-4 uppercase tracking-wider text-secondary">
            Agent Pipeline
          </h2>
          <div className="space-y-2">
            {reviewData.agents.map((agent: any) => (
              <div key={agent.agent} className="flex items-center justify-between">
                <span className="text-sm">{agent.agent}</span>
                <div className="flex items-center gap-4">
                  <Badge
                    variant={
                      agent.status === 'done'
                        ? 'safe'
                        : agent.status === 'running'
                        ? 'brand'
                        : 'secondary'
                    }
                  >
                    {agent.status}
                  </Badge>
                  <span className="text-secondary text-sm">{agent.duration_s}s</span>
                  <span className="text-secondary text-sm">{agent.finding_count} findings</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {reviewData.status === 'done' && (
        <>
          <Tabs
            tabs={[
              { id: 'findings', label: `Findings (${filteredFindings.length})` },
              { id: 'rejected', label: `Rejected (${reviewData.findings.filter((f: Finding) => f.status === 'rejected').length})` },
              { id: 'diff', label: 'Diff' },
              { id: 'report', label: 'Report' },
            ]}
            activeTab={activeTab}
            onTabChange={setActiveTab}
          />

          {activeTab === 'findings' && (
            <div className="mt-6">
              <div className="flex items-center gap-4 mb-4">
                <div className="flex-1 relative">
                  <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-secondary" />
                  <input
                    type="text"
                    placeholder="Search findings..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full bg-page border border-border rounded-lg pl-10 pr-4 py-2 text-sm text-text placeholder-secondary focus:outline-none focus:border-brand"
                  />
                </div>
                <select
                  value={severityFilter}
                  onChange={(e) => setSeverityFilter(e.target.value)}
                  className="bg-page border border-border rounded-lg px-4 py-2 text-sm text-text focus:outline-none focus:border-brand"
                >
                  <option value="">All Severities</option>
                  <option value="CRITICAL">Critical</option>
                  <option value="HIGH">High</option>
                  <option value="MEDIUM">Medium</option>
                  <option value="LOW">Low</option>
                </select>
              </div>

              {filteredFindings.length === 0 ? (
                <div className="bg-panel border border-border rounded-lg p-8 text-center text-secondary">
                  No findings match your filters.
                </div>
              ) : (
                <div className="space-y-4">
                  {filteredFindings.map((finding: Finding) => (
                    <div key={finding.id} className="bg-panel border border-border rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <Badge variant={finding.severity.toLowerCase() as any}>{finding.severity}</Badge>
                          <Badge variant="secondary" confidence={finding.confidence.toLowerCase() as any}>
                            {finding.confidence}
                          </Badge>
                          <Badge variant="brand">{finding.cwe}</Badge>
                        </div>
                        <button
                          onClick={() => copyToClipboard(finding.fix)}
                          className="text-secondary hover:text-brand transition-colors"
                          title="Copy fix"
                        >
                          <Copy size={16} />
                        </button>
                      </div>
                      <p className="font-medium mb-2">{finding.title}</p>
                      <div className="font-mono text-sm text-secondary mb-2">
                        {finding.file}:{finding.line}
                      </div>
                      <div className="bg-page border border-border rounded p-3 mb-2">
                        <pre className="text-sm overflow-x-auto">{finding.evidence}</pre>
                      </div>
                      <div className="bg-page border border-border rounded p-3">
                        <p className="text-sm text-secondary mb-1">Suggested Fix:</p>
                        <pre className="text-sm overflow-x-auto">{finding.fix}</pre>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-secondary mt-2">
                        {finding.sources.map((s) => (
                          <Badge key={s} variant="secondary">{s}</Badge>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === 'rejected' && (
            <div className="mt-6">
              <div className="space-y-4">
                {reviewData.findings.filter((f: Finding) => f.status === 'rejected').map((finding: Finding) => (
                  <div key={finding.id} className="bg-panel border border-border rounded-lg p-4 opacity-60">
                    <div className="flex items-center gap-2 mb-2">
                      <Badge variant="secondary">{finding.severity}</Badge>
                      <Badge variant="brand">{finding.cwe}</Badge>
                    </div>
                    <p className="font-medium mb-2">{finding.title}</p>
                    <p className="text-sm text-secondary">Reason: {finding.rejection_reason}</p>
                  </div>
                ))}
                {reviewData.findings.filter((f: Finding) => f.status === 'rejected').length === 0 && (
                  <div className="bg-panel border border-border rounded-lg p-8 text-center text-secondary">
                    No rejected findings.
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === 'diff' && (
            <div className="mt-6">
              <div className="bg-panel border border-border rounded-lg p-4">
                <pre className="text-sm overflow-x-auto whitespace-pre-wrap">{reviewData.diff_text}</pre>
              </div>
            </div>
          )}

          {activeTab === 'report' && (
            <div className="mt-6">
              <div className="bg-panel border border-border rounded-lg p-4">
                <pre className="text-sm overflow-x-auto whitespace-pre-wrap">{reviewData.report_md || 'No report available.'}</pre>
              </div>
            </div>
          )}
        </>
      )}
      </div>
    </div>
  );
}
