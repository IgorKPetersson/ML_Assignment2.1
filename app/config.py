import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_DIR = BASE_DIR / "workspace"
SYSTEM_PROMPT_PATH = BASE_DIR / "config" / "system_prompt.txt"

MODEL = os.getenv("MODEL", "gpt-4.1-mini")
AGENT_NAME = os.getenv("AGENT_NAME", "igor-petersson-agent")
MAX_STEPS = int(os.getenv("MAX_STEPS", "10"))
MAX_TOOL_OUTPUT_CHARS = int(os.getenv("MAX_TOOL_OUTPUT_CHARS", "4000"))
MAX_CONTEXT_MESSAGES = int(os.getenv("MAX_CONTEXT_MESSAGES", "40"))
MAX_TOTAL_TOKENS = int(os.getenv("MAX_TOTAL_TOKENS", "200000"))
TOKEN_WARNING_RATIO = float(os.getenv("TOKEN_WARNING_RATIO", "0.8"))
ESTIMATED_COST_PER_1K_TOKENS = float(os.getenv("ESTIMATED_COST_PER_1K_TOKENS", "0"))
MAX_BLOCKED_TOOL_ATTEMPTS = int(os.getenv("MAX_BLOCKED_TOOL_ATTEMPTS", "2"))
REQUIRE_TOOL_CONFIRMATION = os.getenv("REQUIRE_TOOL_CONFIRMATION", "true").lower() == "true"
TOOL_APPROVAL_TIMEOUT_SECONDS = float(os.getenv("TOOL_APPROVAL_TIMEOUT_SECONDS", "0"))
DEBUG_AGENT = os.getenv("DEBUG_AGENT", "false").lower() == "true"
DEBUG_RUNTIME_TRACING = os.getenv("DEBUG_RUNTIME_TRACING", "false").lower() == "true"

MAX_SUBAGENTS = int(os.getenv("MAX_SUBAGENTS", "3"))
SUBAGENT_TIMEOUT_SECONDS = int(os.getenv("SUBAGENT_TIMEOUT_SECONDS", "60"))
SUBAGENT_EVIDENCE_CHARS = int(os.getenv("SUBAGENT_EVIDENCE_CHARS", "6000"))

HUB_URL = os.getenv("HUB_URL", "https://wb48jtfnjng6on-8080.proxy.runpod.net").rstrip("/")
HUB_PASSWORD = os.getenv("HUB_PASSWORD", "")
HUB_POLL_SECONDS = float(os.getenv("HUB_POLL_SECONDS", "4"))
HUB_MIN_REQUEST_INTERVAL = float(os.getenv("HUB_MIN_REQUEST_INTERVAL", "1.1"))
HUB_MAX_MESSAGES_SENT = int(os.getenv("HUB_MAX_MESSAGES_SENT", "5"))
HUB_MAX_MODEL_CALLS = int(os.getenv("HUB_MAX_MODEL_CALLS", "20"))
HUB_MAX_TOTAL_TOKENS = int(os.getenv("HUB_MAX_TOTAL_TOKENS", "20000"))
HUB_MAX_CONTEXT_MESSAGES = int(os.getenv("HUB_MAX_CONTEXT_MESSAGES", "20"))
HUB_MAX_POST_CHARS = int(os.getenv("HUB_MAX_POST_CHARS", "4096"))
HUB_INTERACTIVE_CONTROLS = os.getenv("HUB_INTERACTIVE_CONTROLS", "true").lower() == "true"
HUB_SYNC_ON_START = os.getenv("HUB_SYNC_ON_START", "true").lower() == "true"
HUB_BROADCAST_TRIGGERS = [
    trigger.strip().lower()
    for trigger in os.getenv(
        "HUB_BROADCAST_TRIGGERS",
        "all agents,alla agenter,attention agents,agents:",
    ).split(",")
    if trigger.strip()
]

EDITABLE_PATHS = [
    WORKSPACE_DIR,
    BASE_DIR / "app",
    BASE_DIR / "README.md",
    BASE_DIR / "requirements.txt",
]
