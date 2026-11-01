"""Reproducible small local OWASP run; does not change the normal pipeline."""

from __future__ import annotations

import argparse
import csv
import difflib
import json
import logging
import os
import random
import re
import statistics
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATASET = HERE / "datasets" / "OWASP-Benchmark"
SOURCE_ROOT = DATASET / "src" / "main" / "java" / "org" / "owasp" / "benchmark" / "testcode"
LOCAL = HERE / "results" / "local"
MANIFEST = HERE / "manifest_local.json"
SEED = 20261101
TIMEOUT_S = 900
MODEL = "qwen2.5-coder:14b"
LOG = LOCAL / "run.log"
CWE_ORDER = ("CWE-89", "CWE-330", "CWE-79")


def log(message: str) -> None:
    LOCAL.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).isoformat(timespec="seconds")
    line = f"{stamp} {message}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as stream:
        stream.write(line + "\n")


def prepare() -> list[dict[str, Any]]:
    """Select a fixed-seed balanced subset from the checked-in OWASP labels."""
    groups: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: {"vulnerable": [], "safe": []}
    )
    csv_path = DATASET / "expectedresults-1.2.csv"
    with csv_path.open(newline="", encoding="utf-8") as stream:
        for row in csv.reader(stream):
            if not row or row[0].startswith("#") or len(row) < 4:
                continue
            test_name = row[0].strip()
            cwe = f"CWE-{int(row[3])}"
            label = "vulnerable" if row[2].strip().lower() == "true" else "safe"
            groups[cwe][label].append(
                {
                    "test_name": test_name,
                    "id": f"owasp_{test_name}",
                    "cwe": cwe,
                    "label": label,
                }
            )

    counts = {cwe: sum(len(v) for v in labels.values()) for cwe, labels in groups.items()}
    top = sorted(counts, key=lambda cwe: (-counts[cwe], cwe))[:3]
    if len(top) != 3:
        raise RuntimeError("OWASP expected-results CSV has fewer than three CWEs.")

    chooser = random.Random(SEED)
    selected: list[dict[str, Any]] = []
    for cwe in top:
        for label in ("vulnerable", "safe"):
            available = sorted(groups[cwe][label], key=lambda item: item["test_name"])
            if len(available) < 4:
                raise RuntimeError(f"{cwe} has only {len(available)} {label} samples.")
            selected.extend(chooser.sample(available, 4))

    llm_selected: set[str] = set()
    # Nested 12-sample subset: 2 vulnerable + 2 safe for each selected CWE.
    for cwe in top:
        for label in ("vulnerable", "safe"):
            options = [
                item for item in selected if item["cwe"] == cwe and item["label"] == label
            ]
            llm_selected.update(item["id"] for item in chooser.sample(options, 2))

    manifest: list[dict[str, Any]] = []
    input_dir = LOCAL / "input_diffs"
    input_dir.mkdir(parents=True, exist_ok=True)
    for item in sorted(selected, key=lambda row: (row["cwe"], row["label"], row["test_name"])):
        test_name = item["test_name"]
        source_path = SOURCE_ROOT / f"{test_name}.java"
        if not source_path.is_file():
            raise FileNotFoundError(f"OWASP source is missing: {source_path}")
        relative_file = f"src/main/java/org/owasp/benchmark/testcode/{test_name}.java"
        source_text = source_path.read_text(encoding="utf-8")
        file_lines = source_text.splitlines(keepends=True)
        if source_text and not source_text.endswith("\n"):
            file_lines[-1] += "\n"
        diff = (
            f"diff --git a/{relative_file} b/{relative_file}\n"
            "new file mode 100644\n"
            + "".join(
                difflib.unified_diff(
                    [], file_lines, fromfile="/dev/null", tofile=f"b/{relative_file}"
                )
            )
        )
        sample_id = f"owasp_{test_name}"
        diff_path = input_dir / f"{sample_id}.diff"
        diff_path.write_text(diff, encoding="utf-8")
        manifest.append(
            {
                "id": sample_id,
                "dataset": "owasp_benchmark",
                "language": "java",
                "file": relative_file,
                "diff_path": diff_path.relative_to(HERE).as_posix(),
                "label": item["label"],
                "cwe": item["cwe"],
                "line_range": None,
                "llm_subset": sample_id in llm_selected,
                "seed": SEED,
            }
        )

    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    counts_by_cwe = Counter(row["cwe"] for row in manifest)
    counts_by_label = Counter((row["cwe"], row["label"]) for row in manifest)
    log(f"Subset prepared seed={SEED}; semgrep samples={len(manifest)}; llm samples={len(llm_selected)}")
    for cwe in top:
        log(
            f"Subset {cwe}: total={counts_by_cwe[cwe]}, "
            f"vulnerable={counts_by_label[(cwe, 'vulnerable')]}, "
            f"safe={counts_by_label[(cwe, 'safe')]}"
        )
    return manifest


