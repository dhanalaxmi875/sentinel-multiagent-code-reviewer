"""Manage SentinelCode AI Review GitHub Check Run."""

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import sys
import requests


CHECK_RUN_NAME = "SentinelCode AI Review"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create or update SentinelCode GitHub Check Run."
    )
    parser.add_argument(
        "--repo",
        default=os.getenv("GITHUB_REPOSITORY"),
        help="GitHub repository in owner/repo format",
    )
    parser.add_argument(
        "--head-sha",
        default=os.getenv("HEAD_SHA"),
        help="Commit SHA to attach the check run to",
    )
    parser.add_argument(
        "--status",
        choices=["in_progress", "completed"],
        default="completed",
        help="Status of the check run: in_progress or completed",
    )
    parser.add_argument(
        "--report-file",
        help="Path to the Markdown review report file (e.g., review.md)",
    )
    parser.add_argument(
        "--token",
        default=os.getenv("GITHUB_TOKEN"),
        help="GitHub authentication token",
    )
    parser.add_argument(
        "--check-run-id-file",
        default=".sentinelcode_check_run_id",
        help="File path to save or read the created check run ID",
    )
    parser.add_argument(
        "--check-run-id",
        help="Optional explicit check run ID to update",
    )
    return parser.parse_args()


def extract_verdict_and_summary(report_path: Path | None) -> tuple[str, str, str]:
    """
    Extract verdict, conclusion, and summary from the report file.

    Returns:
        (verdict, conclusion, summary)
    """
    if not report_path or not report_path.is_file():
        return (
            "MISSING",
            "failure",
            "SentinelCode review report is missing or invalid. Check failed.",
        )

    try:
        report_text = report_path.read_text(encoding="utf-8")
    except Exception:
        return (
            "INVALID",
            "failure",
            "SentinelCode review report could not be read. Check failed.",
        )

    verdict_match = re.search(r"### Verdict\s*\n+([^\n]+)", report_text, flags=re.IGNORECASE)
    verdict_line = verdict_match.group(1).strip() if verdict_match else ""

    if "REQUEST CHANGES" in verdict_line.upper():
        return (
            "REQUEST CHANGES",
            "failure",
            "SentinelCode review completed. Critical or high-severity findings require changes before merge.",
        )
    elif "APPROVE" in verdict_line.upper():
        return (
            "APPROVE",
            "success",
            "SentinelCode review completed. No critical or high-severity verified findings were identified.",
        )
    else:
        return (
            "UNKNOWN",
            "failure",
            "SentinelCode review completed with an indeterminate verdict. Review requires manual inspection.",
        )


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

    head_sha = (args.head_sha or "").strip()
    if not head_sha:
        print("Error: Head commit SHA must be provided via --head-sha or HEAD_SHA.", file=sys.stderr)
        sys.exit(1)

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "SentinelCode-Reviewer",
    }
    api_base = f"https://api.github.com/repos/{repo}"

    check_run_id_path = Path(args.check_run_id_file)
    existing_check_run_id = args.check_run_id
    if not existing_check_run_id and check_run_id_path.is_file():
        saved_id = check_run_id_path.read_text(encoding="utf-8").strip()
        if saved_id.isdigit():
            existing_check_run_id = saved_id

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if args.status == "in_progress":
        payload = {
            "name": CHECK_RUN_NAME,
            "head_sha": head_sha,
            "status": "in_progress",
            "started_at": now_iso,
            "output": {
                "title": CHECK_RUN_NAME,
                "summary": "SentinelCode AI code review and security analysis is in progress...",
            },
        }

        url = f"{api_base}/check-runs"
        try:
            res = requests.post(url, json=payload, headers=headers, timeout=30)
            if res.status_code in (200, 201):
                data = res.json()
                created_id = str(data.get("id"))
                check_run_id_path.write_text(created_id, encoding="utf-8")
                print(f"Started check run '{CHECK_RUN_NAME}' (ID: {created_id}).")
                sys.exit(0)
            else:
                print(
                    f"Warning: Failed to start check run (HTTP {res.status_code}): {res.text}",
                    file=sys.stderr,
                )
                sys.exit(0)
        except Exception as exc:
            print(f"Warning: Network error starting check run: {exc}", file=sys.stderr)
            sys.exit(0)

    else:
        # Completed status
        report_path = Path(args.report_file) if args.report_file else None
        verdict, conclusion, summary = extract_verdict_and_summary(report_path)

        report_text = ""
        if report_path and report_path.is_file():
            try:
                report_text = report_path.read_text(encoding="utf-8")
            except Exception:
                pass

        payload = {
            "name": CHECK_RUN_NAME,
            "head_sha": head_sha,
            "status": "completed",
            "conclusion": conclusion,
            "completed_at": now_iso,
            "output": {
                "title": CHECK_RUN_NAME,
                "summary": summary,
                "text": report_text[:65000] if report_text else summary,
            },
        }

        # If we have an existing check run ID, update it with PATCH; otherwise POST a new completed check run
        if existing_check_run_id:
            patch_url = f"{api_base}/check-runs/{existing_check_run_id}"
            try:
                res = requests.patch(patch_url, json=payload, headers=headers, timeout=30)
                if res.status_code == 200:
                    print(
                        f"Completed check run '{CHECK_RUN_NAME}' (ID: {existing_check_run_id}) "
                        f"with conclusion: {conclusion}."
                    )
                    sys.exit(0)
                else:
                    print(
                        f"Warning: PATCH check run failed (HTTP {res.status_code}), attempting POST...",
                        file=sys.stderr,
                    )
            except Exception as exc:
                print(f"Warning: Network error updating check run: {exc}", file=sys.stderr)

        # Fallback to POST
        post_url = f"{api_base}/check-runs"
        try:
            res = requests.post(post_url, json=payload, headers=headers, timeout=30)
            if res.status_code in (200, 201):
                data = res.json()
                print(
                    f"Created completed check run '{CHECK_RUN_NAME}' (ID: {data.get('id')}) "
                    f"with conclusion: {conclusion}."
                )
                sys.exit(0)
            else:
                print(
                    f"Warning: Failed to create completed check run (HTTP {res.status_code}): {res.text}",
                    file=sys.stderr,
                )
        except Exception as exc:
            print(f"Warning: Network error creating completed check run: {exc}", file=sys.stderr)

        sys.exit(0)


if __name__ == "__main__":
    main()
