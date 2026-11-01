# Multi-Agent Code Review

An AI-powered code review system that uses a team of specialized agents — built with [LangGraph](https://github.com/langchain-ai/langgraph) and Ollama — to analyze a code diff and produce a structured, prioritized review.

## How It Works

A code diff flows through a pipeline of agents, each with a distinct responsibility:

```
                    ┌─────────────────┐
                    │   Orchestrator  │  Reads the diff + file paths,
                    │                 │  selects which agents to run
                    └────────┬────────┘
                             │ (conditional fan-out)
          ┌──────────────────┼──────────────────┐
          │                  │                  │
    ┌─────▼──────┐   ┌───────▼──────┐   ┌──────▼──────┐   ┌──────────────┐
    │  Bug &     │   │   Security   │   │    Code     │   │    Test      │
    │  Logic     │   │   Agent      │   │   Quality   │   │  Coverage    │
    │  Detector  │   │              │   │   Agent     │   │   Agent      │
    └─────┬──────┘   └───────┬──────┘   └──────┬──────┘   └──────┬───────┘
          │                  │                  │                  │
          └──────────────────┴──────────────────┴──────────────────┘
                                       │ (fan-in)
                               ┌───────▼────────┐
                               │   Summarizer   │  Merges all reports into
                               │                │  a prioritized review
                               └────────────────┘
```

The Orchestrator uses the file paths and diff content to decide which agents are relevant — for example, it will skip the Security agent for CSS-only changes and skip Test Coverage if no logic was added.

## Agents

| Agent | Responsibility |
|---|---|
| **Orchestrator** | Analyzes the diff, selects which specialist agents to activate, explains its routing decision |
| **Bug & Logic Detector** | Finds off-by-one errors, null dereferences, infinite loops, incorrect conditionals, wrong return values |
| **Security Agent** | Flags SQL injection, hardcoded secrets, command injection, insecure deserialization, XSS, auth flaws |
| **Code Quality Agent** | Reviews naming, function length, duplication, magic numbers, dead code, style guide violations |
| **Test Coverage Agent** | Identifies untested logic paths, missing edge cases, regression risks, and suggests test cases |
| **Summarizer** | Synthesizes all reports into a single review: Critical Issues → Suggestions → Nitpicks → Verdict |

## Project Structure

```
multi-agent-code-review/
├── pyproject.toml        # Editable install — fixes sys.path for all entry points
├── requirements.txt
├── .env.example
├── src/
│   ├── config.py         # MODEL name, log path, diff size limit
│   ├── logger.py         # Shared logging setup (file + terminal)
│   ├── chunker.py        # Diff truncation / token budget guard
│   ├── state.py          # Shared ReviewState TypedDict
│   ├── graph.py          # LangGraph StateGraph (fan-out / fan-in)
│   ├── main.py           # run_review() entry point
│   └── agents/
│       ├── orchestrator.py
│       ├── bug_detector.py
│       ├── security.py
│       ├── code_quality.py
│       ├── test_coverage.py
│       └── summarizer.py
├── evals/
│   ├── cases.py          # Keyword-based test cases
│   └── run_eval.py       # Eval runner — scores reviews against expected findings
└── examples/
    ├── app_before.py     # Clean original API (what's on main)
    ├── app_after.py      # PR version with intentional bugs and vulnerabilities
    └── sample_diff.py    # Generates unified diff from the two files using difflib
```

## Real-World Usage

There are two ways to use this tool without cloning the repo into your project.

### Option 1 — Install the CLI (any repo, one command)

Install once, use anywhere:

```bash
pip install git+https://github.com/dhanalaxmi875/sentinel-multiagent-code-reviewer.git
```

Run an Ollama server with the model configured through `OLLAMA_MODEL` (default: `qwen2.5-coder:14b`).

Then run from inside **any** git repository:

```bash
# Review your staged changes before committing
code-review

# Review everything on your branch vs main
code-review --branch main

# Review a specific commit
code-review --commit abc1234

# Review unstaged working-directory changes
code-review --unstaged

# Save the review to a file
code-review --branch main --output review.md
```

### Option 2 — GitHub Actions (automated PR reviews)

The `.github/workflows/sentinelcode.yml` workflow in this repository runs on pull requests and posts its report as a PR comment. It uses Ollama; by default, GitHub Actions installs Ollama and downloads `qwen2.5-coder:1.5b`. Set the repository variable `OLLAMA_MODEL` to choose a different model. If you use a hosted Ollama server, set `OLLAMA_BASE_URL` as a repository secret or variable.

---

## Setup (for development / running the demo)

**Requirements:** Python 3.11+

```bash
# 1. Clone and enter the directory
git clone https://github.com/dhanalaxmi875/sentinel-multiagent-code-reviewer.git
cd sentinel-multiagent-code-reviewer

# 2. Install dependencies and register the project on your Python path
pip install -r requirements.txt
pip install -e .

# 3. Configure your local Ollama model if needed
cp .env.example .env
# Set OLLAMA_MODEL and OLLAMA_BASE_URL to match your Ollama setup
```

## Usage

### Run the built-in example

The `examples/sample_diff.py` file contains a realistic diff with intentional bugs, security vulnerabilities, and quality issues — a good way to see all agents fire at once.

**Option A — directly (no CLI needed):**
```bash
python -m src.main
```

**Option B — via the `code-review` CLI:**
```bash
# 1. Export the sample diff to a file
python -c "from examples.sample_diff import SAMPLE_DIFF; open('sample.diff', 'w').write(SAMPLE_DIFF)"

# 2. Run the CLI against it
code-review --file sample.diff

# Optional: save the output to a file
code-review --file sample.diff --output review.md
```

### Use as a library

After installing (`pip install -e .` or `pip install git+https://github.com/dhanalaxmi875/sentinel-multiagent-code-reviewer.git`):

```python
from code_review import run_review

# Pass a unified diff string (e.g., from `git diff`)
diff = """
diff --git a/src/auth.py b/src/auth.py
...
"""

file_paths = ["src/auth.py", "src/db/queries.py"]

review = run_review(diff, file_paths)
print(review)
```

### Pipe from git

```bash
# Review the current staged changes
git diff --cached | python -c "
import sys
from src.main import run_review
diff = sys.stdin.read()
print(run_review(diff))
"
```

### Run the eval suite

```bash
python -m evals.run_eval
```

Runs 4 test cases (SQL injection, hardcoded secrets, off-by-one, clean code) and scores each review against expected keyword findings. Exits with code `0` if all pass, `1` if any fail.

## Demo

The built-in demo simulates a realistic code review scenario: a developer opens a PR to add a money transfer feature to a banking API. The diff is generated from two real Python files — `examples/app_before.py` (the clean original) and `examples/app_after.py` (the PR).

### The scenario

A developer adds four new things to the API:
- A money transfer endpoint
- An admin command runner
- A user session restore endpoint
- A permissions helper and a paginated user list

The code compiles and looks plausible on a quick skim. The agents catch what a human reviewer might miss.

### What each agent finds

| Finding | Caught by |
|---|---|
| `SECRET_KEY = "hardcoded_secret_12345"` — credential committed to source | Security |
| `"WHERE id = " + user_id` — SQL injection via string concatenation | Security + Bug |
| `subprocess.run(cmd, shell=True)` — command injection, any shell command can run | Security |
| `pickle.loads(raw)` — insecure deserialization of untrusted request body | Security |
| `transfer_funds` has no auth check — any user can drain any account | Security |
| `transfer_funds` allows negative `amount` — funds can be created from nothing | Bug |
| `get_users_page` starts at index `0` regardless of `page` — wrong pagination logic | Bug |
| `check_permissions(u, r, p, f, x)` — 4 levels of nesting, cryptic parameter names | Quality |
| `if user == None` instead of `is None` — PEP 8 violation | Quality |
| Zero tests for any new endpoint or function | Test Coverage |

### Run it

```bash
python -m src.main
```

Logs are written to `logs/review.log` in addition to the terminal.

### Project structure for the demo

```
examples/
├── app_before.py   # The clean original — what's on main
├── app_after.py    # The PR — what the reviewer sees
└── sample_diff.py  # Generates the unified diff from the two files using difflib
```

The diff is produced programmatically at import time, so `app_before.py` and `app_after.py` are genuine Python files you can open and read — not embedded strings.

### Demo video
[![Watch the video](https://img.youtube.com/vi/YfO72C8kmJw/0.jpg)](https://youtu.be/YfO72C8kmJw)


## Output Format

The Summarizer produces a structured review:

```
## Code Review Summary

### Critical Issues  (must fix before merge)
1. [CRITICAL] SQL injection in fetch_user() — user_id is concatenated directly into the query string...

### Suggestions  (should fix, improves quality)
1. transfer_funds() has no balance validation — negative amounts or overdrafts are not checked...

### Nitpicks  (optional, minor improvements)
1. check_user_permissions() uses single-character parameter names (u, r, p, f, x)...

### Verdict
REQUEST CHANGES — multiple critical security vulnerabilities must be resolved before this can merge.
```

## Design Notes

### Parallelism
Specialist agents run concurrently via LangGraph's `add_conditional_edges` fan-out. The Orchestrator selects only the relevant agents, so a CSS-only diff never triggers the Security agent. This is already the default execution model — no extra work required.

### Contradiction handling
The Summarizer is the single point where all agent outputs meet. Its system prompt contains explicit resolution rules: escalate to the higher severity when agents disagree on a finding's priority; present both options when refactor advice conflicts; flag unresolved disagreements as `NEEDS DISCUSSION`. This is simpler and cheaper than a separate arbitration agent.

### Context passing and token budget
Large diffs are preprocessed by `src/chunker.py` before entering the graph. It splits the diff by file (`diff --git` blocks), then trims each block proportionally if the total exceeds `MAX_DIFF_CHARS` (default 40,000). A warning header is prepended so agents know context may be incomplete. To change the limit: edit `src/config.py`.

### Logging
All agent activity is written to both the terminal and `logs/review.log` via Python's standard `logging` module. The log file persists across runs, making it easy to audit what each agent said for a given review. `logs/` is gitignored.

### Evaluation
`evals/run_eval.py` runs the full pipeline against 4 fixed test cases and scores each review with keyword matching — no second LLM call needed. Cases cover SQL injection, hardcoded secrets, off-by-one errors, and a clean-code baseline that should not raise false alarms. This is intentionally simple: the goal is a repeatable regression check, not a complete benchmark.

## Run the SentinelCode web app

The `backend/` folder contains a FastAPI web API and review worker. The built frontend is served by the backend when `frontend/dist/` exists. Start the backend from the `backend` folder so its `app` package resolves correctly.

### Windows PowerShell

From the repository root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
Set-Location backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000). Create an account at `/register` or sign in at `/login`; review, history, and stats APIs require a signed-in account. Accounts and review data are stored in SQLite. The API health check is [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health), and interactive API docs are at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

The real review pipeline uses Ollama. Install/start Ollama separately and download the configured model (the checked-in `.env` selects `qwen2.5-coder:7b`):

```powershell
ollama pull qwen2.5-coder:7b
```

If PowerShell blocks virtual-environment activation, run the Python executable directly instead: `..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000` while in `backend`. To try the web app without Ollama, set `$env:SENTINEL_FAKE_PIPELINE = "true"` before starting the server; this returns deterministic demo reviews and does not run the AI review pipeline.

The backend creates its SQLite database at `backend/data/reviews.sqlite3` by default. Set `DATABASE_URL` to change the location. `frontend/` currently contains the built static site rather than its original component source. To preview that built site through Vite, open a second terminal in `frontend` and run `npm install` followed by `npm run dev`; the dev server proxies `/api` requests to the backend on port 8000.

For the faculty demo, upload `sample_code_review.diff`. The backend recognizes that exact diff (including Windows line endings), waits three seconds, and displays its prepared review. Other uploaded diffs continue through the normal review pipeline.

Authentication endpoints are `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/logout`, and `GET /api/auth/me`. Passwords are stored as salted PBKDF2 hashes; the browser receives a random, HTTP-only session cookie with a 14-day expiry. Existing anonymous reviews in that browser are attached to the account when it first signs in. Set `COOKIE_SECURE=true` when serving the app over HTTPS.

### Model
All agents use the Ollama model configured by `OLLAMA_MODEL` at `temperature=0`. The local default is `qwen2.5-coder:14b`; the GitHub Actions workflow uses `qwen2.5-coder:1.5b` unless overridden by a repository variable.

## Dependencies

| Package | Purpose |
|---|---|
| `langgraph` | Multi-agent graph orchestration |
| `langchain-ollama` | Local Ollama model integration |
| `langchain-core` | Message types and base interfaces |
| `python-dotenv` | `.env` file loading |
