import type { Finding, Severity } from '../api/types';

export function filterFindings(findings: Finding[], search: string, severity: Severity | ''): Finding[] {
  const term = search.trim().toLocaleLowerCase();
  return findings.filter((finding) => {
    const matchesSeverity = !severity || finding.severity === severity;
    const haystack = `${finding.title} ${finding.file} ${finding.evidence} ${finding.cwe} ${finding.sources.join(' ')}`.toLocaleLowerCase();
    return finding.status === 'kept' && matchesSeverity && (!term || haystack.includes(term));
  });
}

export function pollingInterval(status: string | undefined): number | false {
  return status === 'queued' || status === 'running' ? 2000 : false;
}
