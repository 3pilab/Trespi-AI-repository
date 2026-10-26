# Review ledger contract

Every reviewer brief in this directory includes this contract. Pass it with the brief to each reviewer subagent.

## Sweep budget

A standard review runs exactly one exhaustive sweep of the candidate diff per lens, then stops. A full four-lens review
runs at most two sweeps per lens. There is no loop until nothing more turns up; the sweep budget is the whole first
pass.

## Precision gate

Report a finding only when it is a real, user-impacting defect you would defend with concrete evidence. When in doubt,
stay silent: a missed nitpick costs nothing, a false positive costs a full correction cycle. Style and preference
findings are out unless they hide a defect.

## Findings ledger

Return a JSON list, one row per finding, and nothing for a clean lens — the orchestrator then captures `--no-findings`.

| Field | Values |
| --- | --- |
| `id` | Lens prefix and a three-digit number: `R1-001` risk, `R2-001` readability, `R3-001` reliability, `R4-001` resilience |
| `location` | `path/to/file.ext:line` or `path:start-end` |
| `severity` | `BLOCKER`, `CRITICAL`, `WARNING`, or `SUGGESTION` |
| `evidence` | Why it matters: the input or state, then the wrong output, crash, or exposure |

```json
[{"id": "R3-001", "location": "src/orders.ts:41", "severity": "CRITICAL",
  "evidence": "limit=-1 reaches the query builder; the database raises and the route returns 500"}]
```

## Severity floor

Only BLOCKER and CRITICAL findings that survive refutation enter the correction. WARNING and SUGGESTION are reported
once as `info`, never re-reviewed, and never block.

## Scoped validation

A validator receives only the frozen ledger and the correction delta. It re-checks the original acceptance criteria
and the evidence for each surviving finding; it does not inspect the full original diff or look for new defects. Later
observations are non-blocking follow-ups and change no finding, id, or budget.

## Execution

Reviewers are read-only. They never edit files, fix findings, delegate, or widen scope. They return their own ledger
rows; the orchestrator merges and captures them.
