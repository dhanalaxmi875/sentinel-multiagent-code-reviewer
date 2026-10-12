"""Eval test cases.

Each case is a dict with:
  - name        : human-readable label
  - diff        : the code diff to review
  - file_paths  : list of changed file paths
  - must_mention: list of keyword groups — the review MUST contain at least one
                  keyword from each group (case-insensitive). All groups must
                  pass for the case to be considered a PASS.
  - must_not    : list of strings that must NOT appear in the review.
"""

CASES = [
    {
        "name": "sql_injection",
        "file_paths": ["src/api/users.py"],
        "diff": '''\
diff --git a/src/api/users.py b/src/api/users.py
--- a/src/api/users.py
+++ b/src/api/users.py
@@ -1,5 +1,8 @@
+def get_user(user_id):
+    query = "SELECT * FROM users WHERE id = " + user_id
+    return db.execute(query)
''',
        "must_mention": [
            ["sql injection", "sql", "injection", "parameterized", "parameterise"],
        ],
        "must_not": [],
    },
    {
        "name": "hardcoded_secret",
        "file_paths": ["src/config.py"],
        "diff": '''\
diff --git a/src/config.py b/src/config.py
--- a/src/config.py
+++ b/src/config.py
@@ -1,3 +1,5 @@
+SECRET_KEY = "hardcoded_secret_abc123"
+DB_PASSWORD = "admin123"
''',
        "must_mention": [
            ["hardcoded", "secret", "credential", "password", "environment variable", "env"],
        ],
        "must_not": [],
    },
    {
        "name": "off_by_one",
        "file_paths": ["src/utils.py"],
        "diff": '''\
diff --git a/src/utils.py b/src/utils.py
--- a/src/utils.py
+++ b/src/utils.py
@@ -1,6 +1,8 @@
+def get_last_items(items, n):
+    result = []
+    for i in range(len(items) - n, len(items) + 1):
+        result.append(items[i])
+    return result
''',
        "must_mention": [
            ["off-by-one", "index", "out of range", "bounds", "indexerror", "len(items)"],
        ],
        "must_not": [],
    },
    {
        "name": "clean_code_approved",
        "file_paths": ["src/math_utils.py"],
        "diff": '''\
diff --git a/src/math_utils.py b/src/math_utils.py
--- a/src/math_utils.py
+++ b/src/math_utils.py
@@ -1,4 +1,8 @@
+def clamp(value: float, min_val: float, max_val: float) -> float:
+    """Return value constrained to [min_val, max_val]."""
+    return max(min_val, min(value, max_val))
''',
        "must_mention": [
            ["approve", "no issue", "clean", "looks good", "no critical", "no security", "none"],
        ],
        "must_not": ["critical", "sql injection", "hardcoded"],
    },
]
