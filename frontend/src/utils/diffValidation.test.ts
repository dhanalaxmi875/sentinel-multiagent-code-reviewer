import { describe, it, expect } from 'vitest';
import { validateDiff, MAX_DIFF_CHARS } from './diffValidation';

describe('Diff Validation', () => {
  const goodDiff = `diff --git a/file.ts b/file.ts\n--- a/file.ts\n+++ b/file.ts\n@@ -1,1 +1,1 @@\n-old\n+new`;

  it('should accept valid unified diff', () => {
    expect(validateDiff(goodDiff)).toBeNull();
  });

  it('should reject empty diff', () => {
    expect(validateDiff('')).not.toBeNull();
    expect(validateDiff('   ')).not.toBeNull();
  });

  it('should reject diff exceeding 40000 characters', () => {
    expect(validateDiff(goodDiff + ' '.repeat(MAX_DIFF_CHARS))).not.toBeNull();
  });

  it('should accept diff with --- marker', () => {
    expect(validateDiff(goodDiff)).toBeNull();
  });

  it('should reject incomplete file headers', () => {
    expect(validateDiff('+++ b/file.py\n@@ -1,1 +1,1 @@\n-old\n+new')).not.toBeNull();
  });

  it('should reject plain text without diff markers', () => {
    expect(validateDiff('some random text')).not.toBeNull();
  });

  it('rejects file headers without a hunk', () => {
    expect(validateDiff('diff --git a/a b/a\n--- a/a\n+++ b/a')).not.toBeNull();
  });
});
