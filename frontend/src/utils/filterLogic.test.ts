import { describe, expect, it } from 'vitest';
import type { Finding } from '../api/types';
import { filterFindings, pollingInterval } from './filterLogic';

const findings: Finding[] = [
  { id: '1', severity: 'CRITICAL', status: 'kept', title: 'SQL injection', confidence: 'HIGH', cwe: 'CWE-89', file: 'src/db.ts', line: 2, evidence: 'query + input', fix: 'parameterize', sources: ['Security'] },
  { id: '2', severity: 'HIGH', status: 'kept', title: 'XSS', confidence: 'MEDIUM', cwe: 'CWE-79', file: 'src/ui.ts', line: 8, evidence: 'unsafe html', fix: 'escape', sources: ['Bug'] },
  { id: '3', severity: 'CRITICAL', status: 'rejected', title: 'False positive', confidence: 'LOW', cwe: 'CWE-20', file: 'src/a.ts', line: 1, evidence: 'validated', fix: 'none', sources: ['Verifier'] },
];

describe('Finding filters', () => {
  it('filters by severity and excludes rejected findings', () => expect(filterFindings(findings, '', 'CRITICAL').map(f => f.id)).toEqual(['1']));
  it('searches title, path, evidence, CWE, and source', () => {
    expect(filterFindings(findings, 'src/ui', '').map(f => f.id)).toEqual(['2']);
    expect(filterFindings(findings, 'security', '')).toHaveLength(1);
  });
  it('handles empty and non-matching results', () => {
    expect(filterFindings([], '', '')).toEqual([]);
    expect(filterFindings(findings, 'not here', '')).toEqual([]);
  });
});

describe('Review polling interval', () => {
  it.each(['queued', 'running'])('polls while %s', status => expect(pollingInterval(status)).toBe(2000));
  it.each(['done', 'failed', undefined])('stops when status is %s', status => expect(pollingInterval(status)).toBe(false));
});
