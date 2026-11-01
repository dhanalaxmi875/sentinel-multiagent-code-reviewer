# Datasets Documentation

This document describes the security vulnerability datasets downloaded for evaluation.

## SecurityEval

**Source**: https://github.com/s2e-lab/SecurityEval
**License**: Not specified in repository
**Language**: Python
**Format**: JSONL (dataset.jsonl)

### Description
SecurityEval contains 121 prompts for 69 CWEs with insecure code examples. Each sample includes:
- `ID`: Unique identifier (e.g., "CWE-020_author_1.py")
- `Prompt`: Prompt for code generation
- `Insecure_code`: Vulnerable code that may be generated

### Sample Counts per CWE
The dataset covers 69 CWEs with approximately 1-2 samples per CWE. Common CWEs include:
- CWE-20 (Improper Input Validation)
- CWE-22 (Path Traversal)
- CWE-78 (OS Command Injection)
- CWE-79 (Cross-site Scripting)
- CWE-89 (SQL Injection)
- CWE-90 (LDAP Injection)
- CWE-327 (Use of a Broken or Risky Cryptographic Algorithm)

### Limitations
**CRITICAL**: This dataset only contains vulnerable code samples. It does NOT include safe/fixed versions of the code. This means:
- Precision cannot be computed (no safe samples to detect false positives)
- Only recall can be measured (can we detect the vulnerabilities)
- Not suitable for full TP/FP/FN/TN evaluation

### Usage
This dataset is suitable for recall-only evaluation but cannot support precision measurement.

---

## CVEfixes

**Source**: https://github.com/secureIT-project/CVEfixes
**Data Download**: https://zenodo.org/records/13118970 (DOI: 10.5281/zenodo.4476563)
**License**: Other (see repository)
**Language**: Multi-language (Python, C, C++, Java, Ruby, Go)
**Format**: SQLite database (SQL dump)

### Description
CVEfixes is a comprehensive vulnerability dataset automatically collected from CVE records in NVD. It covers:
- 12,107 vulnerability fixing commits
- 4,249 open source projects
- 11,873 CVEs
- 272 different CWE types
- Source code before and after fixes at commit, file, and method level

### Sample Counts per CWE
The dataset includes Python vulnerabilities across many CWEs. Based on the paper:
- Common CWEs include SQL injection (CWE-89), command injection (CWE-78), XSS (CWE-79), path traversal (CWE-22), etc.
- Exact counts per CWE require querying the SQLite database

### Current Status
**LIMITATION**: The GitHub repository contains only the data collection code. The actual dataset SQL dump must be downloaded separately from Zenodo (~4GB compressed).

To download the dataset:
1. Visit https://zenodo.org/records/13118970
2. Download the SQL dump file
3. Convert to SQLite using: `gzcat Data/CVEfixes.sql.gz | sqlite3 Data/CVEfixes.db`

### Usage
Once the SQL dump is downloaded and converted, this dataset provides:
- Vulnerable code (before fix)
- Fixed code (after fix)
- CWE labels
- Suitable for full precision/recall evaluation

---

## OWASP Benchmark

**Source**: https://github.com/OWASP-Benchmark/BenchmarkJava
**License**: GNU GPL v2.0
**Language**: Java
**Format**: CSV (expectedresults-1.2.csv)

### Description
OWASP Benchmark is a Java test suite designed to verify the speed and accuracy of vulnerability detection tools. It includes:
- 2,700+ test cases
- Expected results CSV with vulnerability status (true/false) and CWE
- Exploitable vulnerabilities for fair testing

### Sample Counts per CWE
Based on expectedresults-1.2.csv:
- CWE-22 (Path Traversal): ~200 samples
- CWE-78 (OS Command Injection): ~200 samples
- CWE-79 (Cross-site Scripting): ~300 samples
- CWE-89 (SQL Injection): ~200 samples
- CWE-90 (LDAP Injection): ~50 samples
- CWE-327 (Weak Cryptography): ~100 samples
- CWE-328 (Reversible One-Way Hash): ~150 samples
- CWE-330 (Use of Insufficiently Random Values): ~100 samples
- CWE-501 (Trust Boundary Violation): ~100 samples
- CWE-614 (Insecure Cookie): ~50 samples

### Limitations
**CRITICAL**: This dataset is Java-only. SentinelCode is designed for Python code review.
- Python-specific agents may not detect Java vulnerabilities accurately
- Semgrep Python rules won't apply to Java code
- Only suitable if we extend SentinelCode to support Java

### Usage
This dataset is suitable for evaluation only if:
1. SentinelCode is extended to support Java
2. Or we use this as a baseline for comparison with other tools

---

## Dataset Limitations Summary

| Dataset | Language | Vulnerable Samples | Safe Samples | CWE Labels | Usability |
|---------|----------|-------------------|--------------|------------|-----------|
| SecurityEval | Python | Yes (121) | **No** | Yes | Limited (recall only) |
| CVEfixes | Multi (incl. Python) | Yes | Yes | Yes | **Yes** (requires Zenodo download) |
| OWASP Benchmark | Java | Yes | Yes | Yes | No (wrong language) |

## Evaluation Strategy (Final Decision)

Given the dataset limitations and bandwidth constraints, the evaluation harness uses the following strategy:

### 1. SecurityEval (Python) - Recall-Only Supplement
- **Status**: Included
- **Usage**: Recall-only evaluation
- **Limitation**: No safe/fixed versions → cannot compute precision or F1
- **Reporting**: Clearly labelled as recall-only, excluded from precision/F1 aggregates
- **Sample Count**: 121 vulnerable samples across 69 CWEs

### 2. OWASP Benchmark (Java) - Full Evaluation
- **Status**: Included
- **Usage**: Full precision/recall/F1 evaluation
- **Language**: Java (reported separately)
- **Approach**: Parse expected-results CSV, create balanced subset (~30 vulnerable + 30 safe per CWE)
- **Sample Count**: ~2700+ test cases, balanced per CWE
- **Note**: Orchestrator updated to include .java files for Security agent activation

### 3. CVEfixes (Python) - Future Work
- **Status**: Infrastructure prepared, dataset not downloaded
- **Reason**: 11.8GB download would take ~10 hours at current bandwidth
- **Infrastructure**: `load_cvefixes.py` written to work with pre-extracted Python subset
- **Requirements**: User provides local path to JSON/CSV with method-level before/after code + CWE
- **Documentation**: See `load_cvefixes.py` for expected schema
- **Future**: When bandwidth/time permits, download from Zenodo DOI: 10.5281/zenodo.4476563 (v1.0.8)

### Semgrep Rules by Language

| Language | Semgrep Rule Set | Status |
|----------|-----------------|--------|
| Python | `p/python`, `p/owasp-top-ten`, custom rules | ✓ Active |
| Java | Not supported by current Semgrep config | ⚠️ Will not run |
| C/C++ | Not supported by current Semgrep config | ⚠️ Will not run |

**Note**: For OWASP Benchmark (Java), the Security agent will run via LLM analysis, but Semgrep static analysis will not apply since our Semgrep configuration is Python-only.

## Next Steps

To proceed with CVEfixes in the future:
1. Download from Zenodo: https://zenodo.org/records/13118970/files/CVEfixes_v1.0.8.zip (11.8GB)
2. Extract SQL dump and load into SQLite
3. Extract Python method-level before/after pairs with CWE labels
4. Export to JSON/CSV format compatible with `load_cvefixes.py`
5. Run the evaluation harness with CVEfixes data
