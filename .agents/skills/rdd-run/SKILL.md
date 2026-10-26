---
name: rdd-run
description: Run one complete Receipt-Driven Development (RDD) pass on the current candidate in a single invocation — assess against the last reviewed boundary, ask consent for medium or high, freeze, dispatch the 0, 1, or 4 reviewer lenses in parallel, refute severe findings, apply the one scoped correction, validate, and report receipts — stopping only where the user must decide. Use when the user says "run RDD", "review this commit with receipts", or "RDD before the PR", or when an ODD work-unit commit is due for review.
preferred_profile: orchestrator
escalation_profile: investigator
---

# RDD Run — one full pass

## Mission

Take the current candidate from assessment to a terminal state in one go, following [rdd](../rdd/SKILL.md) exactly.
This skill adds no rule; it removes the pauses between steps. Every step's rules, evidence bar, and refusals are the
ones `rdd` and its [reviewers/](../rdd/reviewers/) define.

## The pass

After every command, read `status --next` and continue with what it names.

- **Switch.** `python3 tools/rdd_receipts/rdd.py mode status`. Off: report the deciding source and stop — delivery is
  `disabled/unmanaged`.
- **Assess.** `rdd.py --json assess` with the selector the user named — `--committed-only` by default,
  `--base-ref <ref> --committed-only` for a branch against a base, `--projection staged` for the index, or none for
  uncommitted workspace changes; `start` takes the same selector.
  Passive: report structural checks only, advance the boundary for a committed candidate, and stop.
- **Consent.** Medium or high: ask the exact consent question from `rdd` and wait. A decline ends the pass under
  ordinary policy.
- **Freeze.** `start … --consent granted`, with one named focus on medium.
- **Review.** Dispatch every selected lens as a read-only subagent in parallel, each with its brief and the ledger
  contract; capture each ledger.
- **Refute.** For BLOCKER or CRITICAL findings, dispatch the refuters the tool names — one task each, each with the
  whole merged list — and record their verdicts.
- **Correct.** Fix only the surviving findings as one correction commit inside the frozen budget.
- **Validate.** Re-run the acceptance checks and the checks behind each surviving finding; `validate`.
- **Report.** Print `status`; export to `<DOCS_ROOT>/execution/rdd/<review-id>.md` when that path is gitignored, else
  outside the repository.

## Stops

The pass stops and hands the decision to the user when:

- RDD is off, or the user declines consent;
- a surviving finding needs a product, scope, or design decision to correct — present it with options;
- the review escalates, on budget or on a failed validation;
- `stale_target_identity` recurs after one restart: something keeps writing to the worktree. Name the writer — a
  watcher, a formatter, a build, a redirect — instead of restarting again.

## Report

```text
RDD — <review-id> · <tier> · <closed | escalated | declined | passive>
Reasons: <codes and paths from assess>
Lenses: <lens: findings count, or none>
Severe: <id severity status — corroborated, refuted, verified>
Correction: spent <n> of <budget> lines · validation <pass | findings>
Boundary: <commit> · Exported: <path>
Delivery: unchanged — commit, push, and PR follow repository policy.
```

A pass MUST NOT report `closed` unless `status` says `closed`.
