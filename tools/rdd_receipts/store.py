"""Review state, reviewed boundaries, and the user-owned RDD switch.

Everything lives under the git common directory, outside every worktree, so recording
a receipt or advancing a boundary never changes a candidate. The switch is git config
`rdd.mode`: clone scope is the clone's local config, which a new clone never inherits;
global scope is the user's global config. Reading the mode changes nothing.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Iterator, Optional

import candidate as cand
import ledger

MODE_KEY = "rdd.mode"


def _config(root: Path, scope: str) -> Optional[str]:
    proc = subprocess.run(["git", "config", f"--{scope}", "--get", MODE_KEY], cwd=root, capture_output=True, text=True)
    value = proc.stdout.strip().lower()
    return value if value in ("on", "off") else None


def mode_status(root: Path) -> dict[str, Optional[str]]:
    """Read-only. Clone scope wins over global; with neither set, RDD is on by default."""
    clone, global_ = _config(root, "local"), _config(root, "global")
    effective, source = (clone, "clone") if clone else (global_, "global") if global_ else ("on", "default")
    return {"effective": effective, "source": source, "clone": clone, "global": global_}


def mode_set(root: Path, value: str, scope: str) -> None:
    git_scope = "local" if scope == "clone" else "global"
    subprocess.run(["git", "config", f"--{git_scope}", MODE_KEY, value], cwd=root, check=True)


def require_mode_on(root: Path) -> None:
    status = mode_status(root)
    if status["effective"] == "on":
        return
    off = [scope for scope in ("global", "clone") if status[scope] == "off"]
    commands = " then ".join(f"{ledger.TOOL} mode enable --scope {s}" for s in off)
    raise ledger.Refusal("mode_off", f"RDD is off ({', '.join(off)} scope); delivery stays disabled/unmanaged",
                         f"only if the user asks: {commands}")


def store_dir(root: Path) -> Path:
    return cand.common_dir(root) / "rdd" / cand.worktree_key(root)


def _write(path: Path, payload: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f".{path.name}.tmp")
        tmp.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
        os.replace(tmp, path)
    except OSError as exc:
        raise ledger.Refusal("store_not_writable", f"cannot write review state under {path.parent}: {exc.strerror}",
                             "make the git directory writable, or run from a writable clone") from exc


def load_current(root: Path) -> Optional[ledger.Record]:
    path = store_dir(root) / "current.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def save_current(root: Path, record: ledger.Record) -> None:
    _write(store_dir(root) / "current.json", record)


def archive(root: Path, record: ledger.Record) -> None:
    _write(store_dir(root) / "history" / f"{record['review_id']}.json", record)


def all_reviews(root: Path) -> Iterator[ledger.Record]:
    current = load_current(root)
    if current:
        yield current
    history = store_dir(root) / "history"
    for path in sorted(history.glob("*.json")) if history.is_dir() else []:
        yield json.loads(path.read_text(encoding="utf-8"))


def consumed(root: Path, identity: str) -> bool:
    """True when a closed review already settled this exact candidate identity."""
    return any(r["state"] == ledger.CLOSED and identity in (r["candidate"], r.get("validated_candidate"))
               for r in all_reviews(root))


def require_review(root: Path) -> ledger.Record:
    record = load_current(root)
    if record is None:
        raise ledger.Refusal("no_review", "no review exists for this worktree", f"{ledger.TOOL} assess")
    return record


# --- reviewed boundaries ------------------------------------------------------

def branch(root: Path) -> str:
    try:
        return cand.git_text(root, "rev-parse", "--abbrev-ref", "HEAD")
    except cand.GitError:
        return "HEAD"


def default_boundary(root: Path) -> Optional[str]:
    """The branch point: merge-base with the remote default branch, else main or master."""
    for ref in ("origin/HEAD", "origin/main", "main", "origin/master", "master"):
        try:
            base = cand.git_text(root, "merge-base", ref, "HEAD")
        except cand.GitError:
            continue
        if base and base != cand.head_commit(root):
            return base
    return None


def boundary(root: Path) -> tuple[Optional[str], str]:
    path = store_dir(root) / "boundaries.json"
    saved = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    if branch(root) in saved:
        return saved[branch(root)], "reviewed"
    return default_boundary(root), "branch point"


def advance_boundary(root: Path, commit: str) -> None:
    path = store_dir(root) / "boundaries.json"
    saved = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    saved[branch(root)] = cand.git_text(root, "rev-parse", "--verify", f"{commit}^{{commit}}")
    _write(path, saved)
