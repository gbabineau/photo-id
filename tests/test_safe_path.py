"""Test the safe_path.py function"""

import os

import pytest

from photo_id.safe_path import safe_path


def test_safe_path_accepts_file_in_current_directory(tmp_path, monkeypatch):
    """A file located inside the working directory should be allowed."""
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "nested" / "report.txt"
    target.parent.mkdir(parents=True)
    target.write_text("hello")

    assert safe_path(target) == os.path.realpath(target)


def test_safe_path_accepts_subdirectory_paths(tmp_path, monkeypatch):
    """Nested paths beneath the working directory should be valid."""
    monkeypatch.chdir(tmp_path)
    nested_dir = tmp_path / "level1" / "level2"
    nested_dir.mkdir(parents=True)

    assert safe_path(nested_dir) == os.path.realpath(nested_dir)


def test_safe_path_rejects_paths_outside_current_directory(
    tmp_path, monkeypatch
):
    """Files outside the working directory should raise ValueError."""
    monkeypatch.chdir(tmp_path)
    outside_dir = tmp_path.parent / "outside"
    outside_dir.mkdir(exist_ok=True)
    outside_file = outside_dir / "secret.txt"
    outside_file.write_text("forbidden")

    with pytest.raises(ValueError, match="outside the allowed directory"):
        safe_path(outside_file)


def test_safe_path_rejects_symlinks_that_escape_the_directory(
    tmp_path, monkeypatch
):
    """A symlink pointing outside the working directory should not be allowed."""
    monkeypatch.chdir(tmp_path)
    outside_dir = tmp_path.parent / "escaped-target"
    outside_dir.mkdir(exist_ok=True)
    link_path = tmp_path / "link-to-outside"

    with pytest.raises((OSError, ValueError)):
        os.symlink(outside_dir, link_path)
        safe_path(link_path)
