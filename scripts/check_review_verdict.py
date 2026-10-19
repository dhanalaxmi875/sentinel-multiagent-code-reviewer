"""Check SentinelCode review verdict and set process exit code accordingly."""

import argparse
from pathlib import Path
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect SentinelCode review report and determine CI check outcome."
    )
    parser.add_argument(
        "--report-file",
        required=True,
        help="Path to the Markdown review report file",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    report_path = Path(args.report_file)
    if not report_path.is_file():
        print(
            f"Error: Report file '{args.report_file}' does not exist or is not a valid file.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        report_text = report_path.read_text(encoding="utf-8")
    except Exception as exc:
        print(f"Error reading report file '{args.report_file}': {exc}", file=sys.stderr)
        sys.exit(1)

    # Search for the verdict specifically under ### Verdict if present
    import re
    verdict_match = re.search(r"### Verdict\s*\n+([^\n]+)", report_text, flags=re.IGNORECASE)
    verdict_target = verdict_match.group(1).upper() if verdict_match else report_text.upper()

    if "REQUEST CHANGES" in verdict_target:
        print("Verdict: REQUEST CHANGES")
        print("SentinelCode detected issues requiring changes before merge. Failing check.")
        sys.exit(1)
    elif "APPROVE" in verdict_target:
        print("Verdict: APPROVE")
        print("SentinelCode review approved. Passing check.")
        sys.exit(0)
    else:
        print(
            "Error: Incomplete review report. Neither 'REQUEST CHANGES' nor 'APPROVE' was found.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
