"""Generate the sample diff from actual before/after Python files.

The diff is produced by difflib so it reflects real code changes —
open examples/app_before.py and examples/app_after.py to read the source.
"""

import difflib
import os

_here = os.path.dirname(__file__)

with open(os.path.join(_here, "app_before.py")) as f:
    _before_lines = f.readlines()

with open(os.path.join(_here, "app_after.py")) as f:
    _after_lines = f.readlines()

SAMPLE_FILE_PATHS = ["examples/app_after.py"]

SAMPLE_DIFF = "".join(
    difflib.unified_diff(
        _before_lines,
        _after_lines,
        fromfile="a/examples/app_before.py",
        tofile="b/examples/app_after.py",
        lineterm="",
    )
)
