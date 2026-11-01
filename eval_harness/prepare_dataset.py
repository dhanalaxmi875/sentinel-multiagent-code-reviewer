"""Prepare datasets for evaluation by converting samples to unified diffs and manifest.

Processes:
1. SecurityEval: Convert vulnerable code samples to diffs (file added)
2. OWASP Benchmark: Parse expected-results CSV, balance samples per CWE

Output: eval_harness/manifest.json with schema:
{
  "id": str,
  "dataset": str,
  "language": str,
  "file": str,
  "diff_path": str,
  "label": "vulnerable" | "safe",
  "cwe": str,
  "line_range": [int, int] | null
}
"""

import argparse
import csv
import json
import re
from pathlib import Path
from typing import List, Dict, Optional
import difflib


SCRIPT_DIR = Path(__file__).resolve().parent
DATASETS_DIR = SCRIPT_DIR / "datasets"
MANIFEST_PATH = SCRIPT_DIR / "manifest.json"
DIFFS_DIR = SCRIPT_DIR / "diffs"
DIFFS_DIR.mkdir(exist_ok=True)


def parse_cwe_from_id(sample_id: str) -> str:
    """Extract CWE ID from sample ID (e.g., 'CWE-020_author_1.py' -> 'CWE-20')."""
    match = re.search(r'CWE-(\d+)', sample_id)
    if match:
        # Remove leading zeros from CWE number
        cwe_num = str(int(match.group(1)))
        return f"CWE-{cwe_num}"
    return "CWE-UNKNOWN"


