---
name: rdd
description: Receipt-Driven Development (RDD) — bounded, independent review evidence for a frozen change candidate, normally one work-unit commit against the last reviewed boundary. Assess the risk tier from evidence, ask the user's consent for medium or high, run 0, 1, or 4 read-only reviewer lenses (risk, readability, reliability, resilience), verify BLOCKER and CRITICAL findings with refuters, apply at most one scoped correction inside its budget, validate it, and record receipts. Use when an ODD work-unit commit is assessed, when the user asks to review a change with receipts, to resume or inspect an RDD review, to explain a refusal, or to turn RDD on or off.
preferred_profile: orchestrator
escalation_profile: investigator
---

# RDD — Receipt-Driven Development

## Mission

Make "this change was reviewed" a checkable statement about one frozen candidate. Review depth comes from risk
evidence, never from size; every lens result is a receipt bound to the candidate; findings are refuted before anyone
fixes them; one candidate permits one bounded correction. RDD is user-owned and never gates delivery: commits, pushes,
and pull requests follow ordinary repository policy.

[rdd-run](../rdd-run/SKILL.md) runs one full pass unattended; this skill is the protocol.

## The switch is the user's

```bash
python3 tools/rdd_receipts/rdd.py mode status
```

- On by default and opt-out. `status` is read-only and names the deciding source; `default` means nobody chose.
- When the user asks to stop using RDD, run `mode disable` — do not argue, work around it, or propose alternatives first.
- While it is off, keep implementing: no reviews, no retries, no reactivation. Delivery reports `disabled/unmanaged`,
  never a fabricated approval. Never enable it on the user's behalf unless they ask.
- When the repository does not carry `tools/rdd_receipts/`, say so and stop. Receipts kept by hand are claims.

## Follow the tool, never the prose

`status --next` is the authority on what comes next. Run the command it returns; never infer a transition from a
summary or from memory. After any ambiguous, interrupted, or malformed result, query `status --next` again first.
Keep every ledger, verdict, and export file outside the repository — a file written into the worktree changes the
candidate and the next capture refuses with `stale_target_identity`.

## The lifecycle

### 1. Assess

```bash
python3 tools/rdd_receipts/rdd.py --json assess --committed-only
```

Pick the selector that matches what the user asked to review; `assess` and `start` take the same ones:

| Selector | Candidate |
| --- | --- |
| `--committed-only` | Commits since the last reviewed boundary — the default at an ODD commit boundary |
| `--base-ref <ref> --committed-only` | Commits since `<ref>`, for example a branch against `main` |
| `--projection staged` | The staged index against `HEAD` |
| none | Uncommitted workspace changes against `HEAD` |

The tier comes from evidence: `high` needs a named signal (hot-path token, service token, shell source, executable mode,
dangerous sink, or an escalation); `passive` needs every path proven passive prose by its bytes; the rest is `medium`.
Raise a candidate you know is high risk with `--escalate-item <1-6> --escalate-reason "<line>"`, citing the high-risk
items in the [odd](../odd/SKILL.md) skill's `task-size.md`. Never lower a tier, and never infer low risk from a failed
assessment.

### 2. Consent — medium and high only

Passive stays silent: structural checks, no reviewer, no prompt. For medium or high, present the candidate's tier and
reasons and ask exactly:

```text
RDD — <tier> risk: <reasons>
1) Run the review now
2) Not now, just this once
To stop RDD entirely: python3 tools/rdd_receipts/rdd.py mode disable
```

On `1`, start with `--consent granted`. On `2`, continue under ordinary policy and record `declined`; the next work unit
asks again.

### 3. Start — freeze and select lenses

```bash
python3 tools/rdd_receipts/rdd.py start --committed-only --consent granted [--lens <focus>]
```

High selects all four lenses. Medium selects the one focus that matches the change — `reliability` for behavior and
tests, `risk` for security-adjacent code, `resilience` for operational paths, `readability` for structure — and states
why in one line. Run every source-mutating formatter before `start`; after it, only check-only tools may run.

### 4. Review — one read-only reviewer per lens

