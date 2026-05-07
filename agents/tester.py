from state import AgentState, TaskResult
from tools import FS_TOOL_DEFINITIONS, SHELL_TOOL_DEFINITIONS
from agents._base import run_agent

SYSTEM_PROMPT = """You are an expert in software testing.
You have been delegated a testing task.

Your job:
1. Read the code you're testing before writing any tests
2. Write tests that cover happy path, edge cases, and failure modes
3. Run the tests with pytest to verify they pass
4. Commit the tests to the current branch
5. Return a summary of what tests you wrote and their results

Never modify production code — only write test files."""

TOOLS = FS_TOOL_DEFINITIONS + SHELL_TOOL_DEFINITIONS


def run_tester(state: AgentState, task: str) -> TaskResult:
    return run_agent(state, task, name="tester", system_prompt=SYSTEM_PROMPT, tools=TOOLS)