def _parse_pre_verifier(state: dict[str, Any], sample: dict[str, Any], diff: str) -> list[dict[str, Any]]:
    """Extract specialist-only candidate findings from one run's pre-verifier state."""
    from src.structured_findings import _infer_cwe_from_finding, extract_file_and_line_from_diff, parse_diff_hunks

    diff_map = parse_diff_hunks(diff)
    output: list[dict[str, Any]] = []
    sources = (
        ("bug_report", "Bug Detector"),
        ("security_report", "Security"),
        ("quality_report", "Code Quality"),
        ("test_report", "Test Coverage"),
    )
    for key, source in sources:
        report = "\n".join(str(part) for part in state.get(key, []))
        blocks = re.split(r"(?m)(?=^\s*(?:\d+[.)]|[-*])\s+)", report)
        for block in blocks:
            text = block.strip()
            if not text:
                continue
            title_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
            title = re.sub(r"^(?:\d+[.)]|[-*])\s*", "", title_line).strip(" *`-")
            if len(title) < 8:
                continue
            evidence_match = re.search(r"(?ims)^\s*(?:[-*]\s*)?Evidence\s*:\s*(.*?)(?=^\s*(?:[-*]\s*)?(?:Fix|Source|CWE|Confidence|Severity)\s*:|\Z)", text)
            evidence = evidence_match.group(1).strip() if evidence_match else ""
            fix_match = re.search(r"(?ims)^\s*(?:[-*]\s*)?Fix\s*:\s*(.*?)(?=^\s*(?:[-*]\s*)?(?:Evidence|Source|CWE|Confidence|Severity)\s*:|\Z)", text)
            fix = fix_match.group(1).strip() if fix_match else ""
            title = re.sub(r"^\[(?:CRITICAL|HIGH|MEDIUM|LOW)\s*\|\s*(?:HIGH|MEDIUM|LOW)\]\s*", "", title, flags=re.I)
            severity_match = re.search(r"\b(CRITICAL|HIGH|MEDIUM|LOW)\b", title_line, re.I)
            confidence_match = re.search(r"\b(HIGH|MEDIUM|LOW)\b", title_line, re.I)
            file_path, line = extract_file_and_line_from_diff(evidence, title, diff_map)
            cwe = _infer_cwe_from_finding(title, evidence)
            output.append(
                {
                    "title": title,
                    "severity": severity_match.group(1).upper() if severity_match else "LOW",
                    "confidence": confidence_match.group(1).upper() if confidence_match else "LOW",
                    "cwe": cwe,
                    "file": file_path or sample["file"],
                    "line": line or 0,
                    "evidence": evidence,
                    "fix": fix,
                    "sources": [source],
                }
            )
    return output


