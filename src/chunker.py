"""Diff chunking utilities.

Strategy: split the unified diff by file (each `diff --git` block), then
enforce a per-file character budget so no single LLM call exceeds the
MAX_DIFF_CHARS limit. Files are truncated in isolation — the largest files
are cut first — so smaller, complete file diffs are always preserved intact.
"""

import re
from src.config import MAX_DIFF_CHARS
from src.logger import get_logger

_log = get_logger("chunker")

_FILE_HEADER = re.compile(r"(?=diff --git )")


def _split_by_file(diff: str) -> list[str]:
    """Split a unified diff into per-file blocks."""
    blocks = _FILE_HEADER.split(diff)
    return [b for b in blocks if b.strip()]


def prepare_diff(diff: str) -> str:
    """Return a diff safe to send to agents, truncating if necessary.

    If the total diff is within MAX_DIFF_CHARS, it is returned unchanged.
    Otherwise each file block is trimmed proportionally so the combined
    result stays under the limit, and a warning header is prepended.
    """
    if len(diff) <= MAX_DIFF_CHARS:
        return diff

    blocks = _split_by_file(diff)
    budget_per_file = MAX_DIFF_CHARS // max(len(blocks), 1)
    truncated = []
    files_cut = []

    for block in blocks:
        if len(block) > budget_per_file:
            # Extract filename for the warning message
            match = re.search(r"diff --git a/(\S+)", block)
            fname = match.group(1) if match else "unknown"
            files_cut.append(fname)
            block = block[:budget_per_file] + "\n... [truncated] ..."
        truncated.append(block)

    warning = (
        f"[CHUNKER WARNING] Diff exceeded {MAX_DIFF_CHARS:,} chars. "
        f"The following files were truncated: {', '.join(files_cut)}\n\n"
    )
    _log.warning(
        "Diff truncated from %d chars to ~%d chars. Files cut: %s",
        len(diff),
        MAX_DIFF_CHARS,
        files_cut,
    )
    return warning + "".join(truncated)
