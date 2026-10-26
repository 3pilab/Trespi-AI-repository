#!/usr/bin/env python3
"""Receipt-Driven Development (RDD) — evidence-selected review with bound receipts.

`assess` classifies a candidate — normally a work-unit commit against the last
reviewed boundary — as passive, medium, or high, and says whether review is due.
`start` freezes the candidate and selects 0, 1, or 4 lenses; `capture`, `refute`, and
`validate` record receipts bound to that freeze; `status` is the read-only authority
on what comes next. State lives under the git common directory, never in a worktree.
Delivery is untouched: commits, pushes, and pull requests follow repository policy,
and a closed review is evidence, not a gate.

Standalone Python 3 with no third-party dependency.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import candidate as cand
import ledger
import risk as riskmod
import store


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def snapshot_for(root: Path, args: argparse.Namespace) -> cand.Snapshot:
    if args.committed_only or args.base_ref:
        base = args.base_ref or store.boundary(root)[0]
        if not base:
            raise ledger.Refusal("no_boundary", "no reviewed boundary or branch point exists to compare against",
                                 f"{ledger.TOOL} assess --base-ref <ref> --committed-only, or review --current changes")
        return cand.take_snapshot(root, cand.COMMITTED, base)
    return cand.take_snapshot(root, args.projection)


def assess_snapshot(root: Path, snapshot: cand.Snapshot, args: argparse.Namespace) -> riskmod.Assessment:
    policy = riskmod.load_policy(riskmod.resolve_risk_path(args.risk, root))
    changes = cand.changes(root, snapshot.base_tree, snapshot.tree, tuple(policy.passive_extensions))
    if not changes:
        raise ledger.Refusal("empty_candidate", f"the {snapshot.projection} candidate has no change",
                             "commit or stage a change, or pick another selector")
    escalation = {"item": args.escalate_item, "reason": args.escalate_reason} if args.escalate_item else None
    if escalation and not (args.escalate_reason or "").strip():
        raise ledger.Refusal("escalation_reason_required", "an escalation cites one item and a one-line reason",
                             "add --escalate-reason \"<one line>\"")
    try:
        return riskmod.classify(policy, changes, escalation)
    except ValueError as exc:
        raise ledger.Refusal("bad_escalation", str(exc), "cite an item from 1 to 6") from exc


def selectors(snapshot: cand.Snapshot) -> str:
    if snapshot.projection == cand.COMMITTED:
        return f"--base-ref {snapshot.base_commit} --committed-only"
    return f"--projection {snapshot.projection}"


def cmd_assess(root: Path, args: argparse.Namespace) -> dict:
    snapshot = snapshot_for(root, args)
    found = assess_snapshot(root, snapshot, args)
    due, reason = ledger.assess_due(store.consumed(root, snapshot.identity), found.tier, found.changed_lines)
    result = {"risk": found.tier, "reasons": list(found.reasons), "changed_lines": found.changed_lines,
              "candidate": snapshot.as_dict(), "review_due": due, "review_due_reason": reason,
              "rdd_mode": store.mode_status(root)["effective"]}
    if due:
        lens = " --lens <focus>" if found.tier == "medium" else ""
        result["next_transition"] = {"command": f"{ledger.TOOL} start {selectors(snapshot)}{lens} --consent granted"}
    return result


def cmd_start(root: Path, args: argparse.Namespace) -> dict:
    store.require_mode_on(root)
    snapshot = snapshot_for(root, args)
    found = assess_snapshot(root, snapshot, args)
    if store.consumed(root, snapshot.identity):
        raise ledger.Refusal("already_reviewed", "terminal authority already covers this exact candidate",
                             "continue; the reviewed boundary already includes it")
    lenses = ledger.select_lenses(found.tier, args.lens)
    if lenses and args.consent != "granted":
        raise ledger.Refusal("consent_required", f"a {found.tier} candidate runs review only on the user's grant",
                             "ask: 1) Run the review now  2) Not now, just this once — then rerun with --consent granted, "
                             "or continue under ordinary policy on a decline")
    previous = store.load_current(root)
    if previous is not None:
        store.archive(root, ledger.supersede(previous, now()))
    review_id = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{snapshot.tree[:8]}"
    record = ledger.new_review(review_id, snapshot.as_dict(), snapshot.identity, found.as_dict(), lenses,
                               riskmod.correction_budget(found.changed_lines), args.consent, now())
    finish(root, record)
    return record


def finish(root: Path, record: ledger.Record) -> None:
    """Persist, and advance the reviewed boundary when a committed candidate closes."""
    store.save_current(root, record)
    head = record["snapshot"].get("head_commit")
    if record["state"] == ledger.CLOSED and head:
        store.advance_boundary(root, head)


def live_identity(root: Path, record: ledger.Record) -> Optional[str]:
    """None when a snapshot cannot be taken, so status stays usable on a read-only store."""
    snap = record["snapshot"]
    try:
        base = snap["base_commit"] if snap["projection"] == cand.COMMITTED else None
        if base:
            return cand.take_snapshot(root, cand.COMMITTED, base).identity
        return cand.take_snapshot(root, snap["projection"]).identity
    except (cand.GitError, cand.UnsupportedCombination):
        return None


def load_json(path: Optional[str], empty: object) -> object:
    if not path:
        return empty
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ledger.Refusal("unreadable_input", f"{path}: {exc}", "write valid JSON and rerun") from exc


def cmd_capture(root: Path, args: argparse.Namespace) -> dict:
    record = store.require_review(root)
    if not args.no_findings and not args.findings_file:
        raise ledger.Refusal("missing_ledger", "pass the lens ledger, or --no-findings for an empty one",
                             "rerun with --findings-file <ledger.json> or --no-findings")
    rows = [] if args.no_findings else load_json(args.findings_file, [])
    if not isinstance(rows, list):
        raise ledger.Refusal("malformed_ledger", "the findings file must hold a JSON list of rows",
                             "write [{\"id\", \"location\", \"severity\", \"evidence\"}, …] and rerun")
    record = ledger.capture_lens(record, live_identity(root, record), args.lens, rows, args.evidence, now())
    finish(root, record)
    return record


def cmd_refute(root: Path, args: argparse.Namespace) -> dict:
    record = store.require_review(root)
    results = load_json(args.results_file, {})
    if isinstance(results, list):
        results = {r.get("finding_id"): r.get("outcome") for r in results if isinstance(r, dict)}
    record = ledger.capture_refutation(record, live_identity(root, record), args.refuter, results, args.evidence, now())
    finish(root, record)
    return record


def cmd_validate(root: Path, args: argparse.Namespace) -> dict:
    record = store.require_review(root)
    snap = record["snapshot"]
    base = snap["base_commit"] if snap["projection"] == cand.COMMITTED else None
    live = cand.take_snapshot(root, cand.COMMITTED, base) if base else cand.take_snapshot(root, snap["projection"])
    spent = cand.lines_between(root, snap["tree"], live.tree)
    record = ledger.capture_validation(record, live.identity, spent, args.verdict, args.evidence, now())
    if record["state"] == ledger.CLOSED and live.head_commit:
        record["snapshot"]["head_commit"] = live.head_commit
    finish(root, record)
    return record


def cmd_export(root: Path, args: argparse.Namespace) -> dict:
    record = store.require_review(root)
    out = Path(args.out).expanduser()
    if not cand.outside_or_ignored(root, out):
        raise ledger.Refusal("export_inside_candidate", f"{out} is inside the worktree and not ignored; "
                             "writing it would change the candidate", "export outside the repository or to a gitignored path")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(["# RDD receipts", "", *[f"- {line}" for line in ledger.summary(record)], ""]),
                   encoding="utf-8")
    return record


def emit(payload: dict, as_json: bool, lines: list[str]) -> None:
    print(json.dumps(payload, indent=1) if as_json else "\n".join(lines))


def report(root: Path, record: ledger.Record, as_json: bool) -> None:
    nxt = ledger.next_transition(record, live_identity(root, record))
    lines = ledger.summary(record) + [f"next: {nxt['kind']}" + (f" → {nxt['command']}" if nxt.get("command") else "")]
    lines += [nxt["hint"]] if nxt.get("hint") else []
    emit({"review": record, "next": nxt}, as_json, lines)


def refuse(refusal: ledger.Refusal, as_json: bool) -> int:
    print(json.dumps(refusal.as_dict(), indent=1) if as_json else refusal, file=sys.stdout if as_json else sys.stderr)
    return 3


def add_selectors(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--base-ref", help="compare against this ref (default: the last reviewed boundary)")
    parser.add_argument("--committed-only", action="store_true", help="review committed work since the base")
    parser.add_argument("--projection", choices=(cand.WORKSPACE, cand.STAGED), default=cand.WORKSPACE,
                        help="current changes to review when no base is named")
    parser.add_argument("--escalate-item", help="raise passive or medium to high by citing a high-risk item 1-6")
    parser.add_argument("--escalate-reason", help="one line, required with --escalate-item")
    parser.add_argument("--risk", type=Path, help="risk policy (default: .rdd/risk.json, else risk.default.json)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cwd", type=Path, default=Path.cwd(), help="repository to act on (default: current)")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    sub = parser.add_subparsers(dest="command", required=True)
    add_selectors(sub.add_parser("assess", help="read-only: risk tier and whether review is due"))
    start = sub.add_parser("start", help="freeze the candidate and select 0, 1, or 4 lenses")
    add_selectors(start)
    start.add_argument("--lens", action="append", default=[], help="medium focus: risk, readability, reliability, resilience")
    start.add_argument("--consent", choices=("granted",), help="the user's grant for a medium or high review")
    capture = sub.add_parser("capture", help="record one lens's findings ledger")
    capture.add_argument("--lens", required=True, choices=list(ledger.LENS_PREFIX))
    capture.add_argument("--findings-file")
    capture.add_argument("--no-findings", action="store_true")
    capture.add_argument("--evidence", required=True)
    refute = sub.add_parser("refute", help="record one refuter's verdict per BLOCKER/CRITICAL finding")
    refute.add_argument("--refuter", required=True, choices=ledger.STANDARD_REFUTERS + ledger.FULL_REFUTERS)
    refute.add_argument("--results-file", required=True)
    refute.add_argument("--evidence", required=True)
    validate = sub.add_parser("validate", help="scoped validation of the one correction")
    validate.add_argument("--verdict", required=True, choices=("pass", "findings"))
    validate.add_argument("--evidence", required=True)
    sub.add_parser("status", help="read-only: state and next transition").add_argument("--next", action="store_true")
    boundary = sub.add_parser("boundary", help="the last reviewed boundary for this branch")
    boundary.add_argument("action", choices=("show", "advance"))
    boundary.add_argument("--to", help="commit to advance to (advance only)")
    mode = sub.add_parser("mode", help="the user-owned RDD switch")
    mode.add_argument("action", choices=("status", "enable", "disable"))
    mode.add_argument("--scope", choices=("clone", "global"), default="clone")
    sub.add_parser("export", help="write a receipt summary outside the candidate").add_argument("--out", required=True)
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        root = cand.repo_root(args.cwd)
        if args.command == "mode":
            if args.action != "status":
                store.mode_set(root, "on" if args.action == "enable" else "off", args.scope)
            status = store.mode_status(root)
            emit(status, args.json, [f"rdd: {status['effective']} (decided by {status['source']})"])
        elif args.command == "boundary":
            if args.action == "advance":
                if not args.to:
                    raise ledger.Refusal("missing_commit", "advance needs --to <commit>", "rerun with --to <commit>")
                store.advance_boundary(root, args.to)
            commit, source = store.boundary(root)
            emit({"boundary": commit, "source": source, "branch": store.branch(root)}, args.json,
                 [f"boundary: {commit or 'none'} ({source}) on {store.branch(root)}"])
        elif args.command == "assess":
            result = cmd_assess(root, args)
            emit(result, args.json, [f"risk: {result['risk']} · {result['changed_lines']} changed lines · "
                                     f"review_due: {str(result['review_due']).lower()} ({result['review_due_reason']})"]
                 + [f"reason: {r['code']} {r.get('path', '')} {r.get('detail', '')}".rstrip() for r in result["reasons"]]
                 + ([f"next: {result['next_transition']['command']}"] if result["review_due"] else []))
        elif args.command == "status":
            record = store.require_review(root)
            if args.next:
                emit(ledger.next_transition(record, live_identity(root, record)), True, [])
            else:
                report(root, record, args.json)
        else:
            handler = {"start": cmd_start, "capture": cmd_capture, "refute": cmd_refute,
                       "validate": cmd_validate, "export": cmd_export}[args.command]
            report(root, handler(root, args), args.json)
        return 0
    except ledger.Refusal as refusal:
        return refuse(refusal, args.json)
    except cand.UnsupportedCombination as exc:
        return refuse(ledger.Refusal("unsupported_combination", str(exc), "rerun with one of the forms the cause names"),
                      args.json)
    except cand.GitError as exc:
        print(f"git: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
