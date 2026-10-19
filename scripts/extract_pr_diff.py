"""Extract PR diff between base SHA and head SHA using git diff."""

import argparse
from pathlib import Path
import subprocess
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract pull-request diff between base and head commits."
    )
    parser.add_argument(
        "--base-sha",
        required=True,
        help="Base commit SHA (target branch commit)",
    )
    parser.add_argument(
        "--head-sha",
        required=True,
        help="Head commit SHA (PR branch commit)",
    )
    parser.add_argument(
        "--output",
        default="pr.diff",
        help="Output file path for the diff (default: pr.diff)",
    )
    return parser.parse_args()


def run_git_diff(base_sha: str, head_sha: str) -> subprocess.CompletedProcess:
    """Run git diff command with three dots to get PR changes."""
    cmd = ["git", "diff", "--no-color", f"{base_sha}...{head_sha}"]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> None:
    args = parse_args()

    base_sha = args.base_sha.strip()
    head_sha = args.head_sha.strip()

    if not base_sha or not head_sha:
        print("Error: Both --base-sha and --head-sha must be non-empty.", file=sys.stderr)
        sys.exit(1)

    result = run_git_diff(base_sha, head_sha)

    # If git diff fails (e.g. shallow clone missing SHAs), attempt fetch and retry
    if result.returncode != 0:
        subprocess.run(
            ["git", "fetch", "--depth=1", "origin", base_sha],
            capture_output=True,
            check=False,
        )
        subprocess.run(
            ["git", "fetch", "--depth=1", "origin", head_sha],
            capture_output=True,
            check=False,
        )
        result = run_git_diff(base_sha, head_sha)

    if result.returncode != 0:
        error_msg = result.stderr.strip() or "Unknown git diff failure."
        print(f"Git diff error ({result.returncode}): {error_msg}", file=sys.stderr)
        sys.exit(result.returncode or 1)

    diff_content = result.stdout

    output_path = Path(args.output)
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(diff_content, encoding="utf-8")
    except OSError as exc:
        print(f"Error writing diff to '{output_path}': {exc}", file=sys.stderr)
        sys.exit(1)

    if not diff_content.strip():
        print(f"Empty diff detected between {base_sha} and {head_sha}. Saved empty diff to {output_path}.")
    else:
        print(f"Successfully extracted diff ({len(diff_content)} bytes) to {output_path}.")

    sys.exit(0)


if __name__ == "__main__":
    main()
