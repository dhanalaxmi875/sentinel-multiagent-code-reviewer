export const MAX_DIFF_CHARS = 40_000;

export function validateDiff(text: string): string | null {
  if (!text.trim()) return 'Paste or upload a unified diff to continue.';
  if (text.length > MAX_DIFF_CHARS) return `Diff must be ${MAX_DIFF_CHARS.toLocaleString()} characters or fewer.`;
  const hasFileHeader = /^diff --git a\/\S+ b\/\S+$/m.test(text) || (/^--- (?:a\/\S+|\/dev\/null)$/m.test(text) && /^\+\+\+ (?:b\/\S+|\/dev\/null)$/m.test(text));
  const hasHunk = /^@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@/m.test(text);
  return hasFileHeader && hasHunk ? null : 'This does not look like a unified diff. Include file headers and a hunk (starting with @@).';
}
