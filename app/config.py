import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_DIR = BASE_DIR / "workspace"
SYSTEM_PROMPT_PATH = BASE_DIR / "config" / "system_prompt.txt"

MODEL = os.getenv("MODEL", "gpt-4.1-mini")
AGENT_NAME = os.getenv("AGENT_NAME", "igorpetersson-codeagent")
MAX_STEPS = int(os.getenv("MAX_STEPS", "10"))
MAX_TOOL_OUTPUT_CHARS = int(os.getenv("MAX_TOOL_OUTPUT_CHARS", "4000"))
REQUIRE_TOOL_CONFIRMATION = os.getenv("REQUIRE_TOOL_CONFIRMATION", "true").lower() == "true"

EDITABLE_PATHS = [
    WORKSPACE_DIR,
    BASE_DIR / "app",
    BASE_DIR / "README.md",
    BASE_DIR / "requirements.txt",
]
