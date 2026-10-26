---
name: work-unit-commits
description: Plan and make commits as reviewable work units — one deliverable behavior, fix, migration, or docs unit per commit, with its tests and docs inside it, a rollback boundary, and recorded verification. Use when implementing a task, deciding what belongs in a commit, splitting a change before a pull request, closing an ODD task, or turning a large change into chained pull requests.
preferred_profile: implementer
escalation_profile: orchestrator
---

# Work-unit commits

## Mission

Make every commit a unit a reviewer can understand, test, and revert on its own, so commits become review candidates
for RDD and slices for chained pull requests without rework.

## Rules

| Rule | Requirement |
| --- | --- |
| Commit by work unit | A commit is one deliverable behavior, fix, migration, or docs unit. |
| Never commit by file type | Not models, then services, then tests, when none of them works alone. |
| Tests with code | Tests belong in the same commit as the behavior they verify. |
| Docs with the change | Docs belong with the feature or workflow they explain. |
| Tell a story | A reviewer understands why each commit exists from its diff and message. |
| Future pull-request ready | Each commit could become a chained pull request if the change grows. |
| High risk alone | A unit whose Risk line names a high-risk item gets its own commit. |
| Repository convention | Follow the commit-message convention `AGENTS.md` declares; the message states the outcome, not the file list. |

## Before each commit

- [ ] The commit has one clear purpose.
- [ ] The repository still makes sense with only this commit applied.
- [ ] Its tests and docs are included when relevant.
- [ ] Rollback is reasonable without reverting unrelated work.
- [ ] The focused test command and its exact result are recorded.
- [ ] The runtime check — a command or scenario that exercises the behavior end to end — and its exact result are
      recorded, or `N/A` with the reason no runtime boundary exists.
- [ ] The rollback boundary names the exact files and behavior removable without unrelated work.

Record those three pieces of evidence in the ODD feature document's `## Log` when one exists, or in the pull request
body otherwise. Uncommitted work units still need a rollback boundary.

## Splits

| Weak split | Work-unit split |
| --- | --- |
| add models | Add token validation with its domain model and tests |
| add services | Wire token validation into the login flow |
| add tests | Tests included with each behavior commit |
| update docs | Docs included with the user-facing change they explain |

## With ODD

- Every ODD task closes with at least one work-unit commit on the feature branch; branch first when on the default
  branch.
- The review candidate is that commit, or the slice it belongs to, against the previous reviewed boundary — never a
  checkbox and never the accumulated branch. See the [odd](../odd/SKILL.md) skill's `delivery.md`.
- Count authored additions plus deletions toward the 400-line delivery budget; generated goldens are excluded from the
  count but stay in the candidate. `python3 tools/odd_tasks/odd_tasks.py budget` reports it.
- When fixing a bounded RDD correction, group its work units inside that one correction; the number of units never
  creates another correction budget.

## Commands

```bash
git diff --stat
git diff --cached --stat
git log --oneline -5
```

Staging is explicit: name the paths of the unit (`git add <paths>`), never `git add -A` on a tree that may hold
scratch or unrelated work.
