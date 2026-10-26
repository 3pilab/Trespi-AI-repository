#!/usr/bin/env python3
"""Feature documents for Organic Driven Development (ODD).

One feature document per substantial task: a short header, `## Specs` with numbered
`S#` requirements that quote the user verbatim, `## Tasks` with one line per task,
and `## Log` last, where `L1` is the original request verbatim. This tool creates
that document, validates its structure, keeps a recovery mirror outside every
worktree, reports progress, and measures the delivery budget from work-unit commits.

Standalone Python 3 with no third-party dependency.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

SECTIONS = ("## Specs", "## Tasks", "## Log")
DELIVERY = ("ask-on-risk", "auto-chain", "single-pr", "exception-ok")
ROUTES = ("inline", "delegated")
HEADER_KEYS = ("Branch:", "Delivery:", "Runner:")
DELIVERY_BUDGET = 400
FEATURE_NAME = re.compile(r"^[a-z0-9][a-z0-9-]{1,80}$")
SPEC_LINE = re.compile(r"^S(\d+)\.\s+\S")
TASK_LINE = re.compile(
    r"^- \[(?P<done>[ xX])\] (?P<id>[A-Z]+\d+)(?: \((?P<specs>S\d+(?:\s*[-,]\s*S\d+)*)\))? (?P<route>\w+)\b(?P<rest>.*)$"
)
LOG_LINE = re.compile(r"^L(\d+)\b")
EVIDENCE = re.compile(r"\b[0-9a-f]{7,40}\b|RED\s*(?:→|->)\s*GREEN|\bevidence:|\bN/A\b", re.IGNORECASE)
PLACEHOLDERS = ("<requirement — quote", "<smallest coherent behavior")
GENERATED = re.compile(r"(^|/)(testdata/golden|__snapshots__)/|\.(golden|snap)$")


@dataclass
class Finding:
    line: int
    message: str


@dataclass
class Document:
    path: Path
    lines: list[str]
    sections: dict[str, int] = field(default_factory=dict)
    specs: dict[int, int] = field(default_factory=dict)
    tasks: list[dict] = field(default_factory=list)
    logs: list[int] = field(default_factory=list)


def spec_ids(ref: Optional[str]) -> list[int]:
    """`S2`, `S2-S4`, and `S1, S3` all expand to explicit numbers."""
    if not ref:
        return []
    ids: list[int] = []
    for part in re.split(r"\s*,\s*", ref):
        bounds = [int(n) for n in re.findall(r"S(\d+)", part)]
        ids.extend(range(bounds[0], bounds[-1] + 1) if len(bounds) == 2 else bounds)
    return ids


def parse(path: Path) -> Document:
    doc = Document(path, path.read_text(encoding="utf-8").splitlines())
    current = None
    for number, line in enumerate(doc.lines, start=1):
        if line.startswith("## "):
            current = line.strip()
            doc.sections.setdefault(current, number)
            continue
        if current == "## Specs" and (match := SPEC_LINE.match(line)):
            doc.specs.setdefault(int(match.group(1)), number)
        elif current == "## Tasks" and line.startswith("- ["):
            match = TASK_LINE.match(line)
            doc.tasks.append({"line": number, "raw": line, "match": match})
        elif current == "## Log" and (match := LOG_LINE.match(line)):
            doc.logs.append(int(match.group(1)))
    return doc


def _check_header(doc: Document, findings: list[Finding]) -> None:
    first_section = min(doc.sections.values(), default=len(doc.lines) + 1)
    header = [line for line in doc.lines[: first_section - 1] if line.strip()]
    if not header or not header[0].startswith("# "):
        findings.append(Finding(1, "the document must open with a `# <feature title>` line"))
        return
    if not 2 <= len(header) <= 3:
        findings.append(Finding(1, f"the header must be two or three lines, found {len(header)}"))
    body = " ".join(header[1:])
    for key in HEADER_KEYS:
        if key not in body:
            findings.append(Finding(2, f"the header must name `{key}`"))
    delivery = re.search(r"Delivery:\s*`?([\w-]+)", body)
    if delivery and delivery.group(1) not in DELIVERY:
        findings.append(Finding(2, f"Delivery must be one of {', '.join(DELIVERY)}, got {delivery.group(1)!r}"))


def _check_sections(doc: Document, findings: list[Finding]) -> None:
    present = [s for s in doc.sections if s in SECTIONS]
    for section in SECTIONS:
        if section not in doc.sections:
            findings.append(Finding(1, f"missing `{section}`"))
    if present and present != [s for s in SECTIONS if s in present]:
        findings.append(Finding(doc.sections[present[0]], "sections must appear as Specs, Tasks, Log"))
    extra = [s for s in doc.sections if s not in SECTIONS]
    for section in extra:
        findings.append(Finding(doc.sections[section], f"unexpected section `{section}`; keep one feature document"))
    if "## Log" in doc.sections and max(doc.sections.values()) != doc.sections["## Log"]:
        findings.append(Finding(doc.sections["## Log"], "`## Log` must be the last section"))


def _check_specs(doc: Document, findings: list[Finding]) -> None:
    if not doc.specs:
        findings.append(Finding(doc.sections.get("## Specs", 1), "`## Specs` needs at least `S1.`"))
        return
    expected = list(range(1, max(doc.specs) + 1))
    missing = [n for n in expected if n not in doc.specs]
    if missing:
        findings.append(Finding(doc.sections["## Specs"], f"specs must be numbered without gaps; missing S{missing[0]}"))


def _check_tasks(doc: Document, findings: list[Finding]) -> None:
    if not doc.tasks:
        findings.append(Finding(doc.sections.get("## Tasks", 1), "`## Tasks` needs at least one task line"))
    seen: set[str] = set()
    covered: set[int] = set()
    for task in doc.tasks:
        match, number = task["match"], task["line"]
        if not match:
            findings.append(Finding(number, "task lines read `- [ ] <ID> (S#) <inline|delegated> · <summary>`"))
            continue
        if match.group("id") in seen:
            findings.append(Finding(number, f"task id {match.group('id')} is not unique"))
        seen.add(match.group("id"))
        if match.group("route") not in ROUTES:
            findings.append(Finding(number, f"route must be inline or delegated, got {match.group('route')!r}"))
        for spec in spec_ids(match.group("specs")):
            if spec not in doc.specs:
                findings.append(Finding(number, f"task {match.group('id')} links S{spec}, which does not exist"))
            covered.add(spec)
        if match.group("done") != " " and not EVIDENCE.search(match.group("rest")):
            findings.append(Finding(number, f"task {match.group('id')} is checked without a commit or RED→GREEN evidence"))
    for spec, number in sorted(doc.specs.items()):
        if doc.tasks and spec not in covered:
            findings.append(Finding(number, f"S{spec} has no task"))


def _check_log(doc: Document, findings: list[Finding]) -> None:
    anchor = doc.sections.get("## Log", 1)
    if not doc.logs or doc.logs[0] != 1:
        findings.append(Finding(anchor, "`## Log` must start with `L1`, the user's original request verbatim"))
        return
    first = next(line for line in doc.lines[anchor:] if LOG_LINE.match(line))
    if "verbatim" not in first.lower():
        findings.append(Finding(anchor + 1, "`L1` must say it is verbatim and quote the request unchanged"))
    if doc.logs != list(range(1, len(doc.logs) + 1)):
        findings.append(Finding(anchor, "log entries must be numbered L1, L2, … without gaps"))


def check(path: Path) -> list[Finding]:
    doc = parse(path)
    findings: list[Finding] = []
    for number, line in enumerate(doc.lines, start=1):
        if any(marker in line for marker in PLACEHOLDERS):
            findings.append(Finding(number, "unfilled template placeholder"))
    for step in (_check_header, _check_sections, _check_specs, _check_tasks, _check_log):
        step(doc, findings)
    return sorted(findings, key=lambda f: f.line)


# --- repository helpers -----------------------------------------------------

def git(root: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc.stdout.strip()


def repo_root(start: Path) -> Path:
    return Path(os.path.realpath(git(start, "rev-parse", "--show-toplevel")))


def docs_root(root: Path) -> str:
    agents = root / "AGENTS.md"
    if agents.is_file():
        match = re.search(r"AGENTIC_DOCS_ROOT=([^\s`]+)", agents.read_text(encoding="utf-8"))
        if match:
            return match.group(1)
    return "docs"


def mirror_path(root: Path, doc_path: Path) -> Path:
    common = Path(git(root, "rev-parse", "--git-common-dir"))
    common = common if common.is_absolute() else root / common
    return Path(os.path.realpath(common)) / "odd" / doc_path.stem / "tasks.md"


def authored_lines(root: Path, base_ref: str) -> tuple[int, str]:
    """Added plus deleted lines from the branch point to HEAD, generated goldens and binaries excluded."""
    base = git(root, "merge-base", base_ref, "HEAD")
    total = 0
    for row in git(root, "diff", "--numstat", "--no-renames", f"{base}..HEAD").splitlines():
        added, deleted, path = row.split("\t", 2)
        if GENERATED.search(path) or not (added.isdigit() and deleted.isdigit()):
            continue
        total += int(added) + int(deleted)
    return total, base


# --- commands ---------------------------------------------------------------

TEMPLATE = """# {title}
Objective: {objective} · Branch: `{branch}` · Delivery: {delivery} · Runner: `{runner}`

