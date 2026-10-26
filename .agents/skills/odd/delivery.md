# Work units, review boundaries, and delivery

Load this file when a task closes with a commit, and when planning pull requests.

## Task size heuristic

About 400 authored changed lines (additions plus deletions) per task is a planning heuristic only — not an acceptance
criterion, a hard cap, an automatic stop, a forced split, or an RDD trigger. Keep the smallest coherent behavior with
its tests and docs. If the clear, correct solution naturally exceeds it, say why briefly and continue. Never delete
spaces, blank lines, or comments for line savings; never omit tests, minify, add gratuitous abstractions, or split
artificially. Forward this same advisory to delegated workers. Existing repository size gates still apply.

## Work-unit commits

Close every task with at least one work-unit commit on the feature branch — branch first when on the default branch —
following the [work-unit-commits](../work-unit-commits/SKILL.md) skill: one deliverable behavior per commit, tests and
docs alongside it, and the repository's commit-message convention from `AGENTS.md`. A unit whose Risk line names a
high-risk item gets its own commit, so review can take it alone; the last slice closes the feature. Record each task's
commit in the feature document.

## RDD at the commit boundary — only when the user's switch is on

The review candidate is a work-unit commit, or the slice it belongs to — never a checkbox, never the accumulated
branch. After each work-unit commit:

```bash
python3 tools/rdd_receipts/rdd.py mode status
python3 tools/rdd_receipts/rdd.py --json assess --committed-only
```

`assess` compares against the last reviewed boundary (the branch point first). Read `review_due` and
`review_due_reason`:

| Reason | Do |
| --- | --- |
| `high_risk` | Run the returned `next_transition.command` through the [rdd](../rdd/SKILL.md) skill, consent first |
| `slice_budget_reached` | Review the open slice the same way |
| `under_budget` | Record it; the medium commit stays pending in the slice |
| `passive` | Record it and advance: `rdd.py boundary advance --to HEAD` |
| `already_reviewed` | Record it; terminal authority already covers this range |

- When a high-risk unit follows pending `under_budget` commits, close the open slice first — assess and review it as
  the slice — so the high-risk commit is reviewed alone against the new boundary.
- When the user explicitly asks for a review, run it even when not due.
- You may raise a commit you know is high risk with `--escalate-item <1-6> --escalate-reason "<line>"`; never lower one.
- An unavailable or failed assessment never means low risk: treat the commit as due.
- Record the assessed tier and outcome per commit in the feature document: granted, declined, passive, under budget,
  already reviewed, or unavailable.
- When RDD is off, do not start or prompt for it; ordinary checks and repository policy remain, reported as
  `disabled/unmanaged`.

## Delivery strategy

At feature-document creation, forecast authored changed lines from the task list, and keep a running count from
work-unit commits:

```bash
python3 tools/odd_tasks/odd_tasks.py budget --base-ref origin/main --file <DOCS_ROOT>/odd/tasks/<feature-name>.md
```

Choose one strategy per feature and record it in the header:

| Strategy | When the forecast or running count exceeds about 400 lines |
| --- | --- |
| `ask-on-risk` (default) | Ask once for the chain strategy — `stacked-to-main` or `feature-branch-chain` — then slice |
| `auto-chain` | Slice automatically; ask only for a missing chain strategy |
| `single-pr` | Keep one pull request and say why in its description |
| `exception-ok` | Keep one pull request under an accepted size exception |

Apply the strategy before the next commit. Cache both choices, and record slice boundaries — which commits each pull
request holds — in the feature document. Use the [chained-pr](../chained-pr/SKILL.md) skill to plan and open slices,
and [pr-builder](../pr-builder/SKILL.md) to write each pull request.

## Publish

At close, once the work is committed and no gate is open, offer to publish and wait for the answer:

```text
1) Open the draft pull request now (pr-builder; chained slices when the delivery strategy applies)
2) No, I will publish it myself
```

On `1`:

- Push the feature branch with upstream tracking (`git push -u origin <branch>`), or each slice branch the chain
  strategy names. Resolve the `gh` invocation and any required prefix from `AGENTS.md`.
- Never force-push. When a push is rejected because the remote moved, stop: fetch, show what arrived, and integrate it
  without discarding the other commits before pushing again.
- Open every pull request as a **draft** with [pr-builder](../pr-builder/SKILL.md): the feature document is the
  governing artifact when `AGENTS.md` declares no tracker, and a tracker id comes from `AGENTS.md` or the user, never
  from a guess. The body carries the verified outcome, the checks run, the Risk line, and each commit's RDD outcome —
  or `disabled/unmanaged`. Chained pull requests add the Chain Context section from
  [chained-pr](../chained-pr/SKILL.md).
- Record the pull request links in the feature document's `## Log`, and report them.

On `2`, report the branch, its commits, and the ready-to-paste pull request title. Agents never mark a pull request
ready for review and never merge.
