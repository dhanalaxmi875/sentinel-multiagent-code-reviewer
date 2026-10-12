import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# Local LLM configuration — SentinelCode (free Ollama setup)
# ============================================================
MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:14b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0"))

# ============================================================
# Original base-project configuration
# ============================================================
# Maximum diff characters per LLM review chunk
MAX_DIFF_CHARS = int(os.getenv("MAX_DIFF_CHARS", "12000"))

# Log file used by src/logger.py
LOG_FILE = os.getenv("LOG_FILE", "logs/code_review.log")