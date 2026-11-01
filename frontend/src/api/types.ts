// API Types for SentinelCode Backend

export type AgentStatus = 'idle' | 'running' | 'done' | 'skipped';
export type ReviewStatus = 'queued' | 'running' | 'done' | 'failed';
export type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
export type Confidence = 'HIGH' | 'MEDIUM' | 'LOW';
export type Verdict = 'APPROVE' | 'REQUEST_CHANGES';
export type FindingStatus = 'kept' | 'rejected';

export interface AgentInfo {
  agent: string;
  status: AgentStatus;
  duration_s: number;
  finding_count: number;
}

export interface Finding {
  id: string;
  title: string;
  severity: Severity;
  confidence: Confidence;
  cwe: string;
  file: string;
  line: number;
  evidence: string;
  fix: string;
  sources: string[];
  status: FindingStatus;
  rejection_reason?: string;
}

export interface Review {
  id: string;
  status: ReviewStatus;
  verdict?: Verdict;
  duration_s?: number;
  error?: string;
  report_md?: string;
  diff_text: string;
  agents: AgentInfo[];
  findings: Finding[];
  created_at: string;
  finished_at?: string;
}

export interface ReviewSummary {
  id: string;
  status: ReviewStatus;
  verdict?: Verdict;
  finding_counts: {
    critical: number;
    high: number;
    medium: number;
    low: number;
  };
  created_at: string;
  duration_s?: number;
}

export interface CreateReviewRequest {
  diff_text: string;
  file_paths?: string[];
  source?: string;
}

export interface CreateReviewResponse {
  id: string;
  status: ReviewStatus;
}

export interface Stats {
  total_reviews: number;
  finding_counts: {
    critical: number;
    high: number;
    medium: number;
    low: number;
  };
  verdict_split: {
    approve: number;
    request_changes: number;
  };
  avg_review_time_s: number;
}

export interface Sample {
  id: string;
  name: string;
  description: string;
  diff_text: string;
  file_paths?: string[];
}
