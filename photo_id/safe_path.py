"""Implements a function to ensure file paths are not escaped."""

import os


def safe_path(path):
    """Return a canonical path within the current working directory.

    Raises:
        ValueError: If the resolved path is outside the current working directory.
    """
    resolved = os.path.realpath(path)
    base_dir = os.path.realpath(os.getcwd())
    if resolved != base_dir and not resolved.startswith(base_dir + os.sep):
        raise ValueError(f"path {path!r} is outside the allowed directory")
    return resolved
