"""Post inline PR review comments for accepted SentinelCode findings."""

import argparse
import json
import os
from pathlib import Path
import sys
import requests

from src.structured_findings import parse_accepted_findings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Post inline SentinelCode review comments to GitHub PR files."
    )
    parser.add_argument(
        "--repo",
        default=os.getenv("GITHUB_REPOSITORY"),
        help="GitHub repository in owner/repo format (e.g., octocat/Hello-World)",
    )
    parser.add_argument(
        "--pr-number",
        default=os.getenv("PR_NUMBER"),
        help="Pull request number",
    )
    parser.add_argument(
        "--report-file",
        required=True,
        help="Path to the generated Markdown report file (e.g., review.md)",
    )
    parser.add_argument(
        "--diff-file",
        default="pr.diff",
        help="Path to the unified diff file to map lines accurately (default: pr.diff)",
    )
    parser.add_argument(
        "--metadata-file",
        help="Optional path to structured metadata JSON file",
    )
    parser.add_argument(
        "--commit-sha",
        default=os.getenv("COMMIT_SHA"),
        help="Head commit SHA for the pull request",
    )
    parser.add_argument(
        "--token",
        default=os.getenv("GITHUB_TOKEN"),
        help="GitHub authentication token",
    )
    return parser.parse_args()


def format_inline_comment(finding: dict) -> str:
    """Format an accepted finding into the required inline comment Markdown template."""
    title = finding.get("title", "Issue Detected")
    sev = finding.get("severity", "MEDIUM")
    conf = finding.get("confidence", "HIGH")
    evidence = finding.get("evidence", "").strip()
    fix = finding.get("fix", "").strip()
    sources = finding.get("source", ["SentinelCode"])
    if isinstance(sources, list):
        source_str = ", ".join(sources)
    else:
        source_str = str(sources)

    # Format evidence with backticks if not already formatted
    formatted_evidence = evidence
    if evidence and not evidence.startswith("`") and not evidence.startswith("```"):
        if "\n" in evidence:
            formatted_evidence = f"```\n{evidence}\n```"
        else:
            formatted_evidence = f"`{evidence}`"

    parts = [
        f"**🛡️ SentinelCode: {sev} | {conf} — {title}**\n",
    ]

    if formatted_evidence:
        parts.append(f"**Evidence:**  \n{formatted_evidence}\n")

    if fix:
        parts.append(f"**Recommended fix:**  \n{fix}\n")

    parts.append(f"**Source:** {source_str}")

    return "\n".join(parts)


def get_existing_inline_comments(
    api_base: str,
    headers: dict,
    pr_number: int,
) -> list[dict]:
    """Fetch existing review comments on the pull request to prevent duplicates."""
    url = f"{api_base}/pulls/{pr_number}/comments"
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.json()
        print(
            f"Warning: Failed to fetch existing inline comments (HTTP {response.status_code}).",
            file=sys.stderr,
        )
    except Exception as exc:
        print(f"Warning: Network error fetching existing comments: {exc}", file=sys.stderr)
    return []


def get_head_commit_sha(
    api_base: str,
    headers: dict,
    pr_number: int,
) -> str | None:
    """Fetch the latest head commit SHA of the pull request."""
    url = f"{api_base}/pulls/{pr_number}"
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            return data.get("head", {}).get("sha")
    except Exception as exc:
        print(f"Warning: Could not fetch head commit SHA: {exc}", file=sys.stderr)
    return None


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    args = parse_args()

    token = (args.token or "").strip()
    if not token:
        print("Error: GitHub token must be provided via --token or GITHUB_TOKEN.", file=sys.stderr)
        sys.exit(1)

    repo = (args.repo or "").strip()
    if not repo or "/" not in repo:
        print(f"Error: Invalid or missing repository '{repo}'.", file=sys.stderr)
        sys.exit(1)

    try:
        pr_number = int(str(args.pr_number).strip())
    except (TypeError, ValueError):
        print(f"Error: Invalid or missing pull request number: {args.pr_number}", file=sys.stderr)
        sys.exit(1)

    report_path = Path(args.report_file)
    if not report_path.is_file():
        print(f"Error: Report file '{args.report_file}' does not exist.", file=sys.stderr)
        sys.exit(1)

    report_content = report_path.read_text(encoding="utf-8")

    # Load diff text if available
    diff_text = None
    if args.diff_file and Path(args.diff_file).is_file():
        diff_text = Path(args.diff_file).read_text(encoding="utf-8")

    # Load structured findings
    findings: list[dict] = []
    if args.metadata_file and Path(args.metadata_file).is_file():
        try:
            findings = json.loads(Path(args.metadata_file).read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"Warning: Failed to load metadata file: {exc}", file=sys.stderr)

    if not findings:
        findings = parse_accepted_findings(report_content, diff_text)

    if not findings:
        print("No accepted findings to comment on. Skipping inline comments.")
        sys.exit(0)

    api_base = f"https://api.github.com/repos/{repo}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "SentinelCode-Reviewer",
    }

    commit_sha = (args.commit_sha or "").strip()
    if not commit_sha:
        commit_sha = get_head_commit_sha(api_base, headers, pr_number)

    if not commit_sha:
        print("Error: Could not determine head commit SHA for pull request.", file=sys.stderr)
        sys.exit(1)

    existing_comments = get_existing_inline_comments(api_base, headers, pr_number)

    posted_count = 0
    max_comments = 10

    for finding in findings:
        if posted_count >= max_comments:
            print(f"Reached maximum limit of {max_comments} inline comments. Stopping.")
            break

        file_path = finding.get("file")
        line_no = finding.get("line")
        title = finding.get("title", "")

        if not file_path or not line_no:
            print(
                f"Warning: Skipping inline comment for finding '{title}': "
                f"could not determine file path and line number in diff."
            )
            continue

        # Check for duplicate comment
        is_duplicate = False
        for ex in existing_comments:
            if (
                ex.get("path") == file_path
                and ex.get("line") == line_no
                and title in ex.get("body", "")
            ):
                is_duplicate = True
                break

        if is_duplicate:
            print(f"Skipping duplicate inline comment for {file_path}:{line_no} — {title}")
            continue

        body = format_inline_comment(finding)
        payload = {
            "body": body,
            "commit_id": commit_sha,
            "path": file_path,
            "line": int(line_no),
            "side": "RIGHT",
        }

        comment_url = f"{api_base}/pulls/{pr_number}/comments"
        try:
            res = requests.post(comment_url, json=payload, headers=headers, timeout=30)
            if res.status_code in (200, 201):
                posted_count += 1
                print(f"Successfully posted inline comment on {file_path}:{line_no} ({title})")
            else:
                print(
                    f"Warning: GitHub API rejected inline comment on {file_path}:{line_no} "
                    f"(HTTP {res.status_code}): {res.text}",
                    file=sys.stderr,
                )
        except Exception as exc:
            print(f"Warning: Network error posting inline comment on {file_path}:{line_no}: {exc}", file=sys.stderr)

    print(f"Inline PR review commenting finished. Total posted: {posted_count}.")
    sys.exit(0)


if __name__ == "__main__":
    main()
