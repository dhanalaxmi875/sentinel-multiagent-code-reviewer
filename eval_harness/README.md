# Evaluation Harness for SentinelCode

This directory contains the evaluation harness for measuring precision, recall, and F1 of vulnerability detection per CWE using real public labelled datasets.

## Quick Start

### 1. Download Datasets

```bash
cd eval_harness
python download_datasets.py
```

This downloads:
- SecurityEval (Python, 121 vulnerable samples)
- OWASP Benchmark (Java, 2700+ samples)
- CVEfixes (GitHub repo only; full dataset requires manual download from Zenodo)

### 2. Prepare Datasets

```bash
python prepare_dataset.py
```

This converts samples to unified diffs and creates `manifest.json` with schema:
```json
{
  "id": "sample_id",
  "dataset": "securityeval | owasp_benchmark",
  "language": "python | java",
  "file": "path/to/file",
  "diff_path": "diffs/sample.diff",
  "label": "vulnerable | safe",
  "cwe": "CWE-89",
  "line_range": [start, end] | null
}
```

### 3. Run Smoke Test

```bash
# Test 10 samples
python run_eval.py --smoke

# Test specific dataset
python run_eval.py --smoke --dataset securityeval
python run_eval.py --smoke --dataset owasp_benchmark
```

### 4. Compute Metrics

```bash
python metrics.py --manifest manifest.json --results-dir results/raw/full/<run-id>
```

### 5. Run Ablation Study

```bash
python ablation.py --manifest manifest.json --output ablation.csv
```

## Dataset Details

### SecurityEval (Python)
- **Source**: https://github.com/s2e-lab/SecurityEval
- **Samples**: 121 vulnerable samples across 69 CWEs
- **Limitation**: No safe/fixed versions → recall-only evaluation
- **Usage**: Supplemental, excluded from precision/F1 aggregates

### OWASP Benchmark (Java)
- **Source**: https://github.com/OWASP-Benchmark/BenchmarkJava
- **Samples**: 632 samples (312 vulnerable, 320 safe) across 11 CWEs
- **Language**: Java (reported separately)
- **Usage**: Full precision/recall/F1 evaluation

### CVEfixes (Python)
- **Source**: https://github.com/secureIT-project/CVEfixes
- **Data**: Zenodo DOI: 10.5281/zenodo.4476563 (v1.0.8, 11.8GB)
- **Status**: Infrastructure prepared, dataset not downloaded due to bandwidth constraints
- **Usage**: Future work - use `load_cvefixes.py` with pre-extracted Python subset

## Pipeline Configurations

The harness supports three configurations for ablation studies:

- **full**: Full pipeline (orchestrator → specialists + semgrep → verifier → summarizer)
- **semgrep_only**: Semgrep static analysis only (no LLM agents)
- **llm_no_verifier**: LLM specialists without verifier

Note: Config-specific graph modifications are TODO - currently all use the full pipeline.

## Metrics

Matching rules:
- **TP**: Finding targets same file and CWE as label (line overlap within +/-5 when available)
- **FN**: Vulnerable sample with no matching finding
- **FP**: Finding on safe sample, or finding with wrong CWE on vulnerable sample
- **TN**: Safe sample with no findings

Metrics computed:
- Per-CWE: precision, recall, F1, TP, FP, FN, TN
- Overall: micro averages
- Macro averages: average of per-CWE metrics

## Testing

Run unit tests for metrics:

```bash
pytest eval_harness/test_metrics.py -v
```

## Reproducibility

Each result file includes:
- Model: qwen2.5-coder:14b (from src/config.py)
- Temperature: 0 (from src/config.py)
- Git commit hash
- Timestamp

## Output Structure

```
eval_harness/
├── results/
│   ├── raw/
│   │   ├── full/
│   │   │   └── <run-id>/
│   │   │       ├── sample1.json
│   │   │       └── sample2.json
│   │   ├── semgrep_only/
│   │   └── llm_no_verifier/
│   ├── summary_per_cwe.csv
│   ├── summary_overall.csv
│   └── ablation.csv
├── diffs/
│   ├── securityeval_sample1.diff
│   └── owasp_sample1.diff
├── manifest.json
└── datasets/
    ├── SecurityEval/
    ├── OWASP-Benchmark/
    └── CVEfixes/
```

## Known Limitations

1. **SecurityEval**: No safe samples → cannot compute precision
2. **OWASP Benchmark**: Java-only → Semgrep Python rules don't apply
3. **CVEfixes**: Not downloaded (11.8GB) → requires manual preparation
4. **Config-specific graphs**: Not yet implemented → all use full pipeline

## Orchestrator Fix

The Orchestrator was updated to include Java files for Security agent activation:
```python
# Old: Activate security for backend code, API endpoints, auth, database queries, config files.
# New: Activate security for backend code, API endpoints, auth, database queries, config files, and ALL Java/Python/C/C++ source files (.java, .py, .c, .cpp, .h, .hpp).
```

This ensures OWASP Benchmark (Java) samples trigger the Security agent.

## CWE Mapping Enhancement

The structured findings parser now includes enhanced CWE inference from vulnerability patterns:
- CWE-89: SQL injection
- CWE-78: OS command injection
- CWE-79: XSS
- CWE-22: Path traversal
- CWE-798: Hardcoded credentials
- CWE-502: Deserialization
- CWE-94: Code injection
- CWE-327: Weak cryptography
- CWE-90: LDAP injection
- CWE-611: XXE
- CWE-330: Insecure random
- CWE-120: Buffer overflow
- CWE-190: Integer overflow
- CWE-476: NULL pointer dereference
- CWE-416: Use after free

## Future Work

1. Download CVEfixes from Zenodo and extract Python subset
2. Implement config-specific graph modifications
3. Add visualization (confusion matrix, F1 by CWE)
4. Extend Semgrep rules for Java support
