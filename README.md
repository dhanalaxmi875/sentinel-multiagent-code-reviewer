# Multi-Agent Code Review

An AI-powered code review system that uses a team of specialized agents — built with [LangGraph](https://github.com/langchain-ai/langgraph) and Claude — to analyze a code diff and produce a structured, prioritized review.

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
pip install git+https://github.com/alanchn31/multi-agent-code-review.git
export ANTHROPIC_API_KEY=sk-ant-...
```

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

Add the workflow file to any repo and it will post an AI review as a comment on every PR automatically.

**1. Copy the workflow file into your repo:**
```bash
mkdir -p .github/workflows
curl -o .github/workflows/code_review.yml \
  https://raw.githubusercontent.com/alanchn31/multi-agent-code-review/main/.github/workflows/code_review.yml
```

**2. Add your API key as a GitHub secret:**

Go to your repo → Settings → Secrets → Actions → New secret:
- Name: `ANTHROPIC_API_KEY`
- Value: your Anthropic API key

**3. Open a PR** — the bot will comment with the full review automatically.

---

## Setup (for development / running the demo)

**Requirements:** Python 3.11+

```bash
# 1. Clone and enter the directory
git clone https://github.com/alanchn31/multi-agent-code-review.git
cd multi-agent-code-review

# 2. Install dependencies and register the project on your Python path
pip install -r requirements.txt
pip install -e .

# 3. Configure your API key
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY=your_key_here
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

After installing (`pip install -e .` or `pip install git+https://github.com/alanchn31/multi-agent-code-review.git`):

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

### Model
All agents use `claude-haiku-4-5-20251001` at `temperature=0` for deterministic, cost-efficient output. The model is defined once in `src/config.py` — change it there to upgrade all agents simultaneously.

## Dependencies

| Package | Purpose |
|---|---|
| `langgraph` | Multi-agent graph orchestration |
| `langchain-anthropic` | Claude model integration |
| `langchain-core` | Message types and base interfaces |
| `anthropic` | Anthropic Python SDK |
| `python-dotenv` | `.env` file loading |
