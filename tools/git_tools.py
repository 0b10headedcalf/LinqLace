import os
import re
import subprocess
import httpx
from dotenv import load_dotenv

load_dotenv()

GITHUB_BASE = "https://api.github.com"


def _github_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}


def _git_with_auth(token: str, args: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Run git with an in-memory Authorization header — token never written to disk."""
    extraheader = f"http.https://github.com/.extraheader=Authorization: Bearer {token}"
    return subprocess.run(
        ["git", "-c", extraheader, *args],
        capture_output=True,
        text=True,
        **kwargs,
    )


def _origin_repo(local_path: str) -> str | None:
    """Parse owner/name from origin remote URL."""
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=local_path,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    url = result.stdout.strip()
    # Match https://github.com/owner/name(.git)? or git@github.com:owner/name(.git)?
    m = re.search(r"github\.com[:/]([^/]+)/([^/.]+?)(?:\.git)?/?$", url)
    if not m:
        return None
    return f"{m.group(1)}/{m.group(2)}"


def clone_repo(repo: str, github_token: str) -> tuple[str, str]:
    """
    Clone a GitHub repo into projects/.
    Token is passed via -c extraheader so it never lands in .git/config.
    Returns (local_path, error_message).
    """
    os.makedirs("projects", exist_ok=True)
    repo_name = repo.split("/")[-1]
    local_path = f"projects/{repo_name}"

    if os.path.exists(local_path):
        return local_path, ""

    clone_url = f"https://github.com/{repo}.git"

    result = _git_with_auth(
        github_token,
        ["clone", clone_url, local_path],
        timeout=120,
    )

    if result.returncode != 0:
        return "", f"Clone failed: {result.stderr}"

    return local_path, ""


def push_and_open_pr(
    local_path: str,
    branch: str,
    title: str,
    body: str,
    github_token: str,
    base: str = "main",
    repo: str | None = None,
) -> str:
    """Push current branch and open a PR. Repo inferred from origin if not provided."""
    repo = repo or _origin_repo(local_path)
    if not repo:
        return "Push failed: could not determine repo from origin remote"

    push = _git_with_auth(
        github_token,
        ["push", "-u", "origin", branch],
        cwd=local_path,
    )
    if push.returncode != 0:
        return f"Push failed: {push.stderr}"

    response = httpx.post(
        f"{GITHUB_BASE}/repos/{repo}/pulls",
        headers=_github_headers(github_token),
        json={"title": title, "body": body, "head": branch, "base": base},
    )

    if response.status_code != 201:
        return f"PR creation failed: {response.text}"

    return response.json()["html_url"]


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
        "description": (
            "Push the current branch and open a pull request. "
            "Repo is auto-detected from the local origin remote. "
            "Call this when work is complete."
        ),
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
