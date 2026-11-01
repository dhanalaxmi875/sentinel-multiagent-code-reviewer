"""Metrics computation for vulnerability detection evaluation.

Computes TP/FP/FN/TN, precision, recall, F1 per CWE, and macro/micro averages.

Matching rules:
- TP: Finding targets same file and CWE as label (line overlap within +/-5 when available)
- FN: Vulnerable sample with no matching finding
- FP: Finding on safe sample, or finding with wrong CWE on vulnerable sample
- TN: Safe sample with no findings
"""

import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from collections import defaultdict


def line_ranges_overlap(
    range1: Optional[Tuple[int, int]],
    range2: Optional[Tuple[int, int]],
    tolerance: int = 5
) -> bool:
    """Check if two line ranges overlap within tolerance."""
    if range1 is None or range2 is None:
        return True  # If either range is unknown, consider it a match

    start1, end1 = range1
    start2, end2 = range2

    # Check overlap with tolerance
    return not (end1 + tolerance < start2 or end2 + tolerance < start1)


def matches_finding_to_label(
    finding: Dict,
    label: Dict,
    tolerance: int = 5
) -> bool:
    """
    Check if a finding matches a label according to evaluation rules.

    Returns True if:
    - Same file path (or both None)
    - Same CWE
    - Line ranges overlap within tolerance (when both available)
    """
    # Check CWE match
    if finding.get('cwe') != label.get('cwe'):
        return False

    # Check file match
    finding_file = finding.get('file', '')
    label_file = label.get('file', '')
    if finding_file and label_file:
        if finding_file != label_file:
            return False

    # Check line range overlap
    finding_range = None
    if finding.get('line') is not None:
        finding_range = (finding['line'], finding['line'])

    label_range = None
    if label.get('line_range') is not None:
        label_range = tuple(label['line_range'])

    return line_ranges_overlap(finding_range, label_range, tolerance)


def compute_metrics(
    manifest: List[Dict],
    results: Dict[str, List[Dict]],
    tolerance: int = 5
) -> Dict:
    """
    Compute TP/FP/FN/TN metrics from manifest and results.

    Args:
        manifest: List of label entries from manifest.json
        results: Dict mapping sample_id to list of findings
        tolerance: Line range tolerance for matching

    Returns:
        Dict with per-CWE and overall metrics
    """
    # Initialize counters
    cwe_stats = defaultdict(lambda: {
        'tp': 0,
        'fp': 0,
        'fn': 0,
        'tn': 0,
        'vulnerable_samples': 0,
        'safe_samples': 0
    })

    overall_stats = {
        'tp': 0,
        'fp': 0,
        'fn': 0,
        'tn': 0,
        'vulnerable_samples': 0,
        'safe_samples': 0
    }

    # Process each sample
    for label in manifest:
        sample_id = label['id']
        cwe = label['cwe']
        label_type = label['label']  # 'vulnerable' or 'safe'
        findings = results.get(sample_id, [])

        # Track sample counts
        cwe_stats[cwe][f'{label_type}_samples'] += 1
        overall_stats[f'{label_type}_samples'] += 1

        if label_type == 'vulnerable':
            # Vulnerable sample
            matched = False
            for finding in findings:
                if matches_finding_to_label(finding, label, tolerance):
                    cwe_stats[cwe]['tp'] += 1
                    overall_stats['tp'] += 1
                    matched = True
                else:
                    # Wrong CWE on vulnerable sample = FP
                    cwe_stats[cwe]['fp'] += 1
                    overall_stats['fp'] += 1

            if not matched:
                cwe_stats[cwe]['fn'] += 1
                overall_stats['fn'] += 1

        else:  # safe
            # Safe sample
            if findings:
                # Any finding on safe sample = FP
                cwe_stats[cwe]['fp'] += len(findings)
                overall_stats['fp'] += len(findings)
            else:
                cwe_stats[cwe]['tn'] += 1
                overall_stats['tn'] += 1

    # Compute derived metrics (precision, recall, F1)
    def compute_derived(stats: Dict) -> Dict:
        precision = stats['tp'] / (stats['tp'] + stats['fp']) if (stats['tp'] + stats['fp']) > 0 else 0.0
        recall = stats['tp'] / (stats['tp'] + stats['fn']) if (stats['tp'] + stats['fn']) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        return {
            'precision': precision,
            'recall': recall,
            'f1': f1
        }

    # Compute per-CWE metrics
    cwe_metrics = {}
    for cwe, stats in cwe_stats.items():
        cwe_metrics[cwe] = {
            **stats,
            **compute_derived(stats)
        }

    # Compute overall metrics
    overall_metrics = {
        **overall_stats,
        **compute_derived(overall_stats)
    }

    # Compute macro averages (average of per-CWE metrics)
    if cwe_metrics:
        macro_precision = sum(m['precision'] for m in cwe_metrics.values()) / len(cwe_metrics)
        macro_recall = sum(m['recall'] for m in cwe_metrics.values()) / len(cwe_metrics)
        macro_f1 = sum(m['f1'] for m in cwe_metrics.values()) / len(cwe_metrics)
    else:
        macro_precision = macro_recall = macro_f1 = 0.0

    return {
        'per_cwe': cwe_metrics,
        'overall': overall_metrics,
        'macro_avg': {
            'precision': macro_precision,
            'recall': macro_recall,
            'f1': macro_f1
        }
    }


