import os
import subprocess
import httpx
from dotenv import load_dotenv

load_dotenv()

GITHUB_BASE = "https://api.github.com"


def _github_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}


def clone_repo(repo: str, github_token: str) -> tuple[str, str]:
    """
    Clone a GitHub repo into projects/.
    Returns (local_path, error_message).
    """
    os.makedirs("projects", exist_ok=True)
    repo_name = repo.split("/")[-1]
    local_path = f"projects/{repo_name}"

    if os.path.exists(local_path):
        return local_path, ""

    # Embed token in URL so private repos work
    clone_url = f"https://{github_token}@github.com/{repo}.git"

    result = subprocess.run(
        ["git", "clone", clone_url, local_path],
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode != 0:
        return "", f"Clone failed: {result.stderr}"

    return local_path, ""


def push_and_open_pr(
    local_path: str,
    repo: str,
    branch: str,
    title: str,
    body: str,
    github_token: str,
    base: str = "main",
) -> str:
    """Push current branch and open a PR."""

    # Push the branch
    result = subprocess.run(
        ["git", "push", "-u", "origin", branch],
        cwd=local_path,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return f"Push failed: {result.stderr}"

    # Open the PR via GitHub API
    response = httpx.post(
        f"{GITHUB_BASE}/repos/{repo}/pulls",
        headers=_github_headers(github_token),
        json={"title": title, "body": body, "head": branch, "base": base},
    )

    if response.status_code != 201:
        return f"PR creation failed: {response.text}"

    pr = response.json()
    return pr["html_url"]


GIT_TOOL_DEFINITIONS = [
    {
        "name": "clone_repo",
        "description": (
            "Clone a GitHub repository so the agent can work on it locally. "
            "Call this when the user mentions a repo they want to work on."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": "GitHub repo in owner/name format e.g. alice/resy-bot",
                }
            },
            "required": ["repo"],
        },
    },
    {
        "name": "push_and_open_pr",
        "description": "Push the current branch and open a pull request. Call this when work is complete.",
        "input_schema": {
            "type": "object",
            "properties": {
                "branch": {"type": "string", "description": "Branch name to push"},
                "title": {"type": "string", "description": "PR title"},
                "body": {
                    "type": "string",
                    "description": "PR description summarizing changes",
                },
            },
            "required": ["branch", "title", "body"],
        },
    },
]
