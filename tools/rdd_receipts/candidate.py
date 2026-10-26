"""Candidate snapshots for Receipt-Driven Development (RDD).

A candidate is the exact state under review, identified by two git tree ids: the
base and the candidate itself. Trees are built through a temporary index, so taking
a snapshot never touches the working tree, the real index, or any tracked file; it
only adds loose objects to the object store. A receipt is bound to that identity,
and any write to the workspace afterwards makes the receipt stale.

Standalone Python 3 with no third-party dependency.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Mapping, Optional

from risk import Change

WORKSPACE = "workspace"
STAGED = "staged"
COMMITTED = "committed"
PROJECTIONS = (WORKSPACE, STAGED, COMMITTED)

MAX_ADDED_BYTES_PER_PATH = 200_000


class GitError(RuntimeError):
    """A git command failed; the message carries git's own stderr."""


class UnsupportedCombination(ValueError):
    """A projection and base-ref pairing the snapshot does not support."""


@dataclass(frozen=True)
class Snapshot:
    projection: str
    base_commit: Optional[str]
    base_tree: str
    tree: str
    head_commit: Optional[str] = None

    @property
    def identity(self) -> str:
        return f"{self.projection}:{self.base_tree}..{self.tree}"

    def as_dict(self) -> dict[str, object]:
        return {
            "projection": self.projection,
            "base_commit": self.base_commit,
            "base_tree": self.base_tree,
            "tree": self.tree,
            "head_commit": self.head_commit,
        }