Dispatch each selected lens as an independent, read-only subagent with its brief from [reviewers/](./reviewers/) and
the frozen candidate (`git diff <base>..<head>`), on the `investigator` profile: in Cursor launch the `investigator`
subagent by name so its pinned model applies; in Claude Code use a general-purpose subagent told it is read-only, with
the `investigator` pin as its model. Run the lenses in parallel. Each returns a findings ledger; capture it:

```bash
python3 tools/rdd_receipts/rdd.py capture --lens <lens> --findings-file <outside>/r1.json --evidence "<what was swept>"
python3 tools/rdd_receipts/rdd.py capture --lens <lens> --no-findings --evidence "<what was swept>"
```

### 5. Refute — BLOCKER and CRITICAL only

When severe findings exist, `status --next` names the refuters: one `general` refuter for a standard review, three for
a full review — `correctness`, `exploitability`, `reproducibility` — each receiving the complete merged list in one task.
Never one task per finding. Run each refuter on the `investigator` subagent, like the lenses, with
[reviewers/review-refuter.md](./reviewers/review-refuter.md), then:

```bash
python3 tools/rdd_receipts/rdd.py refute --refuter <name> --results-file <outside>/verdicts.json --evidence "<counter-evidence read>"
```

A full review refutes a finding only on two of three verdicts; a missing or malformed verdict keeps it.

### 6. Correct once, then validate

Fix only the surviving findings, inside the budget the tool froze (half the candidate's lines, at most 200), as one
correction — a commit on top of the candidate. Then run scoped validation: re-run the original acceptance checks and the
checks that exposed each finding, without new defect discovery.

```bash
python3 tools/rdd_receipts/rdd.py validate --verdict <pass|findings> --evidence "<the re-run and its result>"
```

A pass closes the review and advances the reviewed boundary. Over budget or a failed validation escalates: hand the
receipts to the user. There is no loop-until-clean.

### 7. Report

`status`, and an export for the pull request when one is coming:

```bash
python3 tools/rdd_receipts/rdd.py export --out <DOCS_ROOT>/execution/rdd/<review-id>.md
```

## Refusals

Every refusal carries `code`, `cause`, and `next_action`; follow `next_action`.

| Code | Meaning |
| --- | --- |
| `consent_required` | Medium or high without the user's grant — ask the consent question |
| `lens_required` | Medium needs a named focus |
| `stale_target_identity` | The candidate changed after the freeze — something wrote to the worktree |
| `already_reviewed` | Terminal authority already covers this candidate |
| `mode_off` | The user turned RDD off; the refusal names how to turn it back on if they ask |
| `malformed_ledger`, `missing_ledger` | The lens ledger is not valid yet |
| `refuter_not_pending`, `wrong_state` | That step does not fit the current state |
| `no_correction` | Validation was asked for before a correction exists |
| `export_inside_candidate` | The export path would change the candidate |

## Boundaries

- Reviewers and refuters are read-only: they never edit, fix, delegate, or add scope.
- Never capture a receipt for a sweep that did not happen, or with evidence that was not observed.
- Never block, delay, or condition a commit, push, or pull request on RDD.
- RDD reviews a local candidate; [pr-review](../pr-review/SKILL.md) still reviews the pull request before merge review.

## Companion files

| File | Load it when | What it holds |
| --- | --- | --- |
| [reviewers/review-risk.md](./reviewers/review-risk.md) | Dispatching the `risk` lens | R1: security, privilege boundaries, data exposure, dependencies |
| [reviewers/review-readability.md](./reviewers/review-readability.md) | Dispatching the `readability` lens | R2: naming, complexity, intent, maintainability |
| [reviewers/review-reliability.md](./reviewers/review-reliability.md) | Dispatching the `reliability` lens | R3: behavior-first tests, edge cases, determinism, contracts |
| [reviewers/review-resilience.md](./reviewers/review-resilience.md) | Dispatching the `resilience` lens | R4: fallbacks, observability, rollback, performance |
| [reviewers/ledger-contract.md](./reviewers/ledger-contract.md) | Every reviewer dispatch | Sweep budget, precision gate, ledger schema, severity floor |
| [reviewers/review-refuter.md](./reviewers/review-refuter.md) | Dispatching a refuter | Input, refutation rules, output |
| [tools/rdd_receipts](../../../tools/rdd_receipts/README.md) | A tool behavior needs explaining | Tiers, due reasons, files, kill switch, tuning |
