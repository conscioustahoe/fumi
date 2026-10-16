"""Read-only git queries about the repo a spec file lives in."""

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GitState:
    branch: str
    sha: str


def _git(cwd: Path, *args: str) -> str:
    out = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=10)
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip() or f"git {' '.join(args)} failed")
    return out.stdout.strip()


def toplevel(folder: Path) -> Path | None:
    """The repo that contains this folder or None when it isn't in one."""
    try:
        return Path(_git(folder, "rev-parse", "--show-toplevel")).resolve()
    except (RuntimeError, OSError):
        return None


def git_dir(repo: Path) -> Path:
    """The real git directory. A worktree's .git is a file that points somewhere else."""
    return (repo / _git(repo, "rev-parse", "--git-dir")).resolve()


def state(repo: Path) -> GitState:
    branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    try:
        sha = _git(repo, "rev-parse", "--short", "HEAD")
    except RuntimeError:
        sha = "no commits"
    return GitState(branch="detached" if branch == "HEAD" else branch, sha=sha)
