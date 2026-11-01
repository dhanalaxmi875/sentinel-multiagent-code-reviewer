// API Client with Mock Mode
import type {
  CreateReviewRequest,
  CreateReviewResponse,
  Review,
  ReviewSummary,
  Stats,
  Sample,
} from './types';

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');

// Generate client token on first visit
function getClientToken(): string {
  const existing = localStorage.getItem('client_token');
  if (existing) return existing;
  const token = crypto.randomUUID();
  localStorage.setItem('client_token', token);
  return token;
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    'X-Client-Token': getClientToken(),
    ...options.headers,
  };

  const response = await fetch(url, { ...options, headers });

  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

// Mock Data - clearly marked
const MOCK_REVIEWS: Review[] = [
  {
    id: 'mock-1',
    status: 'done',
    verdict: 'REQUEST_CHANGES',
    duration_s: 45,
    diff_text: `diff --git a/src/api.py b/src/api.py
index 1234567..abcdef 100644
--- a/src/api.py
+++ b/src/api.py
@@ -10,0 +10,5 @@
+def transfer_funds(user_id, amount):
+    cursor.execute("SELECT * FROM users WHERE id = " + user_id)
+    cursor.execute("UPDATE accounts SET balance = balance + " + str(amount))
+    SECRET_KEY = "hardcoded_secret_12345"
+    return subprocess.run(cmd, shell=True)`,
    agents: [
      { agent: 'orchestrator', status: 'done', duration_s: 2, finding_count: 0 },
      { agent: 'bug_detector', status: 'done', duration_s: 8, finding_count: 1 },
      { agent: 'security', status: 'done', duration_s: 12, finding_count: 3 },
      { agent: 'code_quality', status: 'done', duration_s: 6, finding_count: 2 },
      { agent: 'test_coverage', status: 'done', duration_s: 5, finding_count: 1 },
      { agent: 'semgrep', status: 'done', duration_s: 3, finding_count: 2 },
      { agent: 'verifier', status: 'done', duration_s: 7, finding_count: 0 },
      { agent: 'summarizer', status: 'done', duration_s: 2, finding_count: 0 },
    ],
    findings: [
      {
        id: 'f1',
        title: 'SQL injection in transfer_funds',
        severity: 'CRITICAL',
        confidence: 'HIGH',
        cwe: 'CWE-89',
        file: 'src/api.py',
        line: 11,
        evidence: 'cursor.execute("SELECT * FROM users WHERE id = " + user_id)',
        fix: 'Use parameterized queries: cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))',
        sources: ['Security Agent', 'Semgrep'],
        status: 'kept',
      },
      {
        id: 'f2',
        title: 'Hardcoded secret',
        severity: 'CRITICAL',
        confidence: 'HIGH',
        cwe: 'CWE-798',
        file: 'src/api.py',
        line: 13,
        evidence: 'SECRET_KEY = "hardcoded_secret_12345"',
        fix: 'Load from environment variable: SECRET_KEY = os.getenv("SECRET_KEY")',
        sources: ['Security Agent'],
        status: 'kept',
      },
      {
        id: 'f3',
        title: 'Command injection',
        severity: 'CRITICAL',
        confidence: 'HIGH',
        cwe: 'CWE-78',
        file: 'src/api.py',
        line: 14,
        evidence: 'subprocess.run(cmd, shell=True)',
        fix: 'Avoid shell=True or validate cmd input',
        sources: ['Security Agent'],
        status: 'kept',
      },
      {
        id: 'f4',
        title: 'Insecure deserialization',
        severity: 'HIGH',
        confidence: 'MEDIUM',
        cwe: 'CWE-502',
        file: 'src/api.py',
        line: 10,
        evidence: 'Function signature allows untrusted input',
        fix: 'Add input validation before processing',
        sources: ['Security Agent'],
        status: 'rejected',
        rejection_reason: 'No direct evidence of pickle or unsafe deserialization in diff',
      },
    ],
    created_at: new Date().toISOString(),
    finished_at: new Date().toISOString(),
  },
  {
    id: 'mock-2',
    status: 'failed',
    error: 'Ollama service unavailable',
    diff_text: 'diff --git a/test.py b/test.py',
    agents: [],
    findings: [],
    created_at: new Date().toISOString(),
  },
];

