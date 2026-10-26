# rdd_receipts

The deterministic machinery behind [rdd](../../.agents/skills/rdd/SKILL.md) and
[rdd-run](../../.agents/skills/rdd-run/SKILL.md): Receipt-Driven Development assesses a candidate — normally one
work-unit commit against the last reviewed boundary — selects 0, 1, or 4 review lenses from risk evidence, and binds
every review result to the frozen candidate.

This is **not** a linter. It has no pre-commit hook and no repository-wide CI step. It writes review state and reviewed
boundaries under the repository's git common directory, never inside a worktree.

## The rules it enforces

- **Evidence selects the tier, never size.** `high` needs a named signal; `passive` needs proof from the bytes that
  every path is passive prose or an image; everything else is `medium`.
- **0 / 1 / 4 lenses.** Passive: none, closed at start with structural checks only. Medium: the one focus the agent
  names (`risk`, `readability`, `reliability`, `resilience`). High: all four.
- **Consent before review.** A medium or high start needs `--consent granted`; a decline continues under ordinary
  policy.
- **Only BLOCKER and CRITICAL drive fixes.** WARNING and SUGGESTION are reported once as `info`.
- **Adversarial verification.** A standard review gets one `general` refuter; a full review gets three
  (`correctness`, `exploitability`, `reproducibility`) and a finding is refuted only on two of three. A missing or
  malformed verdict counts as `inconclusive`, so the finding stands.
- **One candidate, one correction.** The budget is half the candidate's authored lines, rounded up, capped at 200 and
  never below 2. Exceeding it, or failing scoped validation, escalates to a human.
- **A closed review is spent.** It accepts nothing more, and the boundary advances to the reviewed commit.
- **Every refusal names its way out:** `code`, `cause`, `next_action`.
- **Delivery stays ordinary.** Nothing here gates a commit, a push, or a pull request.

## Run

```bash
python3 tools/rdd_receipts/rdd.py assess --committed-only
python3 tools/rdd_receipts/rdd.py start --committed-only --lens reliability --consent granted
python3 tools/rdd_receipts/rdd.py capture --lens reliability --findings-file /tmp/rdd/r3.json --evidence "one sweep"
python3 tools/rdd_receipts/rdd.py capture --lens risk --no-findings --evidence "one sweep"
python3 tools/rdd_receipts/rdd.py refute --refuter general --results-file /tmp/rdd/verdicts.json --evidence "counter-read"
python3 tools/rdd_receipts/rdd.py validate --verdict pass --evidence "npm test: 41 passed"
python3 tools/rdd_receipts/rdd.py status --next
python3 tools/rdd_receipts/rdd.py boundary show
python3 tools/rdd_receipts/rdd.py mode status
```

Add `--json` before the subcommand for machine-readable output. Keep input and output files outside the repository:
a file written inside the worktree changes the candidate.

| Exit status | Meaning |
| --- | --- |
| `0` | The transition happened, or the read succeeded. |
| `3` | Refused, with `code`, `cause`, and `next_action`. A correct outcome, not an error. |
| `2` | Argument error, or a git failure printed with git's own message. |

## `assess` and `review_due`

| Reason | `review_due` | Meaning |
| --- | --- | --- |
| `already_reviewed` | false | A closed review already covers this exact candidate |
| `high_risk` | true | High tier; review this unit alone |
| `slice_budget_reached` | true | Medium tier and the slice since the boundary reached 400 authored lines |
| `under_budget` | false | Medium tier; stays pending in the slice |
| `passive` | false | Passive; advance the boundary with `boundary advance --to <commit>` |

`--escalate-item <1-6> --escalate-reason "<line>"` raises passive or medium to high by citing a high-risk item. It
never lowers a tier. The first boundary is the branch point; every closed committed review advances it.

## Ledger and verdict files

A lens ledger is a JSON list; ids carry the lens prefix (`R1` risk, `R2` readability, `R3` reliability, `R4`
resilience):

```json
[{"id": "R3-001", "location": "src/app.py:12", "severity": "CRITICAL", "evidence": "negative limit is not tested"}]
```

A refuter's verdicts are a list of `{"finding_id", "outcome"}` with `corroborated`, `refuted`, or `inconclusive`.

## Kill switch

`mode` stores `rdd.mode` in git config. `--scope clone` writes the clone's local config, which a new clone never
inherits; `--scope global` writes the user's global config. Clone scope wins; with neither set, RDD is on. `mode status`
and `status` are read-only. With RDD off, `start` refuses and names each scope to re-enable, global first.

## Snapshots

Committed candidates compare two commit trees. Current-change candidates are built through a temporary copy of the
index, so they change neither the working tree nor the real index. The copy keeps the index mtime on purpose: a fresh
mtime would make git trust stale stat data, and a same-size edit made in the second of the last commit would vanish
from the snapshot. A test pins that case.

## Tuning

`risk.default.json` holds the hot-path tokens, passive and operational path rules, configuration names, the dangerous
sink catalog, and the six high-risk items. Prefer a repo-local override at `.rdd/risk.json`, or pass `--risk <path>`.

## Tests

```bash
python3 -m unittest discover -s tools/rdd_receipts -p 'test_*.py' -v
```
