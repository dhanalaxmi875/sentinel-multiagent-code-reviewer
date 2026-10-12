"""SentinelCode: AI-powered multi-agent code review using local Qwen via Ollama.

Usage examples:
    code-review                        # review staged changes
    code-review --unstaged             # review unstaged changes
    code-review --branch main          # review current branch vs main
    code-review --file patch.diff      # review a saved diff file
    code-review --commit abc123        # review a specific commit
"""

import argparse
import pathlib
import subprocess
import sys


def _run_git(*args: str) -> str:
    """Run a git command and return stdout. Exits with an error on failure."""
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"git error: {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    return result.stdout


def _get_diff_and_files(args: argparse.Namespace) -> tuple[str, list[str]]:
    """Return (diff_text, file_paths) based on the chosen mode."""
    if args.file:
        path = pathlib.Path(args.file)
        if not path.exists():
            print(f"File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        return path.read_text(), []

    if args.branch:
        diff = _run_git("diff", f"{args.branch}...HEAD")
        files = _run_git("diff", "--name-only", f"{args.branch}...HEAD").splitlines()
    elif args.commit:
        diff = _run_git("diff", f"{args.commit}~1", args.commit)
        files = _run_git("diff", "--name-only", f"{args.commit}~1", args.commit).splitlines()
    elif args.unstaged:
        diff = _run_git("diff")
        files = _run_git("diff", "--name-only").splitlines()
    else:
        # Default: staged changes
        diff = _run_git("diff", "--cached")
        files = _run_git("diff", "--cached", "--name-only").splitlines()

    if not diff.strip():
        print("No diff found. Nothing to review.", file=sys.stderr)
        sys.exit(0)

    return diff, files


def main() -> None:
    """Entry point for the `code-review` CLI command."""
    parser = argparse.ArgumentParser(
        prog="code-review",
        description="AI-powered multi-agent code review using Claude.",
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--branch",
        metavar="BRANCH",
        help="Review diff between BRANCH and HEAD (e.g. --branch main)",
    )
    mode.add_argument(
        "--commit",
        metavar="SHA",
        help="Review a specific commit (e.g. --commit abc1234)",
    )
    mode.add_argument(
        "--unstaged",
        action="store_true",
        help="Review unstaged working-directory changes instead of staged",
    )
    mode.add_argument(
        "--file",
        metavar="PATH",
        help="Review a saved unified diff file",
    )

    parser.add_argument(
        "--output",
        metavar="PATH",
        help="Write the review to a file instead of stdout",
    )

    args = parser.parse_args()

    # Import here so the CLI starts fast and errors only if the package is broken
    from dotenv import load_dotenv
    load_dotenv()
    from src.main import run_review

    diff, files = _get_diff_and_files(args)
    review = run_review(diff, files)

    if args.output:
        pathlib.Path(args.output).write_text(review)
        print(f"Review written to {args.output}")
    else:
        print(review)


if __name__ == "__main__":
    main()