def _one_sample(sample_id: str, result_path: Path) -> None:
    """Child-process entry point, isolated so the parent can enforce hard timeouts."""
    os.environ["OLLAMA_MODEL"] = MODEL
    os.environ["MODEL"] = MODEL
    os.environ["TEMPERATURE"] = "0"
    sys.path.insert(0, str(ROOT))
    from src.config import MODEL as configured_model, TEMPERATURE
    from src.main import run_review
    from src.structured_findings import parse_accepted_findings

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    sample = next(row for row in manifest if row["id"] == sample_id)
    diff_path = HERE / sample["diff_path"]
    diff = diff_path.read_text(encoding="utf-8")
    trace: dict[str, Any] = {}

    def capture(event: dict[str, Any]) -> None:
        if event.get("event") == "start" and event.get("node") == "verifier":
            trace["pre_verifier_state"] = dict(event.get("state", {}))
        elif event.get("event") == "end" and event.get("node") == "verifier":
            result = event.get("output") or {}
            trace["verifier_before_rules"] = result.get("verifier_report_before_rules", "")
            trace["verifier_after_rules"] = result.get("verified_report", "")

    started = time.monotonic()
    final_report = run_review(
        diff,
        [sample["file"]],
        node_callback=capture,
        capture_verifier_trace=True,
    )
    elapsed = time.monotonic() - started
    state = trace.get("pre_verifier_state", {})
    pre_findings = _parse_pre_verifier(state, sample, diff)
    # Semgrep is deliberately excluded from the llm_no_verifier config.
    full_findings = parse_accepted_findings(final_report, diff)
    record = {
        "sample_id": sample_id,
        "status": "done",
        "elapsed_s": elapsed,
        "model": configured_model,
        "temperature": TEMPERATURE,
        "label": sample,
        "llm_no_verifier": pre_findings,
        "full": full_findings,
        "verifier_report_before_rules": trace.get("verifier_before_rules", ""),
        "verifier_report_after_rules": trace.get("verifier_after_rules", ""),
        "final_report": final_report,
        "raw_pre_verifier_state": {
            key: state.get(key, [])
            for key in ("bug_report", "security_report", "quality_report", "test_report")
        },
    }
    result_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = result_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(record, indent=2), encoding="utf-8")
    temporary.replace(result_path)


def run_llm(resume: bool) -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    selected = [item for item in manifest if item["llm_subset"]]
    done = 0
    for sample in selected:
        sample_id = sample["id"]
        raw_path = LOCAL / "samples" / f"{sample_id}.json"
        if resume and raw_path.exists():
            try:
                old = json.loads(raw_path.read_text(encoding="utf-8"))
                if old.get("status") in {"done", "timeout", "failed"}:
                    done += 1
                    log(f"resume {sample_id}: existing status={old['status']}; completed {done}/{len(selected)}")
                    continue
            except (OSError, json.JSONDecodeError):
                pass
        started = time.monotonic()
        log(f"starting {sample_id} ({done}/{len(selected)} complete; timeout={TIMEOUT_S}s)")
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        command = [sys.executable, str(HERE / "local_eval.py"), "_one", sample_id, str(raw_path)]
        try:
            completed = subprocess.run(
                command,
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=TIMEOUT_S,
                check=False,
            )
            if completed.returncode != 0:
                record = {
                    "sample_id": sample_id,
                    "status": "failed",
                    "elapsed_s": time.monotonic() - started,
                    "error": (completed.stderr or completed.stdout)[-6000:],
                    "label": sample,
                    "llm_no_verifier": [],
                    "full": [],
                }
                raw_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
            elif not raw_path.exists():
                raise RuntimeError("worker exited successfully without writing its result")
        except subprocess.TimeoutExpired:
            record = {
                "sample_id": sample_id,
                "status": "timeout",
                "elapsed_s": TIMEOUT_S,
                "error": f"sample exceeded {TIMEOUT_S} second timeout",
                "label": sample,
                "llm_no_verifier": [],
                "full": [],
            }
            raw_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
        except Exception as error:
            record = {
                "sample_id": sample_id,
                "status": "failed",
                "elapsed_s": time.monotonic() - started,
                "error": f"{error.__class__.__name__}: {error}",
                "label": sample,
                "llm_no_verifier": [],
                "full": [],
            }
            raw_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
        finally:
            done += 1
            try:
                record = json.loads(raw_path.read_text(encoding="utf-8"))
                log(
                    f"finished {sample_id}: status={record.get('status')}, "
                    f"time={record.get('elapsed_s', time.monotonic() - started):.1f}s; "
                    f"completed {done}/{len(selected)}"
                )
            except (OSError, json.JSONDecodeError):
                log(f"finished {sample_id}: status=failed, completed {done}/{len(selected)}")