def load_manifest(manifest_path: Path) -> List[Dict]:
    """Load manifest from JSON file."""
    with open(manifest_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_results(results_dir: Path) -> Dict[str, List[Dict]]:
    """Load all result JSON files from directory."""
    results = {}
    for result_file in results_dir.glob('*.json'):
        with open(result_file, 'r', encoding='utf-8') as f:
            findings = json.load(f)
            sample_id = result_file.stem
            results[sample_id] = findings
    return results


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Compute evaluation metrics"
    )
    parser.add_argument(
        '--manifest',
        type=Path,
        required=True,
        help="Path to manifest.json"
    )
    parser.add_argument(
        '--results-dir',
        type=Path,
        required=True,
        help="Directory containing result JSON files"
    )
    parser.add_argument(
        '--output',
        type=Path,
        help="Output metrics JSON file (optional)"
    )
    parser.add_argument(
        '--tolerance',
        type=int,
        default=5,
        help="Line range tolerance for matching (default: 5)"
    )

    args = parser.parse_args()

    # Load data
    manifest = load_manifest(args.manifest)
    results = load_results(args.results_dir)

    print(f"Loaded {len(manifest)} samples from manifest")
    print(f"Loaded {len(results)} result files")

    # Compute metrics
    metrics = compute_metrics(manifest, results, args.tolerance)

    # Print summary
    print("\n=== Overall Metrics ===")
    overall = metrics['overall']
    print(f"TP: {overall['tp']}, FP: {overall['fp']}, FN: {overall['fn']}, TN: {overall['tn']}")
    print(f"Precision: {overall['precision']:.3f}")
    print(f"Recall: {overall['recall']:.3f}")
    print(f"F1: {overall['f1']:.3f}")

    print("\n=== Macro Average ===")
    macro = metrics['macro_avg']
    print(f"Precision: {macro['precision']:.3f}")
    print(f"Recall: {macro['recall']:.3f}")
    print(f"F1: {macro['f1']:.3f}")

    print("\n=== Per-CWE Metrics ===")
    print(f"{'CWE':<10} {'Prec':<6} {'Rec':<6} {'F1':<6} {'TP':<4} {'FP':<4} {'FN':<4} {'TN':<4}")
    for cwe in sorted(metrics['per_cwe'].keys()):
        m = metrics['per_cwe'][cwe]
        print(f"{cwe:<10} {m['precision']:.3f}  {m['recall']:.3f}  {m['f1']:.3f}  {m['tp']:<4} {m['fp']:<4} {m['fn']:<4} {m['tn']:<4}")

    # Save if requested
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2)
        print(f"\nMetrics saved to {args.output}")


if __name__ == "__main__":
    main()
