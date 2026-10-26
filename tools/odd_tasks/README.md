# odd_tasks

The deterministic half of the [odd](../../.agents/skills/odd/SKILL.md) skill's tracking: it creates the one feature
document a large Organic Driven Development task keeps, validates its structure, keeps a recovery mirror, reports the
next task's handoff line, and measures the delivery budget from work-unit commits.

This is **not** a linter wired into CI or pre-commit: feature documents belong to consumer branches. It writes the
feature document under `<DOCS_ROOT>/odd/tasks/` (the docs root comes from `AGENTIC_DOCS_ROOT` in `AGENTS.md`, else
`docs`) and the mirror under the git common directory.

## The document it validates

```markdown
# Negative limit validation
Objective: reject negative limits · Branch: `fix/negative-limit` · Delivery: ask-on-risk · Runner: `npm test`

## Specs
S1. "GET /orders?limit=-1 returns 400 with `limit must be positive`". Acceptance: … Checks: …

## Tasks
- [x] T1 (S1) inline · validator rejects negative limit · RED→GREEN · 1a2b3c4d
- [ ] T2 (S2) inline · pin existing limit behavior

## Log
L1 2026-10-23 user (verbatim): > GET /orders returns 500 when limit is negative; it should return 400
```

`check` fails on: a header that is not two or three lines or omits `Branch:`, `Delivery:`, or `Runner:`; a delivery
strategy outside `ask-on-risk`, `auto-chain`, `single-pr`, `exception-ok`; sections out of order, extra sections, or a
`## Log` that is not last; specs numbered with a gap; a task line in another shape, a duplicate id, an unknown route,
or a link to a spec that does not exist; a spec no task covers; a checked task with no commit, `RED→GREEN`,
`evidence:`, or `N/A`; a log that does not start with a verbatim `L1` or skips a number; an unfilled template
placeholder.

## Run

```bash
python3 tools/odd_tasks/odd_tasks.py new negative-limit --request "<the user's words, verbatim>" \
  --objective "reject negative limits" --runner "npm test"
python3 tools/odd_tasks/odd_tasks.py check docs/odd/tasks/negative-limit.md
python3 tools/odd_tasks/odd_tasks.py status docs/odd/tasks/negative-limit.md
python3 tools/odd_tasks/odd_tasks.py mirror write docs/odd/tasks/negative-limit.md
python3 tools/odd_tasks/odd_tasks.py mirror check docs/odd/tasks/negative-limit.md
python3 tools/odd_tasks/odd_tasks.py budget --base-ref origin/main --file docs/odd/tasks/negative-limit.md
```

| Command | Exit `0` | Exit non-zero |
| --- | --- | --- |
| `new` | Created | `3` the feature exists (never overwritten), `2` unsafe name |
| `check` | Every document valid | `1` with `path:line: message` per finding |
| `mirror write` | Written and read back identical | `1` read-back mismatch |
| `mirror check` | Mirror matches | `1` missing (report it pending) or differs (reconcile) |
| `status`, `budget` | Report printed | `2` git failure |

`budget` counts authored additions plus deletions from the branch point to `HEAD`, excluding generated goldens and
binaries, against the 400-line delivery budget, and names the action the feature's delivery strategy takes when the
count is over.

## Tests

```bash
python3 -m unittest discover -s tools/odd_tasks -p 'test_*.py' -v
```
