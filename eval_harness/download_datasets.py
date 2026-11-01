"""Download security vulnerability datasets for evaluation.

Downloads official datasets from their sources:
- SecurityEval (Python, CWE-labelled)
- CVEfixes (Python subset, real CVE fixes with CWE labels)
- OWASP Benchmark (Java, expected-results CSV with vulnerable/safe + CWE)

Dataset files are saved to eval_harness/datasets/ and not committed to git.
"""

import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
DATASETS_DIR = SCRIPT_DIR / "datasets"
DATASETS_DIR.mkdir(parents=True, exist_ok=True)


def download_securityeval() -> bool:
    """Download SecurityEval dataset (Python, CWE-labelled)."""
    # SecurityEval is available on GitHub at s2e-lab/SecurityEval
    # It's also available on HuggingFace
    target_dir = DATASETS_DIR / "SecurityEval"

    if target_dir.exists():
        print(f"SecurityEval already exists at {target_dir}")
        return True

    print("Downloading SecurityEval from GitHub...")
    try:
        subprocess.run(
            ["git", "clone", "https://github.com/s2e-lab/SecurityEval.git", str(target_dir)],
            check=True,
            capture_output=True,
            text=True,
        )
        print(f"  ✓ SecurityEval cloned to {target_dir}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Failed to clone SecurityEval: {e.stderr}")
        return False
    except FileNotFoundError:
        print("  ✗ Git not found. Please install git to clone SecurityEval.")
        return False


def download_cvefixes() -> bool:
    """Download CVEfixes dataset (Python subset, real CVE fixes with CWE labels)."""
    # CVEfixes is available on GitHub at secureIT-project/CVEfixes
    # The actual dataset is released via Zenodo (DOI: 10.5281/zenodo.4476563)
    # Current release: v1.0.8 (July 2024)
    # We'll clone the repository and download the SQL dump from Zenodo
    target_dir = DATASETS_DIR / "CVEfixes"

    if target_dir.exists():
        print(f"CVEfixes already exists at {target_dir}")
    else:
        print("Downloading CVEfixes from GitHub...")
        try:
            subprocess.run(
                ["git", "clone", "https://github.com/secureIT-project/CVEfixes.git", str(target_dir)],
                check=True,
                capture_output=True,
                text=True,
            )
            print(f"  ✓ CVEfixes cloned to {target_dir}")
        except subprocess.CalledProcessError as e:
            print(f"  ✗ Failed to clone CVEfixes: {e.stderr}")
            return False
        except FileNotFoundError:
            print("  ✗ Git not found. Please install git to clone CVEfixes.")
            return False

    # Download SQL dump from Zenodo
    # Using the latest version v1.0.8
    zenodo_url = "https://zenodo.org/record/13118970/files/CVEfixes.sql.gz"
    sql_dump_path = DATASETS_DIR / "CVEfixes.sql.gz"

    if sql_dump_path.exists():
        print(f"CVEfixes SQL dump already exists at {sql_dump_path}")
        return True

    print(f"Downloading CVEfixes SQL dump from Zenodo (v1.0.8, ~4GB)...")
    print(f"  URL: {zenodo_url}")
    print("  This may take several minutes...")

    try:
        from urllib.error import URLError, HTTPError

        def show_progress(block_num, block_size, total_size):
            downloaded = block_num * block_size
            if total_size > 0:
                percent = min(100, (downloaded / total_size) * 100)
                print(f"  Downloaded: {downloaded / (1024*1024):.1f} MB / {total_size / (1024*1024):.1f} MB ({percent:.1f}%)")

        urllib.request.urlretrieve(zenodo_url, sql_dump_path, show_progress)
        print(f"  ✓ SQL dump saved to {sql_dump_path}")
        return True
    except (URLError, HTTPError) as e:
        print(f"  ✗ Failed to download SQL dump: {e}")
        return False
    except Exception as e:
        print(f"  ✗ Error downloading SQL dump: {e}")
        return False


def download_owasp_benchmark() -> bool:
    """Download OWASP Benchmark (Java, expected-results CSV)."""
    # OWASP Benchmark is available on GitHub at OWASP-Benchmark/BenchmarkJava
    target_dir = DATASETS_DIR / "OWASP-Benchmark"

    if target_dir.exists():
        print(f"OWASP Benchmark already exists at {target_dir}")
        return True

    print("Downloading OWASP Benchmark from GitHub...")
    try:
        subprocess.run(
            ["git", "clone", "https://github.com/OWASP-Benchmark/BenchmarkJava.git", str(target_dir)],
            check=True,
            capture_output=True,
            text=True,
        )
        print(f"  ✓ OWASP Benchmark cloned to {target_dir}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Failed to clone OWASP Benchmark: {e.stderr}")
        return False
    except FileNotFoundError:
        print("  ✗ Git not found. Please install git to clone OWASP Benchmark.")
        return False


def main():
    """Download all datasets."""
    print("=" * 60)
    print("Downloading security vulnerability datasets")
    print("=" * 60)
    print()

    results = {}

    # SecurityEval
    print("1. SecurityEval (Python, CWE-labelled)")
    print("-" * 60)
    results["securityeval"] = download_securityeval()
    print()

    # CVEfixes
    print("2. CVEfixes (Python subset, real CVE fixes with CWE labels)")
    print("-" * 60)
    results["cvefixes"] = download_cvefixes()
    print()

    # OWASP Benchmark
    print("3. OWASP Benchmark (Java, expected-results CSV)")
    print("-" * 60)
    results["owasp_benchmark"] = download_owasp_benchmark()
    print()

    # Summary
    print("=" * 60)
    print("Download Summary")
    print("=" * 60)
    for name, success in results.items():
        status = "✓ SUCCESS" if success else "✗ FAILED"
        print(f"{name}: {status}")

    if all(results.values()):
        print("\nAll datasets downloaded successfully!")
        return 0
    else:
        print("\nSome datasets failed to download. See details above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
