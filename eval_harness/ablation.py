"""Ablation study: compare different pipeline configurations.

Compares three configs on the same samples:
- semgrep_only: Semgrep static analysis only
- llm_no_verifier: LLM specialists without verifier
- full: Full pipeline with verifier

Reports precision/recall/F1 and false-positive reduction attributable to the Verifier.
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List
from collections import defaultdict

from eval_harness.metrics import compute_metrics, load_manifest, load_results


def compare_configs(
    manifest: List[Dict],
    results_dirs: Dict[str, Path],
    tolerance: int = 5
) -> Dict:
    """
    Compare metrics across different configurations.

    Args:
        manifest: List of label entries
        results_dirs: Dict mapping config name to results directory
        tolerance: Line range tolerance

    Returns:
        Dict with per-config and comparison metrics
    """
    comparison = {}

    for config, results_dir in results_dirs.items():
        if not results_dir.exists():
            print(f"WARNING: Results directory not found for config {config}: {results_dir}")
            continue

        results = load_results(results_dir)
        metrics = compute_metrics(manifest, results, tolerance)
        comparison[config] = metrics

    # Compute FP reduction
    if 'llm_no_verifier' in comparison and 'full' in comparison:
        fp_llm = comparison['llm_no_verifier']['overall']['fp']
        fp_full = comparison['full']['overall']['fp']
        fp_reduction = fp_llm - fp_full
        fp_reduction_pct = (fp_reduction / fp_llm * 100) if fp_llm > 0 else 0.0

        comparison['fp_reduction'] = {
            'absolute': fp_reduction,
            'percentage': fp_reduction_pct,
            'fp_llm_no_verifier': fp_llm,
            'fp_full': fp_full
        }

    return comparison


def print_comparison_table(comparison: Dict):
    """Print comparison table for all configs."""
    print("\n=== Configuration Comparison ===")
    print(f"{'Config':<20} {'Prec':<6} {'Rec':<6} {'F1':<6} {'TP':<4} {'FP':<4} {'FN':<4} {'TN':<4}")
    print("-" * 50)

    for config in ['semgrep_only', 'llm_no_verifier', 'full']:
        if config not in comparison:
            continue
        m = comparison[config]['overall']
        print(f"{config:<20} {m['precision']:.3f}  {m['recall']:.3f}  {m['f1']:.3f}  {m['tp']:<4} {m['fp']:<4} {m['fn']:<4} {m['tn']:<4}")

    if 'fp_reduction' in comparison:
        print("\n=== False Positive Reduction (Verifier) ===")
        print(f"FP (LLM no verifier): {comparison['fp_reduction']['fp_llm_no_verifier']}")
        print(f"FP (Full): {comparison['fp_reduction']['fp_full']}")
        print(f"Reduction: {comparison['fp_reduction']['absolute']} ({comparison['fp_reduction']['percentage']:.1f}%)")


def save_comparison_csv(comparison: Dict, output_path: Path):
    """Save comparison as CSV file."""
    import csv

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Config', 'Precision', 'Recall', 'F1', 'TP', 'FP', 'FN', 'TN'])

        for config in ['semgrep_only', 'llm_no_verifier', 'full']:
            if config not in comparison:
                continue
            m = comparison[config]['overall']
            writer.writerow([
                config,
                f"{m['precision']:.3f}",
                f"{m['recall']:.3f}",
                f"{m['f1']:.3f}",
                m['tp'],
                m['fp'],
                m['fn'],
                m['tn']
            ])

    print(f"Comparison CSV saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Run ablation study comparing pipeline configurations"
    )
    parser.add_argument(
        '--manifest',
        type=Path,
        required=True,
        help="Path to manifest.json"
    )
    parser.add_argument(
        '--results-base',
        type=Path,
        default=Path("results/raw"),
        help="Base directory for results (default: results/raw)"
    )
    parser.add_argument(
        '--run-id',
        type=str,
        help="Run ID to use (default: latest run for each config)"
    )
    parser.add_argument(
        '--output',
        type=Path,
        help="Output comparison CSV file"
    )
    parser.add_argument(
        '--tolerance',
        type=int,
        default=5,
        help="Line range tolerance (default: 5)"
    )

    args = parser.parse_args()

    # Load manifest
    manifest = load_manifest(args.manifest)
    print(f"Loaded {len(manifest)} samples from manifest")

    # Find results directories for each config
    results_dirs = {}
    for config in ['semgrep_only', 'llm_no_verifier', 'full']:
        config_dir = args.results_base / config

        if not config_dir.exists():
            print(f"WARNING: Config directory not found: {config_dir}")
            continue

        # Find run directory
        if args.run_id:
            run_dir = config_dir / args.run_id
        else:
            # Use latest run
            run_dirs = sorted([d for d in config_dir.iterdir() if d.is_dir()])
            if not run_dirs:
                print(f"WARNING: No runs found for config {config}")
                continue
            run_dir = run_dirs[-1]

        if not run_dir.exists():
            print(f"WARNING: Run directory not found: {run_dir}")
            continue

        results_dirs[config] = run_dir
        print(f"Using results for {config}: {run_dir}")

    if not results_dirs:
        print("ERROR: No valid results directories found")
        sys.exit(1)

    # Compare configs
    comparison = compare_configs(manifest, results_dirs, args.tolerance)

    # Print comparison
    print_comparison_table(comparison)

    # Save CSV if requested
    if args.output:
        save_comparison_csv(comparison, args.output)


if __name__ == "__main__":
    import sys
    main()
