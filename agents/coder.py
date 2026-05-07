from state import AgentState, TaskResult
from tools import FS_TOOL_DEFINITIONS, SHELL_TOOL_DEFINITIONS
from agents._base import run_agent

SYSTEM_PROMPT = """You are an expert software engineer.
You have been delegated a coding task by an orchestrator agent.

Your job:
1. Understand the task fully before writing any code
2. List files to orient yourself in the codebase
3. Read relevant files before making changes
4. Make focused, minimal changes — don't refactor things you weren't asked to touch
5. Always create a new branch before making changes: git checkout -b agent/<short-description>
6. Commit your changes with a clear message when done
7. Return a concise summary of exactly what you changed and why

You are operating inside a local git clone. All file paths are relative to the repo root.
Do not open PRs — the orchestrator handles that."""

TOOLS = FS_TOOL_DEFINITIONS + SHELL_TOOL_DEFINITIONS


def run_coder(state: AgentState, task: str) -> TaskResult:
    return run_agent(state, task, name="coder", system_prompt=SYSTEM_PROMPT, tools=TOOLS)
