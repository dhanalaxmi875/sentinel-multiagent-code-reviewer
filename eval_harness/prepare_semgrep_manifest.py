"""Create a fixed-seed, balanced OWASP Java subset with complete-source diffs."""

from __future__ import annotations

import argparse
import csv
import difflib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
DEFAULT_DATASET = HERE / "datasets" / "OWASP-Benchmark"
DEFAULT_MANIFEST = HERE / "manifest_semgrep.json"
DIFF_DIR = HERE / "semgrep_diffs"
CWES = ("CWE-89", "CWE-330", "CWE-79", "CWE-22")
SEED = 20261101


def has_java_code(diff_text: str) -> bool:
    """Return true when a new-file diff contains at least one non-comment code line."""
    added: list[str] = []
    in_hunk = False
    for line in diff_text.splitlines():
        if line.startswith("@@"):
            in_hunk = True
            continue
        if not in_hunk or line.startswith("+++"):
            continue
        if line.startswith("+"):
            added.append(line[1:].strip())
    for line in added:
        if not line or line.startswith(("//", "/*", "*", "*/")):
            continue
        if line.startswith(("package ", "import ", "@")):
            continue
        return True
    return False


def _source_path(dataset_dir: Path, sample_name: str) -> Path:
    return (
        dataset_dir
        / "src"
        / "main"
        / "java"
        / "org"
        / "owasp"
        / "benchmark"
        / "testcode"
        / f"{sample_name}.java"
    )


def _new_file_diff(relative_path: str, source: str) -> str:
    source_lines = source.splitlines(keepends=True)
    if source and not source.endswith("\n"):
        source_lines[-1] += "\n"
    body = "".join(
        difflib.unified_diff([], source_lines, fromfile="/dev/null", tofile=f"b/{relative_path}")
    )
    diff = f"diff --git a/{relative_path} b/{relative_path}\nnew file mode 100644\n{body}"
    if not has_java_code(diff):
        raise ValueError(f"Java source has no non-comment code lines: {relative_path}")
    return diff


def build_manifest(
    dataset_dir: Path = DEFAULT_DATASET,
    manifest_path: Path = DEFAULT_MANIFEST,
    seed: int = SEED,
    per_label_cap: int = 50,
) -> list[dict[str, Any]]:
    csv_path = dataset_dir / "expectedresults-1.2.csv"
    if not csv_path.is_file():
        raise FileNotFoundError(
            f"OWASP Benchmark expected-results CSV not found: {csv_path}. "
            "Provide --dataset-dir containing expectedresults-1.2.csv and the Java sources."
        )

    grouped: dict[str, dict[str, list[dict[str, str]]]] = defaultdict(
        lambda: {"vulnerable": [], "safe": []}
    )
    with csv_path.open(newline="", encoding="utf-8") as stream:
        for row in csv.reader(stream):
            if not row or row[0].lstrip().startswith("#") or len(row) < 4:
                continue
            try:
                cwe = f"CWE-{int(row[3])}"
            except ValueError:
                continue
            if cwe not in CWES:
                continue
            label = "vulnerable" if row[2].strip().lower() == "true" else "safe"
            grouped[cwe][label].append({"test_name": row[0].strip(), "label": label})

    absent = [cwe for cwe in CWES if cwe not in grouped]
    if absent:
        raise ValueError(f"Required OWASP CWEs missing from CSV: {', '.join(absent)}")

    chooser = random.Random(seed)
    records: list[dict[str, Any]] = []
    placeholder_replacements = 0
    DIFF_DIR.mkdir(parents=True, exist_ok=True)
    for cwe in CWES:
        vulnerable = sorted(grouped[cwe]["vulnerable"], key=lambda row: row["test_name"])
        safe = sorted(grouped[cwe]["safe"], key=lambda row: row["test_name"])
        balanced_n = min(per_label_cap, len(vulnerable), len(safe))
        if balanced_n == 0:
            raise ValueError(
                f"{cwe} cannot be balanced: vulnerable={len(vulnerable)}, safe={len(safe)}"
            )
        chosen = chooser.sample(vulnerable, balanced_n) + chooser.sample(safe, balanced_n)
        for row in chosen:
            test_name = row["test_name"]
            source_path = _source_path(dataset_dir, test_name)
            if not source_path.is_file():
                raise FileNotFoundError(f"OWASP Java source missing for {test_name}: {source_path}")
            relative_file = f"src/main/java/org/owasp/benchmark/testcode/{test_name}.java"
            diff_text = _new_file_diff(relative_file, source_path.read_text(encoding="utf-8"))
            sample_id = f"owasp_{test_name}"
            old_diff = HERE / "diffs" / f"{sample_id}.diff"
            if old_diff.is_file() and not has_java_code(old_diff.read_text(encoding="utf-8")):
                placeholder_replacements += 1
            diff_path = DIFF_DIR / f"{sample_id}.diff"
            diff_path.write_text(diff_text, encoding="utf-8", newline="")
            records.append(
                {
                    "id": sample_id,
                    "dataset": "owasp_benchmark",
                    "language": "java",
                    "file": relative_file,
                    "diff_path": diff_path.relative_to(HERE).as_posix(),
                    "label": row["label"],
                    "cwe": cwe,
                    "line_range": None,
                    "seed": seed,
                }
            )

    records.sort(key=lambda row: (CWES.index(row["cwe"]), row["label"], row["id"]))
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")

    counts = Counter((row["cwe"], row["label"]) for row in records)
    print(
        f"Seed: {seed}; total samples: {len(records)}; "
        f"placeholder diffs replaced in manifest: {placeholder_replacements}"
    )
    for cwe in CWES:
        print(
            f"{cwe}: vulnerable={counts[(cwe, 'vulnerable')]}, "
            f"safe={counts[(cwe, 'safe')]}, total="
            f"{counts[(cwe, 'vulnerable')] + counts[(cwe, 'safe')] }"
        )
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--per-label-cap", type=int, default=50)
    args = parser.parse_args()
    if args.per_label_cap < 1:
        parser.error("--per-label-cap must be positive")
    build_manifest(args.dataset_dir, args.manifest, args.seed, args.per_label_cap)


if __name__ == "__main__":
    main()