def git(root: Path, *args: str, env: Mapping[str, str] | None = None, stdin: bytes | None = None) -> bytes:
    proc = subprocess.run(
        ["git", "-c", "core.quotePath=false", *args],
        cwd=root,
        env={**os.environ, **(env or {})},
        input=stdin,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise GitError(proc.stderr.decode("utf-8", "replace").strip() or f"git {' '.join(args)} failed")
    return proc.stdout


def git_text(root: Path, *args: str, env: Mapping[str, str] | None = None) -> str:
    return git(root, *args, env=env).decode("utf-8", "replace").strip()


def repo_root(cwd: Path) -> Path:
    return Path(os.path.realpath(git_text(cwd, "rev-parse", "--show-toplevel")))


def common_dir(root: Path) -> Path:
    value = Path(git_text(root, "rev-parse", "--git-common-dir"))
    return Path(os.path.realpath(value if value.is_absolute() else root / value))


def worktree_key(root: Path) -> str:
    """Stable per worktree; the real path folds aliases such as /var and /private/var."""
    return hashlib.sha256(os.path.realpath(root).encode("utf-8")).hexdigest()[:16]


def head_commit(root: Path) -> Optional[str]:
    try:
        return git_text(root, "rev-parse", "--verify", "-q", "HEAD^{commit}") or None
    except GitError:
        return None


def empty_tree(root: Path) -> str:
    return git(root, "hash-object", "-t", "tree", "-w", "--stdin", stdin=b"").decode().strip()


def tree_of(root: Path, commit: Optional[str]) -> str:
    return git_text(root, "rev-parse", f"{commit}^{{tree}}") if commit else empty_tree(root)


def _write_tree(root: Path, include_workspace: bool) -> str:
    index_path = Path(git_text(root, "rev-parse", "--git-path", "index"))
    real_index = index_path if index_path.is_absolute() else root / index_path
    with tempfile.TemporaryDirectory(prefix="rdd-index-") as tmp:
        index = Path(tmp) / "index"
        if real_index.is_file():
            # copy2 keeps the index mtime. A fresh mtime would hide racily clean entries,
            # and a same-size edit made in the commit's second would vanish from the snapshot.
            shutil.copy2(real_index, index)
        env = {"GIT_INDEX_FILE": str(index)}
        if include_workspace:
            git(root, "add", "-A", "--", ".", env=env)
        return git_text(root, "write-tree", env=env)


def take_snapshot(root: Path, projection: str = WORKSPACE, base_ref: Optional[str] = None) -> Snapshot:
    if projection not in PROJECTIONS:
        raise UnsupportedCombination(f"unknown projection {projection!r}; use one of {', '.join(PROJECTIONS)}")
    if projection == COMMITTED and not base_ref:
        raise UnsupportedCombination(
            "--projection committed needs --base-ref <ref>; or drop --projection to review the workspace"
        )
    if projection != COMMITTED and base_ref:
        raise UnsupportedCombination(
            f"--projection {projection} does not take --base-ref. Use --projection {projection} alone "
            f"to review against HEAD, or --projection committed --base-ref {base_ref} to review commits"
        )
    head = head_commit(root)
    if projection == COMMITTED:
        if head is None:
            raise UnsupportedCombination("--projection committed needs at least one commit; review the workspace instead")
        base = git_text(root, "merge-base", base_ref, head)
        return Snapshot(COMMITTED, base, tree_of(root, base), tree_of(root, head), head)
    tree = _write_tree(root, include_workspace=projection == WORKSPACE)
    return Snapshot(projection, head, tree_of(root, head), tree)


def changed_paths(root: Path, base_tree: str, tree: str) -> list[str]:
    out = git(root, "diff", "--name-only", "-z", "--no-renames", base_tree, tree)
    return [p for p in out.decode("utf-8", "replace").split("\0") if p]


def added_text(root: Path, base_tree: str, tree: str) -> dict[str, str]:
    """Added lines per path, which is what content rules read."""
    out = git(root, "diff", "--no-color", "--no-ext-diff", "--no-renames", "--unified=0", base_tree, tree)
    added: dict[str, list[str]] = {}
    current: Optional[str] = None
    for line in out.decode("utf-8", "replace").splitlines():
        if line.startswith("+++ "):
            target = line[4:].rstrip("\t")
            current = None if target == "/dev/null" else target[2:] if target.startswith("b/") else target
            continue
        if current and line.startswith("+"):
            bucket = added.setdefault(current, [])
            if sum(len(x) for x in bucket) < MAX_ADDED_BYTES_PER_PATH:
                bucket.append(line[1:])
    return {path: "\n".join(lines) for path, lines in added.items()}


def changes(root: Path, base_tree: str, tree: str, passive_suffixes: tuple[str, ...] = ()) -> list[Change]:
    """Every changed path with its status, modes, line counts, added text, and — for paths
    that could be passive documents — the bytes that prove or disprove it."""
    raw = git(root, "diff", "--raw", "-z", "--no-renames", "--no-abbrev", base_tree, tree).decode("utf-8", "replace")
    fields = raw.split("\0")
    entries: dict[str, dict] = {}
    for meta, path in zip(fields[0::2], fields[1::2]):
        if not meta.startswith(":"):
            continue
        old_mode, new_mode, _, new_oid, status = meta[1:].split(" ")
        entries[path] = {"status": status[0], "old_mode": old_mode, "new_mode": new_mode, "oid": new_oid}
    numstat = git(root, "diff", "--numstat", "-z", "--no-renames", base_tree, tree).decode("utf-8", "replace")
    for row in numstat.split("\0"):
        if row.count("\t") == 2:
            added, deleted, path = row.split("\t")
            if path in entries:
                entries[path].update(binary=not added.isdigit(), additions=int(added) if added.isdigit() else 0,
                                     deletions=int(deleted) if deleted.isdigit() else 0)
    added = added_text(root, base_tree, tree)
    result = []
    for path, entry in entries.items():
        content = None
        if entry["status"] != "D" and PurePosixPath(path.lower()).suffix in passive_suffixes:
            content = git(root, "cat-file", "blob", entry["oid"])
        result.append(Change(path=path, status=entry["status"], old_mode=entry["old_mode"],
                             new_mode=entry["new_mode"], additions=entry.get("additions", 0),
                             deletions=entry.get("deletions", 0), binary=entry.get("binary", False),
                             added=added.get(path, ""), content=content))
    return result


def lines_between(root: Path, tree_a: str, tree_b: str) -> int:
    """Added plus deleted lines between two trees; binary files count as zero lines."""
    total = 0
    for row in git(root, "diff", "--numstat", "--no-renames", tree_a, tree_b).decode().splitlines():
        added, deleted, _ = row.split("\t", 2)
        total += (int(added) if added.isdigit() else 0) + (int(deleted) if deleted.isdigit() else 0)
    return total


def outside_or_ignored(root: Path, path: Path) -> bool:
    """True when writing to `path` cannot change a candidate snapshot of `root`."""
    try:
        rel = os.path.relpath(os.path.realpath(path), root)
    except ValueError:
        return True
    if rel.startswith(".."):
        return True
    proc = subprocess.run(["git", "check-ignore", "-q", "--", rel], cwd=root, capture_output=True)
    return proc.returncode == 0
