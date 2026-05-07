import shlex
import subprocess

ALLOWED_COMMANDS = {
    "git",
    "pytest",
    "python",
    "python3",
    "pip",
    "ls",
    "cat",
    "find",
    "grep",
    "mkdir",
    "touch",
    "mv",
    "cp",
}


def run_command(local_path: str, command: str) -> str:
    """
    Run a shell command inside the repo directory.
    No shell — argv parsed by shlex, first token must be in allowlist.
    Blocks shell metacharacter injection (;, &&, |, $(), backticks).
    """
    try:
        argv = shlex.split(command)
    except ValueError as e:
        return f"Error parsing command: {e}"

    if not argv:
        return "Error: empty command"

    program = argv[0]
    if program not in ALLOWED_COMMANDS:
        return (
            f"Command rejected: '{program}' not allowed. "
            f"Allowed: {sorted(ALLOWED_COMMANDS)}"
        )

    try:
        result = subprocess.run(
            argv,
            shell=False,
            cwd=local_path,
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout + result.stderr
        return output.strip() or "Command completed with no output"
    except subprocess.TimeoutExpired:
        return "Error: command timed out after 60 seconds"
    except FileNotFoundError:
        return f"Error: '{program}' not found on PATH"
    except Exception as e:
        return f"Error running command: {e}"


SHELL_TOOL_DEFINITIONS = [
    {
        "name": "run_command",
        "description": (
            "Run a shell command inside the repo. Use for git operations "
            "(git add, git commit, git checkout -b), running tests (pytest), "
            "and searching code (grep). No shell metacharacters — pass argv only."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Command to run e.g. 'git commit -m \"fix auth\"'",
                }
            },
            "required": ["command"],
        },
    }
]