## Specs
S1. <requirement — quote the user's exact strings, errors, and examples verbatim; acceptance criteria; checks>

## Tasks
- [ ] T1 (S1) inline · <smallest coherent behavior with its tests and docs>

## Log
L1 {today} user (verbatim): > {request}
"""


def cmd_new(args: argparse.Namespace) -> int:
    if not FEATURE_NAME.match(args.feature):
        print(f"feature name must be kebab-case and filename-safe, got {args.feature!r}", file=sys.stderr)
        return 2
    root = repo_root(Path.cwd())
    target = root / docs_root(root) / "odd" / "tasks" / f"{args.feature}.md"
    if target.exists():
        print(f"{target.relative_to(root)} already exists; reuse the same feature identity, never overwrite it",
              file=sys.stderr)
        return 3
    request = args.request if args.request is not None else Path(args.request_file).read_text(encoding="utf-8")
    branch = args.branch or git(root, "rev-parse", "--abbrev-ref", "HEAD")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(TEMPLATE.format(
        title=args.title or args.feature.replace("-", " ").capitalize(), objective=args.objective, branch=branch,
        delivery=args.delivery, runner=args.runner, today=dt.date.today().isoformat(),
        request=request.strip().replace("\n", "\n> "),
    ), encoding="utf-8")
    print(f"created {target.relative_to(root)} — fill S1 and T1, then run `check`")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    findings = []
    for name in args.files:
        for finding in check(Path(name)):
            findings.append(finding)
            print(f"{name}:{finding.line}: {finding.message}")
    if not findings:
        print(f"{len(args.files)} feature document(s) valid")
    return 1 if findings else 0


def cmd_status(args: argparse.Namespace) -> int:
    doc = parse(Path(args.file))
    tasks = [t["match"] for t in doc.tasks if t["match"]]
    done = [t for t in tasks if t.group("done") != " "]
    pending = [t for t in tasks if t.group("done") == " "]
    print(f"{doc.path.name}: {len(done)}/{len(tasks)} tasks done · {len(doc.specs)} specs · {len(doc.logs)} log entries")
    if pending:
        nxt = pending[0]
        specs = ", ".join(f"S{n}" for n in spec_ids(nxt.group("specs"))) or "no linked spec"
        print(f"next: {nxt.group('id')} ({specs}) {nxt.group('route')}{nxt.group('rest')}")
        print(f"handoff: Spec: {doc.path}, {nxt.group('id')}, {specs} — read until `## Log`")
    else:
        print("next: close — report the verified outcome, every failed or pending check, and the next step")
    return 0


def cmd_mirror(args: argparse.Namespace) -> int:
    doc_path = Path(args.file).resolve()
    root = repo_root(doc_path.parent)
    target = mirror_path(root, doc_path)
    locator = f"<!-- locator: {doc_path.relative_to(root)} -->\n"
    content = locator + doc_path.read_text(encoding="utf-8")
    if args.action == "write":
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        same = target.read_text(encoding="utf-8") == content
        print(f"mirror {'written and read back' if same else 'READ-BACK MISMATCH'}: {target}")
        return 0 if same else 1
    if not target.is_file():
        print(f"mirror missing: {target} — run `mirror write`; report the mirror as pending until then")
        return 1
    if args.action == "show":
        print(target.read_text(encoding="utf-8"), end="")
        return 0
    same = target.read_text(encoding="utf-8") == content
    print(f"mirror {'matches' if same else 'DIFFERS from'} {doc_path.relative_to(root)} ({target})")
    return 0 if same else 1


def cmd_budget(args: argparse.Namespace) -> int:
    root = repo_root(Path.cwd())
    lines, base = authored_lines(root, args.base_ref)
    over = lines > DELIVERY_BUDGET
    print(f"authored changed lines since {base[:10]}: {lines} / {DELIVERY_BUDGET}")
    if not over:
        print("delivery: within budget — keep one pull request")
        return 0
    strategy = None
    if args.file:
        match = re.search(r"Delivery:\s*`?([\w-]+)", Path(args.file).read_text(encoding="utf-8"))
        strategy = match.group(1) if match else None
    advice = {
        "ask-on-risk": "ask once for the chain strategy (stacked-to-main or feature-branch-chain), cache it, then slice",
        "auto-chain": "slice automatically; ask only for a missing chain strategy",
        "single-pr": "keep one pull request and say why in its description",
        "exception-ok": "keep one pull request under the accepted size exception",
    }.get(strategy or "", "apply the feature's delivery strategy before the next commit")
    print(f"delivery: over budget — {advice}; record slice boundaries in the feature document")
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    new = sub.add_parser("new", help="create <DOCS_ROOT>/odd/tasks/<feature>.md with L1 verbatim")
    new.add_argument("feature")
    source = new.add_mutually_exclusive_group(required=True)
    source.add_argument("--request", help="the user's original request, verbatim")
    source.add_argument("--request-file", help="a file holding the original request, verbatim")
    new.add_argument("--objective", required=True)
    new.add_argument("--runner", required=True, help="the test command the repository already uses")
    new.add_argument("--delivery", choices=DELIVERY, default="ask-on-risk")
    new.add_argument("--branch")
    new.add_argument("--title")

    sub.add_parser("check", help="validate feature documents").add_argument("files", nargs="+")
    sub.add_parser("status", help="progress and the next task's handoff line").add_argument("file")
    mirror = sub.add_parser("mirror", help="recovery copy under the git common directory")
    mirror.add_argument("action", choices=("write", "check", "show"))
    mirror.add_argument("file")
    budget = sub.add_parser("budget", help="authored changed lines since the branch point")
    budget.add_argument("--base-ref", default="origin/HEAD")
    budget.add_argument("--file", help="feature document whose delivery strategy applies")

    args = parser.parse_args(argv)
    try:
        return {"new": cmd_new, "check": cmd_check, "status": cmd_status,
                "mirror": cmd_mirror, "budget": cmd_budget}[args.command](args)
    except RuntimeError as exc:
        print(f"git: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
