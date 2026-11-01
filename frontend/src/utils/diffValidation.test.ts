import { describe, it, expect } from 'vitest';

describe('Diff Validation', () => {
  const validateDiff = (text: string): boolean => {
    if (!text.trim()) return false;
    if (text.length > 40000) return false;
    return text.includes('diff --git') || text.includes('---') || text.includes('+++');
  };

  it('should accept valid unified diff', () => {
    const validDiff = `diff --git a/src/api.py b/src/api.py
index 1234567..abcdef 100644
--- a/src/api.py
+++ b/src/api.py
@@ -10,0 +10,5 @@
+def transfer_funds(user_id, amount):
+    cursor.execute("SELECT * FROM users WHERE id = " + user_id)`;
    expect(validateDiff(validDiff)).toBe(true);
  });

  it('should reject empty diff', () => {
    expect(validateDiff('')).toBe(false);
    expect(validateDiff('   ')).toBe(false);
  });

  it('should reject diff exceeding 40000 characters', () => {
    const longDiff = 'a'.repeat(40001) + 'diff --git a/file b/file';
    expect(validateDiff(longDiff)).toBe(false);
  });

  it('should accept diff with --- marker', () => {
    const diffWithMarker = `--- a/file.py
+++ b/file.py
@@ -1,1 +1,1 @@
-old line
+new line`;
    expect(validateDiff(diffWithMarker)).toBe(true);
  });

  it('should accept diff with +++ marker', () => {
    const diffWithMarker = `+++ b/file.py
@@ -1,1 +1,1 @@
-old line
+new line`;
    expect(validateDiff(diffWithMarker)).toBe(true);
  });

  it('should reject plain text without diff markers', () => {
    expect(validateDiff('some random text')).toBe(false);
  });
});