def summarize() -> None:
    """Write partial-safe metrics and visualizations from completed raw runs only."""
    sys.path.insert(0, str(ROOT))
    from eval_harness.metrics import compute_metrics, matches_finding_to_label

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    llm_manifest = [item for item in manifest if item["llm_subset"]]
    sample_records: dict[str, dict[str, Any]] = {}
    for path in sorted((LOCAL / "samples").glob("*.json")):
        try:
            sample_records[path.stem] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

    configs: dict[str, dict[str, Any]] = {}
    for config in ("semgrep_only", "llm_no_verifier", "full"):
        if config == "semgrep_only":
            raw_dir = LOCAL / "semgrep_only"
            complete_manifest = [
                item for item in manifest if (raw_dir / f"{item['id']}.json").is_file()
            ]
            results = {
                item["id"]: json.loads((raw_dir / f"{item['id']}.json").read_text(encoding="utf-8"))
                for item in complete_manifest
            }
        else:
            key = config
            complete_manifest = [
                item
                for item in llm_manifest
                if sample_records.get(item["id"], {}).get("status") == "done"
            ]
            results = {
                item["id"]: sample_records[item["id"]].get(key, [])
                for item in complete_manifest
            }
        configs[config] = {
            "manifest": complete_manifest,
            "results": results,
            "metrics": compute_metrics(complete_manifest, results) if complete_manifest else None,
        }

    LOCAL.mkdir(parents=True, exist_ok=True)
    per_cwe_path = LOCAL / "summary_per_cwe.csv"
    with per_cwe_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["config", "cwe", "n_samples", "tp", "fp", "fn", "tn", "precision", "recall", "f1", "status"])
        for config, data in configs.items():
            metrics = data["metrics"]
            if not metrics:
                writer.writerow([config, "", 0, "", "", "", "", "", "", "", "not run / no completed samples"])
                continue
            for cwe, row in sorted(metrics["per_cwe"].items()):
                n = row["vulnerable_samples"] + row["safe_samples"]
                writer.writerow([config, cwe, n, row["tp"], row["fp"], row["fn"], row["tn"], row["precision"], row["recall"], row["f1"], "complete"])

    overall_path = LOCAL / "summary_overall.csv"
    with overall_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["config", "n_samples", "tp", "fp", "fn", "tn", "micro_precision", "micro_recall", "micro_f1", "macro_precision", "macro_recall", "macro_f1", "status"])
        for config, data in configs.items():
            metrics = data["metrics"]
            if not metrics:
                writer.writerow([config, 0, "", "", "", "", "", "", "", "", "", "", "not run / no completed samples"])
                continue
            overall = metrics["overall"]
            n = overall["vulnerable_samples"] + overall["safe_samples"]
            macro = metrics["macro_avg"]
            writer.writerow([config, n, overall["tp"], overall["fp"], overall["fn"], overall["tn"], overall["precision"], overall["recall"], overall["f1"], macro["precision"], macro["recall"], macro["f1"], "complete"])

    llm_data = configs["llm_no_verifier"]
    full_data = configs["full"]
    compared_ids = {
        item["id"] for item in llm_data["manifest"]
    } & {item["id"] for item in full_data["manifest"]}
    compare_manifest = [item for item in llm_manifest if item["id"] in compared_ids]
    before_results = {sample_id: sample_records[sample_id].get("llm_no_verifier", []) for sample_id in compared_ids}
    after_results = {sample_id: sample_records[sample_id].get("full", []) for sample_id in compared_ids}
    before_metrics = compute_metrics(compare_manifest, before_results) if compare_manifest else None
    after_metrics = compute_metrics(compare_manifest, after_results) if compare_manifest else None
    with (LOCAL / "ablation.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["config", "n_samples", "false_positives", "status"])
        for config, metrics in (("llm_no_verifier", before_metrics), ("full", after_metrics)):
            if metrics:
                writer.writerow([config, len(compare_manifest), metrics["overall"]["fp"], "complete"])
            else:
                writer.writerow([config, 0, "", "not run / no paired samples"])
        if before_metrics and after_metrics:
            writer.writerow(["false_positive_change_full_minus_pre_verifier", len(compare_manifest), after_metrics["overall"]["fp"] - before_metrics["overall"]["fp"], "complete"])

    timings: list[dict[str, Any]] = []
    for sample in llm_manifest:
        record = sample_records.get(sample["id"], {})
        timings.append({"sample_id": sample["id"], "cwe": sample["cwe"], "label": sample["label"], "status": record.get("status", "not_started"), "elapsed_s": record.get("elapsed_s", "")})
    with (LOCAL / "timings.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["sample_id", "cwe", "label", "status", "elapsed_s"])
        writer.writeheader()
        writer.writerows(timings)

    try:
        from PIL import Image, ImageDraw
        _write_charts(Image, ImageDraw, configs)
    except ImportError:
        log("Pillow unavailable; PNG charts could not be generated.")

    _write_summary(manifest, llm_manifest, sample_records, configs, before_metrics, after_metrics)
    log("Summary CSV, charts, and results_summary.md updated from completed records.")


def _write_charts(Image: Any, ImageDraw: Any, configs: dict[str, dict[str, Any]]) -> None:
    width, height = 1100, 700
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    labels = ("semgrep_only", "llm_no_verifier", "full")
    draw.text((30, 20), "Confusion matrices (completed samples only)", fill="black")
    for index, config in enumerate(labels):
        x0 = 40 + index * 355
        draw.text((x0, 70), config, fill="black")
        metrics = configs[config]["metrics"]
        if metrics is None:
            draw.text((x0, 105), "Not run / no completed samples", fill="black")
            continue
        values = metrics["overall"]
        cells = (("TP", values["tp"]), ("FN", values["fn"]), ("FP", values["fp"]), ("TN", values["tn"]))
        for cell_index, (label, value) in enumerate(cells):
            row, col = divmod(cell_index, 2)
            x, y = x0 + col * 140, 115 + row * 130
            draw.rectangle((x, y, x + 125, y + 110), outline="#6b5ca5", width=2, fill="#eeeafd")
            draw.text((x + 12, y + 15), f"{label}: {value}", fill="black")
        n = values["vulnerable_samples"] + values["safe_samples"]
        draw.text((x0, 395), f"n={n} completed samples", fill="black")
    image.save(LOCAL / "confusion_matrix.png")

    cwes = list(CWE_ORDER)
    image = Image.new("RGB", (900, 500), "white")
    draw = ImageDraw.Draw(image)
    draw.text((20, 20), "F1 by CWE (completed samples only)", fill="black")
    colors = {"llm_no_verifier": "#4f46e5", "full": "#16a34a"}
    for i, cwe in enumerate(cwes):
        x = 110 + i * 260
        draw.text((x, 440), cwe, fill="black")
        for offset, config in ((0, "llm_no_verifier"), (70, "full")):
            metrics = configs[config]["metrics"]
            if not metrics or cwe not in metrics["per_cwe"]:
                draw.text((x + offset, 80), "n/a", fill="black")
                continue
            result = metrics["per_cwe"][cwe]
            n = result["vulnerable_samples"] + result["safe_samples"]
            bar_h = int(result["f1"] * 330)
            draw.rectangle((x + offset, 410 - bar_h, x + offset + 54, 410), fill=colors[config])
            draw.text((x + offset, max(70, 390 - bar_h)), f"{result['f1']:.3f} n={n}", fill="black")
    image.save(LOCAL / "f1_by_cwe.png")

    image = Image.new("RGB", (700, 450), "white")
    draw = ImageDraw.Draw(image)
    draw.text((20, 20), "False positives before and after Verifier", fill="black")
    for index, config in enumerate(("llm_no_verifier", "full")):
        metrics = configs[config]["metrics"]
        if not metrics:
            draw.text((40, 90 + index * 90), f"{config}: not run", fill="black")
            continue
        row = metrics["overall"]
        n = row["vulnerable_samples"] + row["safe_samples"]
        bar_width = row["fp"] * 25
        x, y = 40, 100 + index * 125
        draw.text((x, y), f"{config}: FP={row['fp']} n={n}", fill="black")
        draw.rectangle((x, y + 30, x + max(2, bar_width), y + 70), fill="#dc2626" if index == 0 else "#16a34a")
    image.save(LOCAL / "ablation_bar.png")


def _write_summary(
    manifest: list[dict[str, Any]],
    llm_manifest: list[dict[str, Any]],
    records: dict[str, dict[str, Any]],
    configs: dict[str, dict[str, Any]],
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
) -> None:
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip() or "unknown"
    statuses = Counter(records.get(item["id"], {}).get("status", "not_started") for item in llm_manifest)
    lines = [
        "# SentinelCode local OWASP evaluation",
        "",
        f"- Date: {datetime.now().date().isoformat()}",
        f"- Git commit: `{commit}`",
        f"- Model: `{MODEL}`",
        "- Temperature: 0",
        "- Hardware: Ollama reported 100% CPU for qwen2.5-coder:14b. `nvidia-smi` was unavailable; GPU use is unverified beyond Ollama's CPU report.",
        "- Speed probe: generated 1.20 tokens/s; prompt evaluation 2.41 tokens/s; one 10-token response. This probe is not an evaluation result.",
        "- Subset: fixed seed 20261101; 4 vulnerable + 4 safe each for CWE-89, CWE-330, CWE-79 (24 total); nested 2 vulnerable + 2 safe each (12 LLM samples). Input diffs add the actual Java source files.",
        "- LLM completion status: " + ", ".join(f"{name}={count}" for name, count in sorted(statuses.items())),
        "",
        "## Overall metrics",
        "",
        "See `summary_overall.csv` for n, confusion counts, micro and macro metrics. `semgrep_only` remains marked unavailable unless result files exist; empty detections are not treated as a completed run.",
        "",
        "| Config | n samples | TP | FP | FN | TN | Micro precision | Micro recall | Micro F1 | Macro precision | Macro recall | Macro F1 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for config, data in configs.items():
        metrics = data["metrics"]
        if metrics is None:
            lines.append(f"| {config} | 0 | — | — | — | — | — | — | — | — | — | — | not run |")
            continue
        row, macro = metrics["overall"], metrics["macro_avg"]
        n = row["vulnerable_samples"] + row["safe_samples"]
        lines.append(f"| {config} | {n} | {row['tp']} | {row['fp']} | {row['fn']} | {row['tn']} | {row['precision']:.4f} | {row['recall']:.4f} | {row['f1']:.4f} | {macro['precision']:.4f} | {macro['recall']:.4f} | {macro['f1']:.4f} |")
    lines.extend(["", "## Per-CWE metrics", "", "See `summary_per_cwe.csv` for per-CWE `n`, TP/FP/FN/TN, precision, recall, and F1.", "", "## Verifier ablation", ""])
    if before and after:
        n = len({item["id"] for item in configs["llm_no_verifier"]["manifest"]} & {item["id"] for item in configs["full"]["manifest"]})
        lines.append(f"Paired completed samples: n={n}. False positives before Verifier: {before['overall']['fp']}; after Verifier: {after['overall']['fp']}; change (after − before): {after['overall']['fp'] - before['overall']['fp']}.")
    else:
        lines.append("No paired completed LLM samples; false-positive change is unavailable.")

    done_records = [records[item["id"]] for item in llm_manifest if records.get(item["id"], {}).get("status") == "done"]
    durations = [float(item["elapsed_s"]) for item in done_records if item.get("elapsed_s") is not None]
    finding_counts = {key: [len(item.get(key, [])) for item in done_records] for key in ("llm_no_verifier", "full")}
    lines.extend(["", "## Timing and finding volume", "", "| Config | n completed samples | Mean seconds/sample | Median seconds/sample | Std dev seconds/sample | Mean findings/sample |", "|---|---:|---:|---:|---:|---:|"])
    for config in ("llm_no_verifier", "full"):
        values = durations
        if not values:
            lines.append(f"| {config} | 0 | — | — | — | — |")
            continue
        findings = finding_counts[config]
        lines.append(f"| {config} | {len(values)} | {statistics.mean(values):.2f} | {statistics.median(values):.2f} | {statistics.stdev(values) if len(values) > 1 else 0.0:.2f} | {statistics.mean(findings):.2f} |")
    lines.extend(["", "## Failures and timeouts", ""])
    issues = [records[item["id"]] for item in llm_manifest if records.get(item["id"], {}).get("status") in {"timeout", "failed"}]
    if issues:
        lines.extend(f"- `{item['sample_id']}`: {item['status']} — {item.get('error', '')}" for item in issues)
    else:
        lines.append("No completed run failures/timeouts recorded yet.")
    lines.extend(["", "## Precision by confidence", "", "Computed from full-pipeline findings only; entries with fewer than 2 findings are marked too few.", ""])
    confidence_counts: dict[str, Counter[str]] = {level: Counter() for level in ("HIGH", "MEDIUM", "LOW")}
    sample_by_id = {item["id"]: item for item in llm_manifest}
    for sample_id in {item["id"] for item in configs["full"]["manifest"]}:
        label = sample_by_id[sample_id]
        for finding in records[sample_id].get("full", []):
            level = str(finding.get("confidence", "LOW")).upper()
            if level not in confidence_counts:
                continue
            confidence_counts[level]["n"] += 1
            if matches_finding_to_label(finding, label):
                confidence_counts[level]["tp"] += 1
    for level, counts in confidence_counts.items():
        n = counts["n"]
        value = f"{counts['tp'] / n:.4f}" if n >= 2 else "too few findings"
        lines.append(f"- {level}: precision={value}; n={n} findings")
    lines.extend([
        "",
        "## Limitations",
        "",
        "- The sample is very small; metrics are preliminary.",
        "- Data is Java-only; CWE assignment is keyword-based; this is one run with no variance estimate.",
        "- The checked-in OWASP source files are used to generate real file-addition diffs because the repository's prepared OWASP diffs are comment-only placeholders and its default manifest contains SecurityEval/Python only.",
        "- Semgrep is not installed and WSL is unavailable on this Windows host, so the semgrep_only configuration could not be run. The pipeline's own Semgrep scanner analyzes Python additions only; it does not scan these Java diffs.",
        "- Local Ollama run was CPU-only according to `ollama ps`; GPU performance could not be verified because `nvidia-smi` is unavailable.",
        "- Metric unit tests could not be run because pytest is not installed in the available Python environments.",
    ])
    (LOCAL / "results_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("prepare")
    llm = sub.add_parser("llm")
    llm.add_argument("--resume", action="store_true")
    sub.add_parser("summarize")
    one = sub.add_parser("_one")
    one.add_argument("sample_id")
    one.add_argument("result_path", type=Path)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare()
    elif args.command == "llm":
        run_llm(args.resume)
    elif args.command == "summarize":
        summarize()
    else:
        _one_sample(args.sample_id, args.result_path)


if __name__ == "__main__":
    main()
