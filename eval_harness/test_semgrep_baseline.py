"""Windows-compatible unit tests for the Semgrep-only parser and file scoring."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any

from eval_harness.semgrep_baseline import (
    CWES,
    parse_cwe_metadata,
    parse_semgrep_payload,
    score_file_level,
)
from eval_harness.prepare_semgrep_manifest import has_java_code

HERE = Path(__file__).resolve().parent


class SemgrepBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest: list[dict[str, Any]] = json.loads(
            (HERE / "manifest_semgrep.json").read_text(encoding="utf-8")
        )

    def test_cwe_parsing_reads_rule_metadata_only(self) -> None:
        self.assertEqual(parse_cwe_metadata("CWE-89: SQL Injection"), ["CWE-89"])
        self.assertEqual(parse_cwe_metadata(["CWE-79: XSS", "related CWE-89"]), ["CWE-79", "CWE-89"])
        self.assertEqual(parse_cwe_metadata(None), [])

    def test_untagged_findings_are_counted_and_not_guessed_from_message(self) -> None:
        payload = {
            "results": [
                {
                    "check_id": "test.rule",
                    "path": "src/A.java",
                    "start": {"line": 4},
                    "extra": {
                        "message": "CWE-89 SQL injection pattern",
                        "metadata": {},
                    },
                },
                {
                    "check_id": "tagged.rule",
                    "path": "src/B.java",
                    "start": {"line": 9},
                    "extra": {
                        "message": "Finding",
                        "metadata": {"cwe": "CWE-330: Weak PRNG"},
                    },
                },
            ]
        }
        parsed = parse_semgrep_payload(payload)
        self.assertTrue(parsed[0]["untagged"])
        self.assertEqual(parsed[0]["cwes"], [])
        self.assertFalse(parsed[1]["untagged"])
        self.assertEqual(parsed[1]["cwes"], ["CWE-330"])

    def test_file_level_confusion_and_benchmark_score(self) -> None:
        manifest = [
            {"id": "vuln-hit", "cwe": "CWE-89", "label": "vulnerable", "file": "A.java"},
            {"id": "vuln-miss", "cwe": "CWE-89", "label": "vulnerable", "file": "B.java"},
            {"id": "safe-fp", "cwe": "CWE-89", "label": "safe", "file": "C.java"},
            {"id": "safe-tn", "cwe": "CWE-89", "label": "safe", "file": "D.java"},
        ]
        findings = {
            "vuln-hit": [{"cwes": ["CWE-89"]}],
            "vuln-miss": [{"cwes": []}],
            "safe-fp": [{"cwes": ["CWE-89"]}],
            "safe-tn": [],
        }
        result = score_file_level(manifest, findings)["CWE-89"]
        self.assertEqual((result["tp"], result["fp"], result["fn"], result["tn"]), (1, 1, 1, 1))
        self.assertEqual(result["n"], 4)
        self.assertEqual(result["precision"], 0.5)
        self.assertEqual(result["recall"], 0.5)
        self.assertEqual(result["f1"], 0.5)
        self.assertEqual(result["tpr"], 0.5)
        self.assertEqual(result["fpr"], 0.5)
        self.assertEqual(result["benchmark_score"], 0.0)

    def test_manifest_has_balanced_top_four_cwes_and_real_code_diffs(self) -> None:
        self.assertEqual({row["cwe"] for row in self.manifest}, set(CWES))
        for cwe in CWES:
            rows = [row for row in self.manifest if row["cwe"] == cwe]
            self.assertEqual(sum(row["label"] == "vulnerable" for row in rows), 50)
            self.assertEqual(sum(row["label"] == "safe" for row in rows), 50)
        for row in self.manifest:
            diff = (HERE / row["diff_path"]).read_text(encoding="utf-8")
            self.assertIn("+++ b/", diff, row["id"])
            self.assertTrue(has_java_code(diff), f"Comment-only or empty diff: {row['id']}")


if __name__ == "__main__":
    unittest.main()
