"""Load CVEfixes Python subset for evaluation.

This script loads a pre-extracted Python subset from CVEfixes.
The expected input format is a JSON or CSV file with method-level
before/after code pairs and CWE labels.

Expected JSON schema:
[
  {
    "id": "CVE-2021-12345_python_1",
    "cwe": "CWE-89",
    "language": "python",
    "file_path": "src/db/queries.py",
    "method_name": "fetch_user",
    "before_code": "def fetch_user(user_id):\n    cursor.execute('SELECT * FROM users WHERE id = ' + user_id)",
    "after_code": "def fetch_user(user_id):\n    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))",
    "line_range": [10, 15]
  },
  ...
]

Expected CSV schema:
id,cwe,language,file_path,method_name,before_code,after_code,line_range
CVE-2021-12345_python_1,CWE-89,python,src/db/queries.py,fetch_user,"def fetch_user...","def fetch_user...","[10,15]"
...

Usage:
    python -m eval_harness.load_cvefixes --input path/to/python_subset.json
    python -m eval_harness.load_cvefixes --input path/to/python_subset.csv
"""

import argparse
import json
import csv
from pathlib import Path
from typing import List, Dict, Optional


def load_json_subset(input_path: Path) -> List[Dict]:
    """Load CVEfixes Python subset from JSON file."""
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Validate schema
    required_fields = {'id', 'cwe', 'language', 'before_code', 'after_code'}
    for item in data:
        if not required_fields.issubset(item.keys()):
            raise ValueError(f"Missing required fields in item: {item}")
        if item.get('language', '').lower() != 'python':
            raise ValueError(f"Non-Python language found: {item.get('language')}")

    return data


def load_csv_subset(input_path: Path) -> List[Dict]:
    """Load CVEfixes Python subset from CSV file."""
    data = []
    with open(input_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Parse line_range from string to list
            if row.get('line_range'):
                try:
                    row['line_range'] = json.loads(row['line_range'])
                except json.JSONDecodeError:
                    row['line_range'] = None

            # Validate language
            if row.get('language', '').lower() != 'python':
                raise ValueError(f"Non-Python language found: {row.get('language')}")

            data.append(row)

    return data


def load_subset(input_path: Path) -> List[Dict]:
    """Load CVEfixes Python subset from JSON or CSV file."""
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    suffix = input_path.suffix.lower()
    if suffix == '.json':
        return load_json_subset(input_path)
    elif suffix == '.csv':
        return load_csv_subset(input_path)
    else:
        raise ValueError(f"Unsupported file format: {suffix}. Use .json or .csv")


def get_cwe_counts(subset: List[Dict]) -> Dict[str, Dict[str, int]]:
    """Count vulnerable and safe samples per CWE."""
    counts = {}
    for item in subset:
        cwe = item['cwe']
        if cwe not in counts:
            counts[cwe] = {'vulnerable': 0, 'safe': 0}

        # Count as vulnerable if before_code exists and differs from after_code
        if item.get('before_code') and item.get('after_code'):
            if item['before_code'] != item['after_code']:
                counts[cwe]['vulnerable'] += 1
            else:
                counts[cwe]['safe'] += 1

    return counts


def main():
    parser = argparse.ArgumentParser(
        description="Load CVEfixes Python subset for evaluation"
    )
    parser.add_argument(
        '--input',
        type=Path,
        required=True,
        help="Path to JSON or CSV file with Python subset"
    )
    parser.add_argument(
        '--output',
        type=Path,
        help="Path to save statistics (optional)"
    )
    parser.add_argument(
        '--min-samples',
        type=int,
        default=10,
        help="Minimum samples per CWE to include (default: 10)"
    )

    args = parser.parse_args()

    # Load subset
    print(f"Loading CVEfixes Python subset from {args.input}...")
    subset = load_subset(args.input)
    print(f"  Loaded {len(subset)} samples")

    # Count per CWE
    counts = get_cwe_counts(subset)
    print(f"\nSample counts per CWE:")
    for cwe, count in sorted(counts.items()):
        print(f"  {cwe}: {count['vulnerable']} vulnerable, {count['safe']} safe")

    # Filter CWEs with insufficient samples
    filtered_cwes = {
        cwe: count for cwe, count in counts.items()
        if count['vulnerable'] >= args.min_samples and count['safe'] >= args.min_samples
    }

    print(f"\nCWEs with >= {args.min_samples} vulnerable and safe samples: {len(filtered_cwes)}")
    dropped_cwes = set(counts.keys()) - set(filtered_cwes.keys())
    if dropped_cwes:
        print(f"Dropped CWEs (insufficient samples): {len(dropped_cwes)}")
        for cwe in sorted(dropped_cwes):
            print(f"  {cwe}: {counts[cwe]['vulnerable']} vulnerable, {counts[cwe]['safe']} safe")

    # Save statistics if requested
    if args.output:
        stats = {
            'total_samples': len(subset),
            'cwe_counts': counts,
            'filtered_cwes': filtered_cwes,
            'dropped_cwes': list(dropped_cwes)
        }
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2)
        print(f"\nStatistics saved to {args.output}")


if __name__ == "__main__":
    main()
