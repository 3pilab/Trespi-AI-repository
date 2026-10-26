"""Evidence-based risk tiers for Receipt-Driven Development (RDD).

Three tiers, selected from evidence alone. `high` needs a named signal: a hot-path
token, a service token, shell source, an executable-mode change, a dangerous sink
in added lines, or an agent escalation citing a high-risk item. `passive` needs
proof that every authored path is a passive document by its own bytes, never by
extension alone. Everything else is `medium`. Change volume, file count, and model
are deliberately not inputs: size is a delivery concern, not risk.

Standalone Python 3 with no third-party dependency.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Optional, Sequence

DEFAULT_RISK = Path(__file__).resolve().parent / "risk.default.json"
ADOPTER_RISK = Path(".rdd/risk.json")

PASSIVE = "passive"
MEDIUM = "medium"
HIGH = "high"
TIERS = (PASSIVE, MEDIUM, HIGH)
IMAGE_SIGNATURES = (b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff", b"GIF87a", b"GIF89a")


@dataclass(frozen=True)
class Change:
    path: str
    status: str = "M"
    old_mode: str = "100644"
    new_mode: str = "100644"
    additions: int = 0
    deletions: int = 0
    binary: bool = False
    added: str = ""
    content: Optional[bytes] = None


@dataclass(frozen=True)
class Assessment:
    tier: str
    reasons: tuple[dict, ...]
    changed_lines: int
    lenses: tuple[str, ...] = field(default=())

    def as_dict(self) -> dict[str, object]:
        return {"tier": self.tier, "reasons": list(self.reasons), "changed_lines": self.changed_lines,
                "lenses": list(self.lenses)}


@dataclass(frozen=True)
class Policy:
    raw: dict

    def __getattr__(self, name: str):
        try:
            return self.raw[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    @property
    def lens_names(self) -> tuple[str, ...]:
        return tuple(self.raw["lenses"])


def resolve_risk_path(explicit: Path | None, root: Path | None = None) -> Path:
    """Shipped default, unless the adopter keeps a repo-local override or passes --risk."""
    if explicit is not None:
        return explicit
    adopter = (root or Path.cwd()) / ADOPTER_RISK
    return adopter if adopter.is_file() else DEFAULT_RISK


def load_policy(path: Path = DEFAULT_RISK) -> Policy:
    raw = json.loads(path.read_text(encoding="utf-8"))
    for sink in raw["dangerous_sinks"]:
        re.compile(sink["pattern"])
    if len(raw["lenses"]) != 4:
        raise ValueError(f"{path}: a full review needs exactly four lenses")
    return Policy(raw)


def _tokens(value: str) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9]+", value.lower()) if t]


def is_test_path(policy: Policy, path: str) -> bool:
    parts = PurePosixPath(path.lower()).parts
    if any(segment in policy.test_path_segments for segment in parts[:-1]):
        return True
    return any(re.search(p, parts[-1]) for p in policy.test_file_patterns)


def is_generated(policy: Policy, path: str) -> bool:
    return any(re.search(p, path) for p in policy.generated_patterns)


def is_configuration(policy: Policy, path: str) -> bool:
    name = PurePosixPath(path.lower()).name
    return (name in policy.configuration_basenames or name == ".env" or name.startswith(".env.")
            or PurePosixPath(name).suffix in policy.configuration_extensions)


def is_operational(policy: Policy, path: str) -> bool:
    """Agent-facing material is consumed as instructions, so it is never passive prose."""
    lower = PurePosixPath(path.lower())
    if lower.name in policy.operational_basenames:
        return True
    if any(segment in policy.operational_segments for segment in lower.parts):
        return True
    return any(token in policy.operational_tokens for part in lower.parts for token in _tokens(PurePosixPath(part).stem))


def _passive_content(policy: Policy, path: str, content: Optional[bytes]) -> bool:
    suffix = PurePosixPath(path.lower()).suffix
    if content is None:
        return False
    if suffix in policy.image_extensions:
        return content.startswith(IMAGE_SIGNATURES)
    if b"\x00" in content:
        return False
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return False
    if text.lstrip("\ufeff").startswith("#!"):
        return False
    if suffix == ".mdx":
        return not re.search(r"^\s*(import|export)\b|<script\b", text, re.MULTILINE)
    return True


def is_passive(policy: Policy, change: Change) -> bool:
    suffix = PurePosixPath(change.path.lower()).suffix
    if suffix not in policy.passive_extensions or is_configuration(policy, change.path):
        return False
    if is_operational(policy, change.path) or change.old_mode != change.new_mode and change.status != "A":
        return False
    return change.status == "D" or _passive_content(policy, change.path, change.content)


def high_reasons(policy: Policy, change: Change) -> list[dict]:
    reasons = []
    if not is_test_path(policy, change.path) and not is_generated(policy, change.path):
        signals = {policy.hot_path_tokens[t] for t in _tokens(change.path) if t in policy.hot_path_tokens}
        reasons += [{"code": "hot_path", "signal": s, "path": change.path} for s in sorted(signals)]
        for part in PurePosixPath(change.path.lower()).parts:
            tokens = _tokens(PurePosixPath(part).stem)
            if any(a == "service" and b == "token" for a, b in zip(tokens, tokens[1:])):
                reasons.append({"code": "service_token", "signal": "auth", "path": change.path})
                break
    if PurePosixPath(change.path.lower()).suffix in policy.shell_extensions and change.status != "D":
        reasons.append({"code": "shell_source", "signal": "shell_process", "path": change.path})
    if "100755" in (change.old_mode, change.new_mode) and change.old_mode != change.new_mode and change.status == "M":
        reasons.append({"code": "executable_mode", "signal": "permissions", "path": change.path,
                        "detail": f"mode {change.old_mode} -> {change.new_mode}"})
    suffix = PurePosixPath(change.path.lower()).suffix
    for sink in policy.dangerous_sinks:
        if suffix in sink["extensions"] and change.added and re.search(sink["pattern"], change.added, re.MULTILINE):
            reasons.append({"code": "dangerous_sink", "signal": "dangerous_sink", "path": change.path,
                            "detail": sink["name"]})
    return reasons


def changed_lines(policy: Policy, changes: Sequence[Change]) -> int:
    """Authored additions plus deletions; generated goldens, binaries, and mode-only changes count zero."""
    return sum(c.additions + c.deletions for c in changes if not (c.binary or is_generated(policy, c.path)))


def classify(policy: Policy, changes: Sequence[Change], escalation: Optional[dict] = None) -> Assessment:
    lines = changed_lines(policy, changes)
    reasons = [r for change in changes for r in high_reasons(policy, change)]
    if escalation:
        item = str(escalation["item"])
        if item not in policy.high_risk_items:
            raise ValueError(f"escalation item must be one of {', '.join(policy.high_risk_items)}, got {item!r}")
        reasons.append({"code": "agent_escalation", "signal": "agent_escalation",
                        "detail": f"item {item} ({policy.high_risk_items[item]}): {escalation['reason']}"})
    if reasons:
        return Assessment(HIGH, tuple(reasons), lines, policy.lens_names)
    if changes and all(is_passive(policy, c) for c in changes):
        return Assessment(PASSIVE, ({"code": "non_executable_only"},), lines, ())
    if changes and all(c.content == b"" and c.additions == c.deletions == 0 for c in changes):
        return Assessment(MEDIUM, ({"code": "empty_content"},), lines, ())
    code = "configuration_change" if any(is_configuration(policy, c.path) for c in changes) else "executable_change"
    paths = [c.path for c in changes if not is_passive(policy, c)][:3]
    return Assessment(MEDIUM, tuple({"code": code, "path": p} for p in paths), lines, ())


def correction_budget(original_lines: int) -> int:
    """Half the candidate, rounded up, capped at 200; never below two while anything changed."""
    if original_lines <= 0:
        return 0
    return max(2, min(200, original_lines // 2 + original_lines % 2))
