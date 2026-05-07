import os


def _safe_join(local_path: str, path: str) -> str | None:
    """Resolve `path` under `local_path`. Returns None if it escapes the repo."""
    root = os.path.realpath(local_path)
    full = os.path.realpath(os.path.join(root, path))
    if full != root and not full.startswith(root + os.sep):
        return None
    return full


def read_file(local_path: str, path: str) -> str:
    full_path = _safe_join(local_path, path)
    if full_path is None:
        return f"Error: {path} escapes the repo"
    if not os.path.exists(full_path):
        return f"Error: {path} does not exist"
    with open(full_path, "r") as f:
        return f.read()


def write_file(local_path: str, path: str, content: str) -> str:
    full_path = _safe_join(local_path, path)
    if full_path is None:
        return f"Error: {path} escapes the repo"
    parent = os.path.dirname(full_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(full_path, "w") as f:
        f.write(content)
    return f"Successfully wrote {path}"


def list_files(local_path: str, path: str = "") -> str:
    full_path = _safe_join(local_path, path)
    if full_path is None:
        return f"Error: {path} escapes the repo"
    if not os.path.exists(full_path):
        return f"Error: {path} does not exist"
    items = []
    for entry in os.scandir(full_path):
        kind = "DIR" if entry.is_dir() else "FILE"
        items.append(f"{kind} {entry.name}")
    return "\n".join(items)


FS_TOOL_DEFINITIONS = [
    {
        "name": "read_file",
        "description": "Read the contents of a file from the local repo.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path relative to repo root e.g. src/auth.py",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Write content to a file in the local repo. Creates the file if it doesn't exist.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path relative to repo root",
                },
                "content": {
                    "type": "string",
                    "description": "Full file content to write",
                },
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "list_files",
        "description": "List files and directories at a path in the repo. Use empty string for root.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path to list. Empty string for root.",
                }
            },
            "required": [],
        },
    },
]
