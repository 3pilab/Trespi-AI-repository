"""Receipt ledger for Receipt-Driven Development (RDD).

The review lifecycle as pure functions over one JSON record. Git and storage live
elsewhere; these functions take the live candidate identity as an argument, so every
transition, refusal, vote, and closure can be unit-tested without a repository.

Lifecycle: start → one ledger receipt per selected lens (0, 1, or 4) → refuters vote
on BLOCKER/CRITICAL candidates → at most one scoped correction → scoped validation →
closed. A passive start closes at once. A closed review accepts nothing more: its
authority is spent, and the next candidate starts a new review.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence

TOOL = "python3 tools/rdd_receipts/rdd.py"

COLLECTING = "collecting"
REFUTING = "refuting"
CORRECTING = "correcting"
CLOSED = "closed"
ESCALATED = "escalated"
SUPERSEDED = "superseded"
TERMINAL = (CLOSED, ESCALATED, SUPERSEDED)

SEVERE = ("BLOCKER", "CRITICAL")
SEVERITIES = SEVERE + ("WARNING", "SUGGESTION")
LENS_PREFIX = {"risk": "R1", "readability": "R2", "reliability": "R3", "resilience": "R4"}
STANDARD_REFUTERS = ("general",)
FULL_REFUTERS = ("correctness", "exploitability", "reproducibility")
OUTCOMES = ("corroborated", "refuted", "inconclusive")
SLICE_BUDGET = 400

Record = dict[str, Any]


@dataclass
class Refusal(Exception):
    """A typed refusal. It always names the continuation that unblocks it."""

    code: str
    cause: str
    next_action: str

    def __str__(self) -> str:
        return f"code:        {self.code}\nnext_action: {self.next_action}\ncause:       {self.cause}"

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "cause": self.cause, "next_action": self.next_action}


def select_lenses(tier: str, requested: Sequence[str]) -> list[str]:
    """Passive gets none, high gets all four, and medium gets the focus the agent names."""
    if tier == "passive":
        return []
    if tier == "high":
        return list(LENS_PREFIX)
    unknown = [lens for lens in requested if lens not in LENS_PREFIX]
    if unknown or not requested or len(set(requested)) != len(requested):
        raise Refusal("lens_required", "a medium candidate needs one or more distinct lenses: "
                      + ", ".join(LENS_PREFIX), f"{TOOL} start … --lens <risk|readability|reliability|resilience>")
    return [lens for lens in LENS_PREFIX if lens in requested]


def assess_due(consumed: bool, tier: str, slice_lines: int) -> tuple[bool, str]:
    """Precedence is load-bearing: an acknowledged candidate is never reviewed twice."""
    if consumed:
        return False, "already_reviewed"
    if tier == "high":
        return True, "high_risk"
    if tier == "medium":
        return (True, "slice_budget_reached") if slice_lines >= SLICE_BUDGET else (False, "under_budget")
    return False, "passive"


def new_review(review_id: str, snapshot: dict, identity: str, assessment: dict, lenses: list[str],
               budget: int, consent: Optional[str], now: str) -> Record:
    record: Record = {
        "version": 2, "review_id": review_id, "created_at": now, "snapshot": snapshot,
        "candidate": identity, "assessment": assessment, "lenses": lenses, "consent": consent,
        "state": COLLECTING, "receipts": [], "ledger": [], "refuters": [], "refutations": {},
        "correction": {"budget": budget}, "closed_reason": None,
    }
    if not lenses:
        _close(record, "passive candidate: structural checks only, no reviewer and no prompt", now)
    return record


def _close(record: Record, reason: str, now: str, state: str = CLOSED) -> None:
    record.update(state=state, closed_reason=reason, closed_at=now)


def supersede(record: Record, now: str) -> Record:
    if record["state"] not in TERMINAL:
        _close(record, "superseded by a new candidate before it closed", now, SUPERSEDED)
    return record


def pending_lenses(record: Record) -> list[str]:
    done = {r["lens"] for r in record["receipts"]}
    return [lens for lens in record["lenses"] if lens not in done]


def severe_rows(record: Record) -> list[dict]:
    return [row for row in record["ledger"] if row["severity"] in SEVERE]


def open_rows(record: Record) -> list[dict]:
    return [row for row in record["ledger"] if row["status"] == "open"]


def _require(record: Record, live_identity: Optional[str], *states: str) -> None:
    if record["state"] not in states:
        raise Refusal("wrong_state", f"review {record['review_id']} is {record['state']}; "
                      f"this transition needs {' or '.join(states)}", f"{TOOL} status --next")
    if live_identity is not None and live_identity != record["candidate"]:
        raise Refusal("stale_target_identity", "the candidate changed after the review froze it, so its receipts "
                      "no longer describe it", f"{TOOL} status --next")


def _validate_rows(lens: str, rows: Sequence[Mapping[str, str]]) -> list[dict]:
    prefix, clean = LENS_PREFIX[lens], []
    for row in rows:
        problem = None
        if not re.fullmatch(rf"{prefix}-\d{{3}}", str(row.get("id", ""))):
            problem = f"id must look like {prefix}-001"
        elif row.get("severity") not in SEVERITIES:
            problem = f"severity must be one of {', '.join(SEVERITIES)}"
        elif not str(row.get("location", "")).strip() or not str(row.get("evidence", "")).strip():
            problem = "every finding needs a location and evidence"
        if problem:
            raise Refusal("malformed_ledger", f"{row.get('id', '?')}: {problem}", f"{TOOL} status --next")
        clean.append({"id": row["id"], "lens": lens, "location": row["location"], "severity": row["severity"],
                      "status": "open" if row["severity"] in SEVERE else "info", "evidence": row["evidence"]})
    return clean


def capture_lens(record: Record, live_identity: str, lens: str, rows: Sequence[Mapping[str, str]],
                 evidence: str, now: str) -> Record:
    _require(record, live_identity, COLLECTING)
    if lens not in pending_lenses(record):
        code = "lens_already_captured" if lens in record["lenses"] else "lens_not_selected"
        raise Refusal(code, f"lens {lens!r} is not pending for this candidate", f"{TOOL} status --next")
    if not evidence.strip():
        raise Refusal("missing_evidence", "a receipt names what was swept", f"{TOOL} status --next")
    clean = _validate_rows(lens, rows)
    record["ledger"].extend(clean)
    record["receipts"].append({"lens": lens, "findings": len(clean), "evidence": evidence, "at": now,
                               "candidate": live_identity})
    if pending_lenses(record):
        return record
    if not severe_rows(record):
        _close(record, "no BLOCKER or CRITICAL finding; warnings and suggestions are reported once as info", now)
    else:
        record["state"] = REFUTING
        record["refuters"] = list(STANDARD_REFUTERS if record["assessment"]["tier"] == "medium" else FULL_REFUTERS)
    return record


def capture_refutation(record: Record, live_identity: str, refuter: str, results: Mapping[str, str],
                       evidence: str, now: str) -> Record:
    _require(record, live_identity, REFUTING)
    if refuter not in record["refuters"] or refuter in record["refutations"]:
        raise Refusal("refuter_not_pending", f"refuter {refuter!r} is not pending; pending: "
                      + ", ".join(r for r in record["refuters"] if r not in record["refutations"]),
                      f"{TOOL} status --next")
    verdicts = {}
    for row in severe_rows(record):
        outcome = results.get(row["id"])
        verdicts[row["id"]] = outcome if outcome in OUTCOMES else "inconclusive"
    record["refutations"][refuter] = {"verdicts": verdicts, "evidence": evidence, "at": now}
    if len(record["refutations"]) < len(record["refuters"]):
        return record
    needed = 1 if len(record["refuters"]) == 1 else 2
    for row in severe_rows(record):
        refuted = sum(r["verdicts"][row["id"]] == "refuted" for r in record["refutations"].values())
        row["status"] = "refuted" if refuted >= needed else "open"
    if not open_rows(record):
        _close(record, "every BLOCKER and CRITICAL finding was refuted", now)
    else:
        record["state"] = CORRECTING
        record["correction"]["surviving"] = [row["id"] for row in open_rows(record)]
    return record


def capture_validation(record: Record, live_identity: str, spent: int, verdict: str, evidence: str,
                       now: str) -> Record:
    """Scoped validation of the one correction this candidate permits, inside its frozen budget."""
    _require(record, None, CORRECTING)
    budget = record["correction"]["budget"]
    numbers = f"spent {spent} lines, remaining {max(budget - spent, 0)}, total budget {budget}"
    if spent == 0:
        raise Refusal("no_correction", f"nothing changed since the candidate froze ({numbers})",
                      "apply the correction for the surviving findings, then run validate again")
    record["correction"]["spent"] = spent
    if spent > budget:
        _close(record, f"correction exceeded its budget: {numbers}", now, ESCALATED)
        return record
    if verdict not in ("pass", "findings") or not evidence.strip():
        raise Refusal("missing_evidence", "validation needs --verdict pass|findings and --evidence",
                      f"{TOOL} status --next")
    record["receipts"].append({"lens": "validation", "verdict": verdict, "spent": spent, "evidence": evidence,
                               "at": now, "candidate": live_identity})
    record["validated_candidate"] = live_identity
    if verdict == "pass":
        for row in open_rows(record):
            row["status"] = "verified"
        _close(record, f"scoped validation passed ({numbers})", now)
    else:
        _close(record, "scoped validation still found the defect; one candidate permits one correction", now, ESCALATED)
    return record


def next_transition(record: Record, live_identity: Optional[str]) -> dict[str, Any]:
    """What happens next. Read-only: it never changes the record."""
    state = record["state"]
    if state in TERMINAL:
        moved = live_identity is not None and live_identity != record["candidate"]
        return {"kind": state, "reason": record["closed_reason"],
                "hint": f"The workspace has moved on; `{TOOL} assess` the new candidate." if moved else ""}
    if state == CORRECTING:
        return {"kind": "validate", "surviving": record["correction"]["surviving"],
                "command": f"{TOOL} validate --verdict <pass|findings> --evidence <text>"}
    if live_identity is not None and live_identity != record["candidate"]:
        return {"kind": "stale", "reason": "the candidate changed after the freeze", "command": f"{TOOL} assess"}
    if state == COLLECTING:
        lens = pending_lenses(record)[0]
        return {"kind": "collect", "lens": lens, "remaining": pending_lenses(record),
                "command": f"{TOOL} capture --lens {lens} (--findings-file <ledger.json> | --no-findings) --evidence <text>"}
    pending = [r for r in record["refuters"] if r not in record["refutations"]]
    return {"kind": "refute", "refuter": pending[0], "remaining": pending,
            "candidates": [row["id"] for row in severe_rows(record)],
            "command": f"{TOOL} refute --refuter {pending[0]} --results-file <verdicts.json> --evidence <text>"}


def summary(record: Record) -> list[str]:
    assessment = record["assessment"]
    lines = [f"review {record['review_id']} · {record['state']} · tier {assessment['tier']} · "
             f"{assessment['changed_lines']} changed lines · lenses: {', '.join(record['lenses']) or 'none'}"]
    lines += [f"reason: {r['code']}" + (f" ({r.get('signal')})" if r.get("signal") else "")
              + (f" {r['path']}" if r.get("path") else "") + (f" — {r['detail']}" if r.get("detail") else "")
              for r in assessment["reasons"]]
    lines += [f"{row['id']} {row['severity']} {row['status']} {row['location']} — {row['evidence']}"
              for row in record["ledger"]]
    if record["closed_reason"]:
        lines.append(f"closed: {record['closed_reason']}")
    return lines
