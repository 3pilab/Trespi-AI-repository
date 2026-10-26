---
name: chained-pr
description: Split a change that would exceed about 400 changed lines into chained pull requests that each hold one reviewable work unit — stacked to main or as a feature-branch chain with a tracker — with a dependency diagram, a review budget, and a clean diff per slice. Use when a planned pull request may exceed 400 changed lines, when an ODD feature's delivery strategy fires, or when the user asks for chained or stacked pull requests or review slices.
preferred_profile: orchestrator
escalation_profile: investigator
---

# Chained pull requests

## Activation

Load this skill when a planned pull request may exceed **400 changed lines** (additions plus deletions), when an ODD
feature document's delivery strategy applies, or when the user asks for chained or stacked pull requests, review
slices, or reviewer-load control.

## Rules

- Split pull requests over 400 changed lines unless a maintainer explicitly accepts a size exception.
- Keep each pull request reviewable in about an hour: one deliverable work unit, with its tests and docs.
- State the start, end, prior dependencies, follow-up, and out-of-scope items in every chained pull request.
- Every child pull request carries a dependency diagram marking itself with `📍`.
- In a feature-branch chain, open a draft, do-not-merge tracker pull request; child 1 targets the tracker branch, later
  children target their immediate parent.
- A polluted diff is a base bug: retarget or rebase until only the current unit appears.
- Never mix chain strategies after the user chooses one.
- Opening, marking ready, and merging stay the user's decisions; agents open drafts only when asked.

## Decision gates

| Condition | Action |
| --- | --- |
| At most 400 changed lines and focused | Keep one pull request |
| Over 400, each slice can land on its own | Stacked pull requests to main |
| Over 400, the feature must integrate before main | Feature-branch chain with a tracker |
| Generated, vendored, or migration diff cannot split cleanly | Ask a maintainer for a size exception |
| An ODD feature document names a delivery strategy | Follow it before creating any pull request |

## Steps

- Measure changed lines and identify independent work units:
  `python3 tools/odd_tasks/odd_tasks.py budget --base-ref origin/main`.
- Ask for a chain strategy when none is cached and the budget is exceeded.
- Create branches and pull requests with the chosen strategy only. For stacked pull requests, use the `gh-stack`
  skill when the repository installs it.
- Add the Chain Context section to each pull request body without replacing the repository's template; package the
  body with [pr-builder](../pr-builder/SKILL.md).
- Verify each pull request on its own: CI, tests, docs, manual checks, rollback scope, and a clean diff.
- Keep the tracker draft and unmerged until every child is reviewed and integrated.
- Record slice boundaries — which commits each pull request holds — in the ODD feature document.

## Output

Return the chosen strategy, the pull request order, the current pull request's boundary, the dependency diagram, the
review budget (`additions + deletions` / 400), the verification plan, and any size-exception rationale.

## Companion files

| File | Load it when | What it holds |
| --- | --- | --- |
| [chaining-details.md](./chaining-details.md) | Creating branches or writing a chained pull request body | Strategy comparison, branch diagrams, the Chain Context section, commands, reviewer guidance |
