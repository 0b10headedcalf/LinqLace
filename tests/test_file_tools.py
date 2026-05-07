import os
from tools.file_tools import read_file, write_file, list_files, _safe_join


def test_safe_join_inside_repo(tmp_path):
    full = _safe_join(str(tmp_path), "src/auth.py")
    assert full is not None
    assert full.startswith(str(tmp_path.resolve()))


def test_safe_join_rejects_traversal(tmp_path):
    assert _safe_join(str(tmp_path), "../etc/passwd") is None
    assert _safe_join(str(tmp_path), "../../etc/passwd") is None


def test_safe_join_rejects_absolute(tmp_path):
    assert _safe_join(str(tmp_path), "/etc/passwd") is None


def test_safe_join_allows_root(tmp_path):
    assert _safe_join(str(tmp_path), "") == str(tmp_path.resolve())


def test_safe_join_rejects_symlink_escape(tmp_path):
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("secret")
    link = tmp_path / "link"
    os.symlink(str(outside), str(link))
    assert _safe_join(str(tmp_path), "link") is None


def test_write_then_read(tmp_path):
    msg = write_file(str(tmp_path), "hello.txt", "world")
    assert "Successfully" in msg
    assert read_file(str(tmp_path), "hello.txt") == "world"


def test_write_creates_parent_dirs(tmp_path):
    write_file(str(tmp_path), "a/b/c.txt", "deep")
    assert (tmp_path / "a" / "b" / "c.txt").read_text() == "deep"


def test_read_missing(tmp_path):
    assert "does not exist" in read_file(str(tmp_path), "ghost.txt")


def test_read_traversal_rejected(tmp_path):
    assert "escapes the repo" in read_file(str(tmp_path), "../oops.txt")


def test_write_traversal_rejected(tmp_path):
    assert "escapes the repo" in write_file(str(tmp_path), "../oops.txt", "x")


def test_list_files(tmp_path):
    (tmp_path / "a.txt").write_text("x")
    (tmp_path / "sub").mkdir()
    out = list_files(str(tmp_path), "")
    assert "FILE a.txt" in out
    assert "DIR sub" in out
