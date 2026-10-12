"""Simple keyword-based eval runner.

Usage:
    python -m evals.run_eval

Scoring:
  Each case passes if:
    1. Every `must_mention` group has at least one matching keyword in the review.
    2. No `must_not` keyword appears in the review.

  Final score is reported as X/N cases passed.
"""

import sys

from dotenv import load_dotenv

load_dotenv()

from evals.cases import CASES
from src.main import run_review

_SEPARATOR_WIDTH = 55


def _check(review: str, case: dict) -> tuple[bool, list[str]]:
    """Return (passed, list_of_failure_reasons)."""
    review_lower = review.lower()
    failures = []

    for group in case.get("must_mention", []):
        if not any(kw.lower() in review_lower for kw in group):
            failures.append(f"Missing any of: {group}")

    for forbidden in case.get("must_not", []):
        if forbidden.lower() in review_lower:
            failures.append(f"Should not mention: '{forbidden}'")

    return len(failures) == 0, failures


def run() -> None:
    """Run all eval cases and report a pass/fail score."""
    results = []

    for case in CASES:
        print(f"\n{'=' * _SEPARATOR_WIDTH}")
        print(f"Running: {case['name']}")
        print("=" * _SEPARATOR_WIDTH)

        review = run_review(case["diff"], case["file_paths"])
        case_passed, failures = _check(review, case)

        print(review)
        print()
        if case_passed:
            print(f"[PASS] {case['name']}")
        else:
            print(f"[FAIL] {case['name']}")
            for reason in failures:
                print(f"       - {reason}")

        results.append({"name": case["name"], "passed": case_passed, "failures": failures})

    total = len(results)
    n_passed = sum(1 for r in results if r["passed"])

    print(f"\n{'=' * _SEPARATOR_WIDTH}")
    print(f"Eval complete: {n_passed}/{total} cases passed")
    print("=" * _SEPARATOR_WIDTH)
    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"  [{status}] {r['name']}")

    sys.exit(0 if n_passed == total else 1)


if __name__ == "__main__":
    run()
