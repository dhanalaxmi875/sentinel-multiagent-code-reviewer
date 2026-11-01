/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, it, expect } from 'vitest';

describe('Filter Logic', () => {
  const mockFindings = [
    { id: '1', severity: 'CRITICAL', status: 'kept', title: 'SQL Injection' },
    { id: '2', severity: 'HIGH', status: 'kept', title: 'XSS' },
    { id: '3', severity: 'MEDIUM', status: 'kept', title: 'Unused Variable' },
    { id: '4', severity: 'LOW', status: 'kept', title: 'Code Style' },
    { id: '5', severity: 'CRITICAL', status: 'rejected', title: 'False Positive' },
  ];

  it('should filter findings by severity', () => {
    const filterBySeverity = (findings: any[], severity: string) => {
      return findings.filter(f => f.severity === severity);
    };

    const critical = filterBySeverity(mockFindings, 'CRITICAL');
    expect(critical).toHaveLength(2);
    expect(critical.every(f => f.severity === 'CRITICAL')).toBe(true);
  });

  it('should filter findings by status', () => {
    const filterByStatus = (findings: any[], status: string) => {
      return findings.filter(f => f.status === status);
    };

    const kept = filterByStatus(mockFindings, 'kept');
    expect(kept).toHaveLength(4);
    expect(kept.every(f => f.status === 'kept')).toBe(true);

    const rejected = filterByStatus(mockFindings, 'rejected');
    expect(rejected).toHaveLength(1);
    expect(rejected[0].status).toBe('rejected');
  });

  it('should filter findings by both severity and status', () => {
    const filterByBoth = (findings: any[], severity: string, status: string) => {
      return findings.filter(f => f.severity === severity && f.status === status);
    };

    const criticalKept = filterByBoth(mockFindings, 'CRITICAL', 'kept');
    expect(criticalKept).toHaveLength(1);
    expect(criticalKept[0].id).toBe('1');
  });

  it('should filter findings by search term', () => {
    const filterBySearch = (findings: any[], term: string) => {
      const lowerTerm = term.toLowerCase();
      return findings.filter(f =>
        f.title.toLowerCase().includes(lowerTerm)
      );
    };

    const sqlResults = filterBySearch(mockFindings, 'sql');
    expect(sqlResults).toHaveLength(1);
    expect(sqlResults[0].title).toBe('SQL Injection');

    const falseResults = filterBySearch(mockFindings, 'false');
    expect(falseResults).toHaveLength(1);
    expect(falseResults[0].title).toBe('False Positive');
  });

  it('should return empty array for non-matching filters', () => {
    const filterBySeverity = (findings: any[], severity: string) => {
      return findings.filter(f => f.severity === severity);
    };

    const none = filterBySeverity(mockFindings, 'NONEXISTENT');
    expect(none).toHaveLength(0);
  });

  it('should handle empty findings array', () => {
    const filterBySeverity = (findings: any[], severity: string) => {
      return findings.filter(f => f.severity === severity);
    };

    const result = filterBySeverity([], 'CRITICAL');
    expect(result).toHaveLength(0);
  });
});
