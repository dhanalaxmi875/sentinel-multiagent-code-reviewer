"""Post SentinelCode review report as a GitHub pull-request comment."""

import argparse
import os
from pathlib import Path
import sys
import requests


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Post SentinelCode review report to GitHub pull-request comment."
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
        help="Path to the generated Markdown report file",
    )
    parser.add_argument(
        "--token",
        default=os.getenv("GITHUB_TOKEN"),
        help="GitHub token for authentication",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    token = (args.token or "").strip()
    if not token:
        print(
            "Error: GitHub token must be provided via --token or GITHUB_TOKEN environment variable.",
            file=sys.stderr,
        )
        sys.exit(1)

    repo = (args.repo or "").strip()
    if not repo or "/" not in repo:
        print(
            f"Error: Invalid or missing repository '{repo}'. Must be in 'owner/repo' format.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        pr_number = int(str(args.pr_number).strip())
    except (TypeError, ValueError):
        print(
            f"Error: Invalid or missing pull request number: {args.pr_number}",
            file=sys.stderr,
        )
        sys.exit(1)

    report_path = Path(args.report_file)
    if not report_path.is_file():
        print(
            f"Error: Report file '{args.report_file}' does not exist or is not a file.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        report_content = report_path.read_text(encoding="utf-8").strip()
    except Exception as exc:
        print(f"Error reading report file '{args.report_file}': {exc}", file=sys.stderr)
        sys.exit(1)

    comment_header = "## 🛡️ SentinelCode AI Review\n\n"
    comment_body = f"{comment_header}{report_content}\n"

    api_url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "SentinelCode-Reviewer",
    }
    payload = {"body": comment_body}

    try:
        response = requests.post(
            api_url,
            json=payload,
            headers=headers,
            timeout=30,
        )
    except requests.RequestException as exc:
        print(f"Network error while connecting to GitHub API: {exc}", file=sys.stderr)
        sys.exit(1)

    if response.status_code in (200, 201):
        data = response.json()
        comment_url = data.get("html_url", "")
        print(f"Successfully posted SentinelCode review to {repo} PR #{pr_number}.")
        if comment_url:
            print(f"Comment URL: {comment_url}")
        sys.exit(0)
    else:
        print(
            f"GitHub API error (HTTP {response.status_code}): {response.text}",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