def prepare_securityeval(
    dataset_dir: Path,
    max_per_cwe: int = 30,
    min_per_cwe: int = 1  # Lower threshold for SecurityEval (recall-only)
) -> List[Dict]:
    """Prepare SecurityEval dataset."""
    print("Preparing SecurityEval dataset...")

    dataset_file = dataset_dir / "dataset.jsonl"
    if not dataset_file.exists():
        raise FileNotFoundError(f"SecurityEval dataset not found: {dataset_file}")

    # Load JSONL
    samples = []
    with open(dataset_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                samples.append(json.loads(line))

    print(f"  Loaded {len(samples)} samples from SecurityEval")

    # Group by CWE
    cwe_groups = {}
    for sample in samples:
        cwe = parse_cwe_from_id(sample['ID'])
        if cwe not in cwe_groups:
            cwe_groups[cwe] = []
        cwe_groups[cwe].append(sample)

    # Balance samples per CWE (cap at max_per_cwe)
    # SecurityEval is recall-only, so we include all CWEs with at least 1 sample
    balanced_samples = []
    for cwe, group in cwe_groups.items():
        if len(group) >= min_per_cwe:
            balanced_samples.extend(group[:max_per_cwe])

    print(f"  Kept {len(balanced_samples)} samples after balancing (max {max_per_cwe} per CWE)")
    dropped_cwes = [cwe for cwe, group in cwe_groups.items() if len(group) < min_per_cwe]
    print(f"  CWEs dropped (insufficient samples): {len(dropped_cwes)}")

    # Convert to manifest entries
    manifest_entries = []
    for sample in balanced_samples:
        cwe = parse_cwe_from_id(sample['ID'])
        sample_id = sample['ID'].replace('.py', '')

        # Create diff (file added)
        diff_content = f"""diff --git a/{sample['ID']} b/{sample['ID']}
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/{sample['ID']}
@@ -0,0 +1,{len(sample['Insecure_code'].splitlines())} +{sample['Insecure_code']}
"""

        # Save diff
        diff_path = DIFFS_DIR / f"securityeval_{sample_id}.diff"
        diff_path.write_text(diff_content, encoding='utf-8')

        manifest_entries.append({
            "id": f"securityeval_{sample_id}",
            "dataset": "securityeval",
            "language": "python",
            "file": sample['ID'],
            "diff_path": str(diff_path.relative_to(SCRIPT_DIR)),
            "label": "vulnerable",  # SecurityEval only has vulnerable samples
            "cwe": cwe,
            "line_range": None  # Line ranges not available in SecurityEval
        })

    print(f"  Created {len(manifest_entries)} manifest entries")
    return manifest_entries


def prepare_owasp_benchmark(
    dataset_dir: Path,
    max_per_cwe: int = 30
) -> List[Dict]:
    """Prepare OWASP Benchmark dataset."""
    print("Preparing OWASP Benchmark dataset...")

    csv_file = dataset_dir / "expectedresults-1.2.csv"
    if not csv_file.exists():
        raise FileNotFoundError(f"OWASP Benchmark CSV not found: {csv_file}")

    # Load CSV
    samples = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if row[0].startswith('#'):  # Skip header
                continue
            if len(row) >= 4:
                samples.append({
                    'test_name': row[0],
                    'category': row[1],
                    'real_vulnerability': row[2] == 'true',
                    'cwe': f"CWE-{row[3]}"
                })

    print(f"  Loaded {len(samples)} samples from OWASP Benchmark")

    # Group by CWE
    cwe_groups = {}
    for sample in samples:
        cwe = sample['cwe']
        if cwe not in cwe_groups:
            cwe_groups[cwe] = {'vulnerable': [], 'safe': []}
        if sample['real_vulnerability']:
            cwe_groups[cwe]['vulnerable'].append(sample)
        else:
            cwe_groups[cwe]['safe'].append(sample)

    # Balance samples per CWE (cap at max_per_cwe each)
    balanced_samples = []
    for cwe, group in cwe_groups.items():
        if len(group['vulnerable']) >= 10 and len(group['safe']) >= 10:
            balanced_samples.extend(group['vulnerable'][:max_per_cwe])
            balanced_samples.extend(group['safe'][:max_per_cwe])

    print(f"  Kept {len(balanced_samples)} samples after balancing (max {max_per_cwe} vulnerable + {max_per_cwe} safe per CWE)")
    dropped_cwes = [
        cwe for cwe, group in cwe_groups.items()
        if len(group['vulnerable']) < 10 or len(group['safe']) < 10
    ]
    print(f"  CWEs dropped (insufficient samples): {len(dropped_cwes)}")

    # Convert to manifest entries
    # Note: OWASP Benchmark is Java source code, but we don't have the actual source files
    # We'll create placeholder diffs that reference the test names
    manifest_entries = []
    for sample in balanced_samples:
        sample_id = sample['test_name']
        label = "vulnerable" if sample['real_vulnerability'] else "safe"

        # Create placeholder diff (references the test file)
        diff_content = f"""diff --git a/src/main/java/org/owasp/benchmark/testcode/{sample_id}.java b/src/main/java/org/owasp/benchmark/testcode/{sample_id}.java
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/src/main/java/org/owasp/benchmark/testcode/{sample_id}.java
@@ -0,0 +1,1 @@
+// OWASP Benchmark test case: {sample_id}
"""

        # Save diff
        diff_path = DIFFS_DIR / f"owasp_{sample_id}.diff"
        diff_path.write_text(diff_content, encoding='utf-8')

        manifest_entries.append({
            "id": f"owasp_{sample_id}",
            "dataset": "owasp_benchmark",
            "language": "java",
            "file": f"src/main/java/org/owasp/benchmark/testcode/{sample_id}.java",
            "diff_path": str(diff_path.relative_to(SCRIPT_DIR)),
            "label": label,
            "cwe": sample['cwe'],
            "line_range": None  # Line ranges not available from CSV
        })

    print(f"  Created {len(manifest_entries)} manifest entries")
    return manifest_entries


def main():
    parser = argparse.ArgumentParser(
        description="Prepare datasets for evaluation"
    )
    parser.add_argument(
        '--datasets',
        nargs='+',
        choices=['securityeval', 'owasp_benchmark'],
        default=['securityeval', 'owasp_benchmark'],
        help="Datasets to prepare (default: all)"
    )
    parser.add_argument(
        '--max-per-cwe',
        type=int,
        default=30,
        help="Maximum samples per CWE (default: 30)"
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=MANIFEST_PATH,
        help="Output manifest path (default: eval_harness/manifest.json)"
    )

    args = parser.parse_args()

    manifest = []

    if 'securityeval' in args.datasets:
        securityeval_dir = DATASETS_DIR / "SecurityEval"
        if securityeval_dir.exists():
            # SecurityEval is recall-only, use lower threshold
            manifest.extend(prepare_securityeval(securityeval_dir, args.max_per_cwe, min_per_cwe=1))
        else:
            print(f"WARNING: SecurityEval directory not found: {securityeval_dir}")

    if 'owasp_benchmark' in args.datasets:
        owasp_dir = DATASETS_DIR / "OWASP-Benchmark"
        if owasp_dir.exists():
            manifest.extend(prepare_owasp_benchmark(owasp_dir, args.max_per_cwe))
        else:
            print(f"WARNING: OWASP Benchmark directory not found: {owasp_dir}")

    # Save manifest
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)

    print(f"\nManifest saved to {args.output}")
    print(f"Total entries: {len(manifest)}")

    # Print summary
    print("\nDataset summary:")
    dataset_counts = {}
    for entry in manifest:
        dataset = entry['dataset']
        if dataset not in dataset_counts:
            dataset_counts[dataset] = {'vulnerable': 0, 'safe': 0, 'cwe': set()}
        dataset_counts[dataset][entry['label']] += 1
        dataset_counts[dataset]['cwe'].add(entry['cwe'])

    for dataset, counts in dataset_counts.items():
        print(f"  {dataset}:")
        print(f"    Vulnerable: {counts['vulnerable']}")
        print(f"    Safe: {counts['safe']}")
        print(f"    CWEs: {len(counts['cwe'])}")


if __name__ == "__main__":
    main()
