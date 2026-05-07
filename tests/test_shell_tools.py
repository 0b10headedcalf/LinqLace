from tools.shell_tools import run_command


def test_allowed_simple(tmp_path):
    (tmp_path / "a.txt").write_text("hi")
    out = run_command(str(tmp_path), "ls")
    assert "a.txt" in out


def test_rejected_unknown(tmp_path):
    out = run_command(str(tmp_path), "rm -rf /")
    assert "rejected" in out.lower()


def test_no_shell_injection_semicolon(tmp_path):
    """`;` must not chain a second command — shell=False so semicolon is just an arg to git."""
    out = run_command(str(tmp_path), "git ; rm -rf /")
    # git treats ';' and 'rm' as args, doesn't execute rm
    assert "rm -rf" not in out or "not a git command" in out.lower() or "is not a git command" in out.lower()
    # The key invariant: subprocess didn't actually run rm. tmp_path still exists.
    assert tmp_path.exists()


def test_no_shell_injection_pipe(tmp_path):
    out = run_command(str(tmp_path), "ls | cat /etc/passwd")
    # `|` and `/etc/passwd` become args to ls, ls errors. /etc/passwd contents not in output.
    assert "root:" not in out


def test_no_command_substitution(tmp_path):
    out = run_command(str(tmp_path), "ls $(whoami)")
    # $() not expanded — passed literally to ls which fails to find a file named "$(whoami)"
    assert "$(whoami)" in out or "No such" in out or "cannot access" in out


def test_empty_command(tmp_path):
    assert "empty" in run_command(str(tmp_path), "   ").lower()


def test_unbalanced_quotes(tmp_path):
    out = run_command(str(tmp_path), 'git commit -m "unclosed')
    assert "parsing" in out.lower() or "rejected" in out.lower()


def test_disallowed_program_with_path(tmp_path):
    """Bypass attempt: invoke disallowed program via /bin/sh."""
    out = run_command(str(tmp_path), "/bin/sh -c 'rm -rf /'")
    assert "rejected" in out.lower()
    assert tmp_path.exists()
