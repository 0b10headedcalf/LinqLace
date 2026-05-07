import subprocess
from unittest.mock import patch
import pytest
from tools.git_tools import _origin_repo, clone_repo, push_and_open_pr


def _git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)


@pytest.fixture
def repo_with_origin(tmp_path):
    repo = tmp_path / "myrepo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "remote", "add", "origin", "https://github.com/alice/myrepo.git")
    return repo


def test_origin_repo_https(repo_with_origin):
    assert _origin_repo(str(repo_with_origin)) == "alice/myrepo"


def test_origin_repo_ssh(tmp_path):
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "remote", "add", "origin", "git@github.com:bob/proj.git")
    assert _origin_repo(str(repo)) == "bob/proj"


def test_origin_repo_no_remote(tmp_path):
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-q")
    assert _origin_repo(str(repo)) is None


def test_clone_repo_token_not_in_config(tmp_path, monkeypatch):
    """Critical: token must not land in .git/config."""
    monkeypatch.chdir(tmp_path)
    # Set up a local "remote" repo to clone.
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)

    # Patch _git_with_auth to clone from local path instead of github.com — but still
    # pass through the same -c argv so we can verify token isolation.
    real_run = subprocess.run

    captured_argv = {}

    def fake_run(argv, **kw):
        captured_argv["argv"] = argv
        # Replace github URL with our local bare repo
        argv = [a if not a.endswith(".git") or "github.com" not in a else str(remote) for a in argv]
        return real_run(argv, **kw)

    with patch("tools.git_tools.subprocess.run", side_effect=fake_run):
        local_path, err = clone_repo("alice/remote", "SECRET_TOKEN_XYZ")

    assert err == "" or "already exists" in err
    # Token was passed via -c extraheader, not embedded in URL
    argv = captured_argv["argv"]
    assert any("extraheader" in a and "SECRET_TOKEN_XYZ" in a for a in argv)
    # Clone URL itself contains no token (only the -c extraheader does)
    url_args = [a for a in argv if a.startswith(("https://", "http://"))]
    for u in url_args:
        assert "SECRET_TOKEN_XYZ" not in u

    # And .git/config has no token
    config_path = tmp_path / "projects" / "remote" / ".git" / "config"
    if config_path.exists():
        assert "SECRET_TOKEN_XYZ" not in config_path.read_text()


def test_push_and_open_pr_no_origin(tmp_path):
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-q")
    out = push_and_open_pr(
        local_path=str(repo),
        branch="feature",
        title="t",
        body="b",
        github_token="tok",
    )
    assert "could not determine repo" in out
