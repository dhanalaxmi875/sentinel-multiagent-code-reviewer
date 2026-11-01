"""Run and score a file-level Semgrep-only OWASP Benchmark Java baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import time
import uuid
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DEFAULT_MANIFEST = HERE / "manifest_semgrep.json"
OUTPUT_DIR = HERE / "results" / "semgrep_only"
RAW_DIR = OUTPUT_DIR / "raw"
CWES = ("CWE-89", "CWE-330", "CWE-79", "CWE-22")
RULE_SETS = ("p/java", "p/owasp-top-ten")
CWE_PATTERN = re.compile(r"\bCWE-(\d+)\b", re.IGNORECASE)


def log(message: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).isoformat(timespec="seconds")
    line = f"{stamp} {message}"
    print(line, flush=True)
    with (OUTPUT_DIR / "run.log").open("a", encoding="utf-8") as stream:
        stream.write(line + "\n")


def parse_cwe_metadata(value: Any) -> list[str]:
    """Extract only explicit CWE identifiers from the rule metadata cwe field."""
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, list):
        values = [item for item in value if isinstance(item, str)]
    else:
        values = []
    found: list[str] = []
    for item in values:
        for match in CWE_PATTERN.finditer(item):
            cwe = f"CWE-{int(match.group(1))}"
            if cwe not in found:
                found.append(cwe)
    return found


def parse_semgrep_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize Semgrep JSON results without guessing missing CWE metadata."""
    normalized: list[dict[str, Any]] = []
    results = payload.get("results", [])
    if not isinstance(results, list):
        raise ValueError("Semgrep JSON field 'results' must be a list")
    for raw in results:
        if not isinstance(raw, dict):
            continue
        extra = raw.get("extra") if isinstance(raw.get("extra"), dict) else {}
        metadata = extra.get("metadata") if isinstance(extra.get("metadata"), dict) else {}
        cwes = parse_cwe_metadata(metadata.get("cwe"))
        start = raw.get("start") if isinstance(raw.get("start"), dict) else {}
        normalized.append(
            {
                "rule_id": str(raw.get("check_id", "unknown")),
                "path": str(raw.get("path", "")),
                "line": start.get("line") if isinstance(start.get("line"), int) else None,
                "message": str(extra.get("message", "")),
                "severity": str(extra.get("severity", "")),
                "cwes": cwes,
                "untagged": not cwes,
            }
        )
    return normalized


def has_code_line(diff_text: str) -> bool:
    """True if the unified diff adds a non-comment Java source line."""
    try:
        from .prepare_semgrep_manifest import has_java_code
    except ImportError:
        from prepare_semgrep_manifest import has_java_code

    return has_java_code(diff_text)


def source_from_new_file_diff(diff_text: str) -> str:
    lines: list[str] = []
    in_hunk = False
    for line in diff_text.splitlines():
        if line.startswith("@@"):
            in_hunk = True
            continue
        if not in_hunk or line.startswith("+++"):
            continue
        if line.startswith("+"):
            lines.append(line[1:])
        elif line.startswith(" "):
            lines.append(line[1:])
        elif line.startswith("-"):
            continue
    if not lines:
        raise ValueError("No source lines were found in the unified diff")
    source = "\n".join(lines) + "\n"
    if not has_code_line(diff_text):
        raise ValueError("Diff contains only comments/declarations, not Java code")
    return source


def score_file_level(
    manifest: list[dict[str, Any]], findings_by_sample: dict[str, list[dict[str, Any]]]
) -> dict[str, dict[str, float | int]]:
    """Score one binary prediction per source file and its labeled category CWE."""
    counters: dict[str, Counter[str]] = {cwe: Counter() for cwe in CWES}
    for sample in manifest:
        cwe = sample["cwe"]
        label = sample["label"]
        predicted = any(cwe in finding.get("cwes", []) for finding in findings_by_sample.get(sample["id"], []))
        positive = label == "vulnerable"
        if positive and predicted:
            counters[cwe]["tp"] += 1
        elif positive:
            counters[cwe]["fn"] += 1
        elif predicted:
            counters[cwe]["fp"] += 1
        else:
            counters[cwe]["tn"] += 1
        counters[cwe]["n"] += 1

    metrics: dict[str, dict[str, float | int]] = {}
    for cwe, counts in counters.items():
        if counts["n"] == 0:
            continue
        tp, fp, fn, tn = (counts[key] for key in ("tp", "fp", "fn", "tn"))
        precision = tp / (tp + fp) if tp + fp else 0.0
        tpr = tp / (tp + fn) if tp + fn else 0.0
        fpr = fp / (fp + tn) if fp + tn else 0.0
        f1 = 2 * precision * tpr / (precision + tpr) if precision + tpr else 0.0
        metrics[cwe] = {
            "n": counts["n"], "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": precision, "recall": tpr, "f1": f1,
            "tpr": tpr, "fpr": fpr, "benchmark_score": tpr - fpr,
        }
    return metrics