// Mock API
const submittedAt = new Map<string, number>();
let mockSequence = 2;
const demoCompletedReview = MOCK_REVIEWS[0];
const mockApi = {
  async createReview(req: CreateReviewRequest): Promise<CreateReviewResponse> {
    await new Promise(r => setTimeout(r, 500));
    const id = `mock-${++mockSequence}`;
    const now = new Date().toISOString();
    const review: Review = { ...MOCK_REVIEWS[0], id, status: 'running', verdict: undefined, duration_s: undefined, diff_text: req.diff_text, agents: MOCK_REVIEWS[0].agents.map((agent, index) => ({ ...agent, status: index === 0 ? 'done' : 'idle' })), findings: [], created_at: now, finished_at: undefined, report_md: undefined };
    MOCK_REVIEWS.unshift(review);
    submittedAt.set(id, Date.now());
    return { id, status: 'queued' };
  },
  async getReviews(): Promise<ReviewSummary[]> {
    await new Promise(r => setTimeout(r, 300));
    for (const review of MOCK_REVIEWS) {
      if (submittedAt.has(review.id)) await mockApi.getReview(review.id);
    }
    return MOCK_REVIEWS.map(r => ({
      id: r.id,
      status: r.status,
      verdict: r.verdict,
      finding_counts: {
        critical: r.findings.filter(f => f.severity === 'CRITICAL' && f.status === 'kept').length,
        high: r.findings.filter(f => f.severity === 'HIGH' && f.status === 'kept').length,
        medium: r.findings.filter(f => f.severity === 'MEDIUM' && f.status === 'kept').length,
        low: r.findings.filter(f => f.severity === 'LOW' && f.status === 'kept').length,
      },
      created_at: r.created_at,
      duration_s: r.duration_s,
    }));
  },
  async getReview(id: string): Promise<Review> {
    await new Promise(r => setTimeout(r, 300));
    const review = MOCK_REVIEWS.find(r => r.id === id);
    if (!review) throw new Error('Review not found');
    const started = submittedAt.get(id);
    if (started !== undefined) {
      const elapsed = Date.now() - started;
      if (elapsed > 6500) {
        review.status = 'done';
        review.verdict = 'REQUEST_CHANGES';
        review.duration_s = Math.round(elapsed / 1000);
        review.finished_at = new Date().toISOString();
        review.agents = demoCompletedReview.agents.map((agent) => ({ ...agent, status: 'done' }));
        review.findings = demoCompletedReview.findings;
        review.report_md = '# Review report\n\nThe demo review completed. Findings are illustrative demo data.';
        submittedAt.delete(id);
      } else {
        review.status = elapsed > 1800 ? 'running' : 'queued';
        review.agents = review.agents.map((agent, index) => ({ ...agent, status: elapsed > index * 700 + 500 ? 'running' : agent.status }));
      }
    }
    return review;
  },
  async deleteReview(id: string): Promise<void> {
    await new Promise(r => setTimeout(r, 300));
    const idx = MOCK_REVIEWS.findIndex(r => r.id === id);
    if (idx === -1) throw new Error('Review not found');
    submittedAt.delete(id);
    MOCK_REVIEWS.splice(idx, 1);
  },
  async getSamples(): Promise<Sample[]> {
    await new Promise(r => setTimeout(r, 300));
    return [
      {
        id: 'banking-api',
        name: 'Banking API Demo',
        description: 'Intentional vulnerabilities: SQL injection, hardcoded secrets, command injection',
        diff_text: demoCompletedReview.diff_text,
      },
    ];
  },
  async getStats(): Promise<Stats> {
    await new Promise(r => setTimeout(r, 300));
    const finished = MOCK_REVIEWS.filter(review => review.status === 'done');
    return {
      total_reviews: MOCK_REVIEWS.length,
      finding_counts: {
        critical: finished.flatMap(r => r.findings).filter(f => f.severity === 'CRITICAL' && f.status === 'kept').length,
        high: finished.flatMap(r => r.findings).filter(f => f.severity === 'HIGH' && f.status === 'kept').length,
        medium: finished.flatMap(r => r.findings).filter(f => f.severity === 'MEDIUM' && f.status === 'kept').length,
        low: finished.flatMap(r => r.findings).filter(f => f.severity === 'LOW' && f.status === 'kept').length,
      },
      verdict_split: {
        approve: finished.filter(r => r.verdict === 'APPROVE').length,
        request_changes: finished.filter(r => r.verdict === 'REQUEST_CHANGES').length,
      },
      avg_review_time_s: finished.length ? finished.reduce((sum, r) => sum + (r.duration_s ?? 0), 0) / finished.length : 0,
    };
  },
};

// Real API
const realApi = {
  async createReview(req: CreateReviewRequest): Promise<CreateReviewResponse> {
    return request<CreateReviewResponse>('/api/reviews', {
      method: 'POST',
      body: JSON.stringify(req),
    });
  },
  async getReviews(): Promise<ReviewSummary[]> {
    return request<ReviewSummary[]>('/api/reviews');
  },
  async getReview(id: string): Promise<Review> {
    return request<Review>(`/api/reviews/${id}`);
  },
  async deleteReview(id: string): Promise<void> {
    return request<void>(`/api/reviews/${id}`, { method: 'DELETE' });
  },
  async getSamples(): Promise<Sample[]> {
    return request<Sample[]>('/api/samples');
  },
  async getStats(): Promise<Stats> {
    return request<Stats>('/api/stats');
  },
};

export const api = USE_MOCK ? mockApi : realApi;
