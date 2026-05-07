from tools.file_tools import read_file, write_file, list_files, FS_TOOL_DEFINITIONS
from tools.shell_tools import run_command, SHELL_TOOL_DEFINITIONS
from tools.git_tools import clone_repo, push_and_open_pr, GIT_TOOL_DEFINITIONS


def execute_tool(name: str, inputs: dict, local_path: str, github_token: str) -> str:
    """Route a tool call by name to the correct function."""
    match name:
        case "read_file":
            return read_file(local_path, **inputs)
        case "write_file":
            return write_file(local_path, **inputs)
        case "list_files":
            return list_files(local_path, inputs.get("path", ""))
        case "run_command":
            return run_command(local_path, **inputs)
        case "clone_repo":
            path, err = clone_repo(inputs["repo"], github_token)
            return err if err else f"Cloned to {path}"
        case "push_and_open_pr":
            return push_and_open_pr(
                local_path=local_path,
                github_token=github_token,
                **inputs,
            )
        case _:
            return f"Unknown tool: {name}"