def _source_path_for_sample(scan_root: Path, sample: dict[str, Any]) -> Path:
    return scan_root / f"{sample['id']}.java"


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_manifest(path: Path) -> list[dict[str, Any]]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, list):
        raise ValueError("Manifest must be a JSON list")
    for sample in manifest:
        if sample.get("language") != "java" or sample.get("cwe") not in CWES:
            raise ValueError(f"Unexpected non-Java or unsupported CWE sample: {sample.get('id')}")
        if sample.get("label") not in {"safe", "vulnerable"}:
            raise ValueError(f"Unexpected label in sample: {sample.get('id')}")
        diff_path = HERE / sample["diff_path"]
        diff_text = diff_path.read_text(encoding="utf-8")
        if not has_code_line(diff_text):
            raise ValueError(f"Sample diff is comment-only or empty: {diff_path}")
    return manifest


def _existing_record(sample: dict[str, Any], semgrep_version: str, resume: bool) -> dict[str, Any] | None:
    if not resume:
        return None
    record_path = RAW_DIR / f"{sample['id']}.json"
    try:
        record = json.loads(record_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    diff_text = (HERE / sample["diff_path"]).read_text(encoding="utf-8")
    if (
        record.get("status") == "done"
        and record.get("source_sha256") == _sha256(source_from_new_file_diff(diff_text))
        and record.get("semgrep_version") == semgrep_version
        and record.get("rule_sets") == list(RULE_SETS)
    ):
        return record
    return None


def _run_batch(pending: list[dict[str, Any]], semgrep_command: str, version: str) -> tuple[dict[str, list[dict[str, Any]]], dict[str, str], float]:
    findings_by_sample: dict[str, list[dict[str, Any]]] = {sample["id"]: [] for sample in pending}
    failures: dict[str, str] = {}
    if not pending:
        return findings_by_sample, failures, 0.0

    with tempfile.TemporaryDirectory(prefix="sentinel-semgrep-") as temporary:
        scan_root = Path(temporary) / "sources"
        scan_root.mkdir(parents=True)
        source_hashes: dict[str, str] = {}
        path_to_sample: dict[str, str] = {}
        for sample in pending:
            diff_text = (HERE / sample["diff_path"]).read_text(encoding="utf-8")
            source = source_from_new_file_diff(diff_text)
            source_path = _source_path_for_sample(scan_root, sample)
            source_path.write_text(source, encoding="utf-8", newline="")
            source_hashes[sample["id"]] = _sha256(source)
            path_to_sample[source_path.resolve().as_posix()] = sample["id"]

        command = [semgrep_command, "scan"]
        for rules in RULE_SETS:
            command.extend(("--config", rules))
        command.extend(("--metrics=off", "--json", "--no-git-ignore", str(scan_root)))
        log(f"Running one Semgrep batch over {len(pending)} Java files: {' '.join(command[:7])} …")
        started = time.perf_counter()
        process = subprocess.run(command, capture_output=True, text=True, check=False)
        batch_elapsed = time.perf_counter() - started

        try:
            payload = json.loads(process.stdout)
            if not isinstance(payload, dict):
                raise ValueError("Semgrep JSON output is not an object")
        except (json.JSONDecodeError, ValueError) as error:
            message = (
                f"Semgrep failed (exit={process.returncode}) and returned no usable JSON: {error}. "
                f"stderr: {(process.stderr or '').strip()[-3000:]}"
            )
            failures.update({sample["id"]: message for sample in pending})
            return findings_by_sample, failures, batch_elapsed
        if process.returncode not in (0, 1):
            message = (
                f"Semgrep returned exit code {process.returncode}. "
                f"stderr: {(process.stderr or '').strip()[-3000:]}"
            )
            failures.update({sample["id"]: message for sample in pending})
            return findings_by_sample, failures, batch_elapsed

        path_lookup = {key.replace("\\", "/"): value for key, value in path_to_sample.items()}
        basename_lookup = {Path(path).name: sample_id for path, sample_id in path_to_sample.items()}
        for finding in parse_semgrep_payload(payload):
            reported = finding.get("path", "").replace("\\", "/")
            sample_id = path_lookup.get(reported)
            if sample_id is None:
                try:
                    resolved = Path(reported).resolve().as_posix()
                except OSError:
                    resolved = reported
                sample_id = path_to_sample.get(resolved)
            if sample_id is None:
                sample_id = basename_lookup.get(Path(reported).name)
            if sample_id is not None:
                findings_by_sample[sample_id].append(finding)

        for error in payload.get("errors", []):
            if not isinstance(error, dict):
                continue
            path_value = error.get("path")
            if not path_value:
                continue
            error_path = str(path_value).replace("\\", "/")
            sample_id = path_lookup.get(error_path)
            if sample_id is None:
                sample_id = basename_lookup.get(Path(error_path).name)
            if sample_id:
                failures[sample_id] = str(error.get("message", "Semgrep file error"))

        for sample in pending:
            sample_id = sample["id"]
            if sample_id in failures:
                continue
            RAW_DIR.mkdir(parents=True, exist_ok=True)
            record = {
                "id": sample_id,
                "status": "done",
                "sample": sample,
                "semgrep_version": version,
                "rule_sets": list(RULE_SETS),
                "source_sha256": source_hashes[sample_id],
                "findings": findings_by_sample[sample_id],
                "untagged_findings": sum(item["untagged"] for item in findings_by_sample[sample_id]),
                "batch_elapsed_s": batch_elapsed,
                "batch_sample_count": len(pending),
            }
            (RAW_DIR / f"{sample_id}.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
            log(f"Saved {sample_id}: {len(findings_by_sample[sample_id])} findings; batch {batch_elapsed:.3f}s")

    for sample_id, message in failures.items():
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        record = {"id": sample_id, "status": "failed", "error": message, "findings": [], "semgrep_version": version, "rule_sets": list(RULE_SETS), "batch_elapsed_s": batch_elapsed, "batch_sample_count": len(pending)}
        (RAW_DIR / f"{sample_id}.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        log(f"Failed {sample_id}: {message}")
    return findings_by_sample, failures, batch_elapsed


def _measure_version(semgrep_command: str) -> str:
    process = subprocess.run([semgrep_command, "--version"], capture_output=True, text=True, check=False)
    if process.returncode != 0 or not process.stdout.strip():
        raise RuntimeError(f"Could not read Semgrep version: {process.stderr.strip()}")
    return process.stdout.strip()


def _write_outputs(manifest: list[dict[str, Any]], semgrep_version: str, batch_elapsed: float, batch_count: int, failed: dict[str, str]) -> None:
    import csv

    sys.path.insert(0, str(ROOT))
    from eval_harness.metrics import compute_metrics

    completed: list[dict[str, Any]] = []
    findings_by_sample: dict[str, list[dict[str, Any]]] = {}
    statuses: dict[str, str] = {}
    for sample in manifest:
        path = RAW_DIR / f"{sample['id']}.json"
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            statuses[sample["id"]] = "not_run"
            continue
        status = record.get("status", "failed")
        statuses[sample["id"]] = status
        if status == "done":
            completed.append(sample)
            findings_by_sample[sample["id"]] = record.get("findings", [])

    # Existing metrics.py is the source of truth for confusion counts and micro/macro formulas.
    predicted_by_sample = {
        sample_id: ([{"cwe": sample_cwe, "file": manifest_item["file"]}] if any(sample_cwe in finding.get("cwes", []) for finding in findings) else [])
        for sample_id, findings in findings_by_sample.items()
        for manifest_item in manifest if manifest_item["id"] == sample_id
        for sample_cwe in [manifest_item["cwe"]]
    }
    metric_input = [sample for sample in completed]
    metrics = compute_metrics(metric_input, predicted_by_sample) if metric_input else {"per_cwe": {}, "overall": {}, "macro_avg": {}}

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with (OUTPUT_DIR / "summary_per_cwe.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["cwe", "n", "tp", "fp", "fn", "tn", "precision", "recall", "f1", "tpr", "fpr", "benchmark_score", "findings_total", "untagged_findings"])
        for cwe in CWES:
            result = metrics["per_cwe"].get(cwe)
            if not result:
                writer.writerow([cwe, 0, "", "", "", "", "", "", "", "", "", "", 0, 0])
                continue
            cwe_samples = [sample for sample in completed if sample["cwe"] == cwe]
            cwe_findings = [finding for sample in cwe_samples for finding in findings_by_sample[sample["id"]]]
            untagged = sum(not finding.get("cwes") for finding in cwe_findings)
            writer.writerow([cwe, len(cwe_samples), result["tp"], result["fp"], result["fn"], result["tn"], result["precision"], result["recall"], result["f1"], result["recall"], result["fp"] / (result["fp"] + result["tn"]) if result["fp"] + result["tn"] else 0.0, result["recall"] - (result["fp"] / (result["fp"] + result["tn"]) if result["fp"] + result["tn"] else 0.0), len(cwe_findings), untagged])

    overall = metrics["overall"] if metrics["overall"] else None
    with (OUTPUT_DIR / "summary_overall.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["metric", "n", "tp", "fp", "fn", "tn", "micro_precision", "micro_recall", "micro_f1", "micro_tpr", "micro_fpr", "micro_benchmark_score", "macro_precision", "macro_recall", "macro_f1", "macro_tpr", "macro_fpr", "macro_benchmark_score", "findings_total", "findings_per_sample", "untagged_findings", "failed_samples", "batch_elapsed_s"])
        if overall:
            total_findings = sum(len(items) for items in findings_by_sample.values())
            untagged = sum(not item.get("cwes") for items in findings_by_sample.values() for item in items)
            n = len(completed)
            fpr = overall["fp"] / (overall["fp"] + overall["tn"]) if overall["fp"] + overall["tn"] else 0.0
            macro = metrics["macro_avg"]
            cwe_rows = [metrics["per_cwe"][cwe] for cwe in CWES if cwe in metrics["per_cwe"]]
            macro_fpr = sum((row["fp"] / (row["fp"] + row["tn"])) if row["fp"] + row["tn"] else 0.0 for row in cwe_rows) / len(cwe_rows) if cwe_rows else 0.0
            writer.writerow(["completed samples", n, overall["tp"], overall["fp"], overall["fn"], overall["tn"], overall["precision"], overall["recall"], overall["f1"], overall["recall"], fpr, overall["recall"] - fpr, macro["precision"], macro["recall"], macro["f1"], macro["recall"], macro_fpr, macro["recall"] - macro_fpr, total_findings, total_findings / n if n else "", untagged, len(failed), batch_elapsed])
        else:
            writer.writerow(["no completed samples", 0, "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", 0, "", 0, len(failed), batch_elapsed])

    with (OUTPUT_DIR / "timings.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["sample_id", "cwe", "label", "status", "sample_elapsed_s", "batch_elapsed_s", "batch_sample_count", "error"])
        for sample in manifest:
            try:
                record = json.loads((RAW_DIR / f"{sample['id']}.json").read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                record = {}
            writer.writerow([sample["id"], sample["cwe"], sample["label"], statuses.get(sample["id"], "not_run"), "", record.get("batch_elapsed_s", ""), record.get("batch_sample_count", ""), record.get("error", "")])

    _write_plots(metrics)
    _write_summary(manifest, completed, findings_by_sample, statuses, failed, metrics, semgrep_version, batch_elapsed, batch_count)


def _write_plots(metrics: dict[str, Any]) -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(7, 6), facecolor="#111318")
    ax.set_facecolor("#111318")
    labels = ("TP", "FN", "FP", "TN")
    overall = metrics.get("overall", {})
    counts = [int(overall.get(key.lower(), 0)) for key in labels]
    grid = np.array([[counts[0], counts[1]], [counts[2], counts[3]]])
    image = ax.imshow(grid, cmap="magma", interpolation="nearest")
    ax.set_xticks([0, 1], ["Predicted vulnerable", "Predicted safe"])
    ax.set_yticks([0, 1], ["Actual vulnerable", "Actual safe"])
    ax.set_title("OWASP Benchmark file-level confusion matrix")
    for row in range(2):
        for col in range(2):
            name = (("TP", "FN"), ("FP", "TN"))[row][col]
            ax.text(col, row, f"{name}\n{grid[row, col]}", ha="center", va="center", color="white", fontsize=14)
    fig.colorbar(image, ax=ax, label="Files")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "confusion_matrix.png", dpi=160, facecolor=fig.get_facecolor())
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5), facecolor="#111318")
    ax.set_facecolor("#111318")
    cwes = [cwe for cwe in CWES if cwe in metrics.get("per_cwe", {})]
    values = [metrics["per_cwe"][cwe]["f1"] for cwe in cwes]
    bars = ax.bar(cwes, values, color="#8b5cf6")
    ax.set_ylim(0, 1)
    ax.set_ylabel("F1")
    ax.set_title("Semgrep-only F1 by CWE (file-level)")
    ax.grid(axis="y", alpha=0.2)
    for bar, cwe in zip(bars, cwes):
        row = metrics["per_cwe"][cwe]
        n = row["vulnerable_samples"] + row["safe_samples"]
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{row['f1']:.4f}\nn={n}", ha="center", va="bottom")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "f1_by_cwe.png", dpi=160, facecolor=fig.get_facecolor())
    plt.close(fig)


def _write_summary(manifest: list[dict[str, Any]], completed: list[dict[str, Any]], findings_by_sample: dict[str, list[dict[str, Any]]], statuses: dict[str, str], failed: dict[str, str], metrics: dict[str, Any], version: str, batch_elapsed: float, batch_count: int) -> None:
    import subprocess

    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False).stdout.strip() or "unknown"
    untagged = sum(not finding.get("cwes") for findings in findings_by_sample.values() for finding in findings)
    records = [
        "# Semgrep-only OWASP Benchmark Java baseline",
        "",
        f"- Date: {datetime.now(UTC).date().isoformat()}",
        f"- Git commit: `{commit}`",
        f"- Semgrep version: `{version}`",
        f"- Rule sets: `{', '.join(RULE_SETS)}`",
        "- `semgrep_rules/` was inspected; its only rule targets Python, so it is not included in this Java scan.",
        f"- Rule pack registry access: required for uncached `p/java` and `p/owasp-top-ten` packs.",
        f"- Fixed-seed subset: seed `{manifest[0]['seed'] if manifest else 'n/a'}`; total selected `{len(manifest)}`; maximum 50 vulnerable + 50 safe per CWE.",
        f"- Completed files: `{len(completed)}` / `{len(manifest)}`; failed files: `{len(failed)}`; untagged findings (not assigned a CWE): `{untagged}`.",
        f"- Semgrep invocation: one batch over `{batch_count}` pending Java files; measured batch wall time `{batch_elapsed:.6f}` seconds.",
        "- Per-file scan durations are not exposed by this single batch JSON run. Per-file mean/median/std are therefore unavailable; `timings.csv` leaves `sample_elapsed_s` blank instead of dividing the batch time across files.",
        "- Scoring is file-level: a sample is predicted vulnerable only when a finding in that file has an explicit rule metadata CWE equal to the sample's category CWE. The Benchmark expected-results CSV has no line ranges.",
        "",
        "## Overall metrics",
        "",
        "| n files | TP | FP | FN | TN | Micro precision | Micro recall | Micro F1 | Micro TPR | Micro FPR | Micro Benchmark score (TPR−FPR) | Macro precision | Macro recall | Macro F1 | Macro TPR | Macro FPR | Macro Benchmark score |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    overall = metrics.get("overall", {})
    if overall:
        fpr = overall["fp"] / (overall["fp"] + overall["tn"]) if overall["fp"] + overall["tn"] else 0.0
        macro = metrics["macro_avg"]
        rows = [metrics["per_cwe"][cwe] for cwe in CWES if cwe in metrics["per_cwe"]]
        macro_fpr = sum((r["fp"] / (r["fp"] + r["tn"])) if r["fp"] + r["tn"] else 0.0 for r in rows) / len(rows) if rows else 0.0
        records.append(f"| {len(completed)} | {overall['tp']} | {overall['fp']} | {overall['fn']} | {overall['tn']} | {overall['precision']:.6f} | {overall['recall']:.6f} | {overall['f1']:.6f} | {overall['recall']:.6f} | {fpr:.6f} | {overall['recall'] - fpr:.6f} | {macro['precision']:.6f} | {macro['recall']:.6f} | {macro['f1']:.6f} | {macro['recall']:.6f} | {macro_fpr:.6f} | {macro['recall'] - macro_fpr:.6f} |")
    else:
        records.append("No completed files; metrics are unavailable.")
    records.extend([
        "",
        "## Per-CWE metrics",
        "",
        "| CWE | n files | TP | FP | FN | TN | Precision | Recall / TPR | F1 | FPR | Benchmark score (TPR−FPR) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for cwe in CWES:
        row = metrics.get("per_cwe", {}).get(cwe)
        if not row:
            records.append(f"| {cwe} | 0 | — | — | — | — | — | — | — | — | — |")
            continue
        fpr = row["fp"] / (row["fp"] + row["tn"]) if row["fp"] + row["tn"] else 0.0
        n = row["vulnerable_samples"] + row["safe_samples"]
        records.append(f"| {cwe} | {n} | {row['tp']} | {row['fp']} | {row['fn']} | {row['tn']} | {row['precision']:.6f} | {row['recall']:.6f} | {row['f1']:.6f} | {fpr:.6f} | {row['recall'] - fpr:.6f} |")
    records.extend(["", "## Findings and run timing", "", f"- Tagged + untagged Semgrep findings across completed files: `{sum(len(items) for items in findings_by_sample.values())}` (n=`{len(completed)}` files).", f"- Findings without a CWE tag: `{untagged}`. They remain untagged, are excluded from CWE predictions, and are not guessed.", f"- Batch wall time: `{batch_elapsed:.6f}` seconds for `{batch_count}` pending files. Per-file mean/median/std are unavailable from one batch invocation.", "- Failed samples:"])
    if failed:
        records.extend(f"  - `{sample_id}`: {message}" for sample_id, message in sorted(failed.items()))
    else:
        records.append("  - None.")
    records.extend([
        "",
        "## Limitations",
        "",
        "- This is a small subset of the OWASP Benchmark, Java only.",
        "- Results describe Semgrep alone, not the SentinelCode multi-agent pipeline.",
        "- Matching is file-level because the Benchmark expected-results CSV has no line ranges.",
        "- CWE mapping uses only explicit Semgrep rule metadata; untagged findings are counted separately and never inferred.",
        "- Registry rule packs require internet access when not already cached.",
        "- Per-file runtimes cannot be derived from this one-process batch output; only actual batch wall time is reported.",
    ])
    (OUTPUT_DIR / "results_summary.md").write_text("\n".join(records) + "\n", encoding="utf-8")


def run(manifest_path: Path, semgrep_command: str, resume: bool) -> None:
    manifest = _load_manifest(manifest_path)
    version = _measure_version(semgrep_command)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    records = {sample["id"]: _existing_record(sample, version, resume) for sample in manifest}
    pending = [sample for sample in manifest if records[sample["id"]] is None]
    log(f"Semgrep version={version}; rule sets={list(RULE_SETS)}; selected={len(manifest)}; pending={len(pending)}; resume={resume}")
    _, failed, batch_elapsed = _run_batch(pending, semgrep_command, version)
    meta = {
        "semgrep_version": version,
        "rule_sets": list(RULE_SETS),
        "manifest_path": str(manifest_path.relative_to(HERE)) if manifest_path.is_relative_to(HERE) else str(manifest_path),
        "selected_samples": len(manifest),
        "batch_samples": len(pending),
        "batch_elapsed_s": batch_elapsed,
        "batch_id": str(uuid.uuid4()),
        "failed": failed,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    (OUTPUT_DIR / "run_metadata.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    _write_outputs(manifest, version, batch_elapsed, len(pending), failed)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--semgrep-command", default="semgrep")
    parser.add_argument("--resume", action="store_true", help="Reuse completed sample records with matching input hash, version, and rule sets")
    args = parser.parse_args()
    try:
        run(args.manifest.resolve(), args.semgrep_command, args.resume)
    except Exception as error:
        log(f"Run did not complete: {error.__class__.__name__}: {error}")
        raise


if __name__ == "__main__":
    main()
