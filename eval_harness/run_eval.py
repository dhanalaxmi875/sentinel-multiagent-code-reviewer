"""Evaluation harness for running SentinelCode on test datasets.

Runs the pipeline on manifest samples, saves raw findings JSON,
and supports multiple configurations for ablation studies.

Configs:
- full: Full pipeline (orchestrator -> specialists + semgrep -> verifier -> summarizer)
- semgrep_only: Semgrep static analysis only (no LLM agents)
- llm_no_verifier: LLM specialists without verifier
"""

import argparse
import json
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import hashlib

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
MANIFEST_PATH = SCRIPT_DIR / "manifest.json"
RESULTS_DIR = SCRIPT_DIR / "results"
RAW_RESULTS_DIR = RESULTS_DIR / "raw"


def get_git_commit() -> str:
    """Get current git commit hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def get_model_info() -> Dict:
    """Get model information from config."""
    from src.config import MODEL, TEMPERATURE
    return {
        "model": MODEL,
        "temperature": TEMPERATURE
    }


def run_review_on_diff(
    diff_content: str,
    file_paths: List[str],
    config: str
) -> str:
    """Run SentinelCode review on a diff with specified config."""
    # Add project root to sys.path
    sys.path.insert(0, str(PROJECT_ROOT))

    from src.main import run_review
    from src.graph import build_graph

    # For different configs, we'd need to modify the graph
    # For now, use the default full pipeline
    # TODO: Implement config-specific graph modifications
    return run_review(diff_content, file_paths)


def load_manifest(manifest_path: Path) -> List[Dict]:
    """Load manifest from JSON file."""
    with open(manifest_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def filter_manifest(
    manifest: List[Dict],
    dataset: Optional[str] = None,
    cwe: Optional[str] = None,
    limit: Optional[int] = None
) -> List[Dict]:
    """Filter manifest by dataset, CWE, and limit."""
    filtered = manifest

    if dataset:
        filtered = [s for s in filtered if s['dataset'] == dataset]

    if cwe:
        filtered = [s for s in filtered if s['cwe'] == cwe]

    if limit:
        filtered = filtered[:limit]

    return filtered


def get_output_path(
    config: str,
    run_id: str,
    sample_id: str
) -> Path:
    """Get output path for a sample's results."""
    config_dir = RAW_RESULTS_DIR / config / run_id
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / f"{sample_id}.json"


def run_sample(
    sample: Dict,
    config: str,
    run_id: str,
    resume: bool = False
) -> Optional[Dict]:
    """Run evaluation on a single sample."""
    sample_id = sample['id']
    output_path = get_output_path(config, run_id, sample_id)

    # Skip if resume and output exists
    if resume and output_path.exists():
        print(f"  Skipping {sample_id} (already exists)")
        with open(output_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    print(f"  Processing {sample_id}...")

    # Load diff
    diff_path = SCRIPT_DIR / sample['diff_path']
    diff_content = diff_path.read_text(encoding='utf-8')

    # Get file paths
    file_paths = [sample['file']] if sample.get('file') else []

    # Run review
    try:
        review = run_review_on_diff(diff_content, file_paths, config)

        # Parse structured findings
        sys.path.insert(0, str(PROJECT_ROOT))
        from src.structured_findings import parse_accepted_findings
        findings = parse_accepted_findings(review, diff_content)

        # Create result
        result = {
            "sample_id": sample_id,
            "config": config,
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(),
            "git_commit": get_git_commit(),
            "model": get_model_info(),
            "label": sample,
            "review": review,
            "findings": findings
        }

        # Save result
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2)

        return result

    except Exception as e:
        print(f"  ERROR processing {sample_id}: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Run evaluation harness"
    )
    parser.add_argument(
        '--config',
        choices=['full', 'semgrep_only', 'llm_no_verifier'],
        default='full',
        help="Pipeline configuration (default: full)"
    )
    parser.add_argument(
        '--runs',
        type=int,
        default=3,
        help="Number of runs (default: 3)"
    )
    parser.add_argument(
        '--limit',
        type=int,
        help="Limit number of samples to process"
    )
    parser.add_argument(
        '--dataset',
        choices=['securityeval', 'owasp_benchmark'],
        help="Filter by dataset"
    )
    parser.add_argument(
        '--cwe',
        help="Filter by CWE (e.g., CWE-89)"
    )
    parser.add_argument(
        '--resume',
        action='store_true',
        help="Skip samples that already have results"
    )
    parser.add_argument(
        '--smoke',
        action='store_true',
        help="Run smoke test with 10 samples"
    )
    parser.add_argument(
        '--manifest',
        type=Path,
        default=MANIFEST_PATH,
        help="Path to manifest.json"
    )

    args = parser.parse_args()

    # Load manifest
    if not args.manifest.exists():
        print(f"ERROR: Manifest not found: {args.manifest}")
        sys.exit(1)

    manifest = load_manifest(args.manifest)
    print(f"Loaded {len(manifest)} samples from manifest")

    # Filter manifest
    if args.smoke:
        args.limit = 10
        print("Smoke test mode: limiting to 10 samples")

    filtered = filter_manifest(
        manifest,
        dataset=args.dataset,
        cwe=args.cwe,
        limit=args.limit
    )

    print(f"Filtered to {len(filtered)} samples")

    if args.dataset:
        print(f"  Dataset: {args.dataset}")
    if args.cwe:
        print(f"  CWE: {args.cwe}")
    if args.limit:
        print(f"  Limit: {args.limit}")

    # Run evaluation
    config = args.config
    run_id = str(uuid.uuid4())[:8]

    print(f"\nRunning evaluation with config: {config}")
    print(f"Run ID: {run_id}")
    print(f"Number of runs: {args.runs}")

    for run in range(args.runs):
        print(f"\n=== Run {run + 1}/{args.runs} ===")

        for sample in filtered:
            result = run_sample(sample, config, run_id, args.resume)
            if result is None:
                print(f"  Failed to process {sample['id']}")

    print(f"\nEvaluation complete. Results saved to {RAW_RESULTS_DIR / config / run_id}")


if __name__ == "__main__":
    main()
