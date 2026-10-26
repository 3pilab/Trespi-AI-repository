# The feature document

Load this file for large authorized work (protocol step 5) and when resuming. One feature document per feature: it is
intent, progress, and evidence in one place, and it is the specification workers read by reference.

## Location and identity

- `<DOCS_ROOT>/odd/tasks/<feature-name>.md`, with a descriptive, filename-safe, kebab-case name. `odd_tasks.py new`
  resolves the docs root from `AGENTIC_DOCS_ROOT` in `AGENTS.md`.
- Reuse the same identity for the whole feature; never overwrite another feature's document. Keep one document — no
  separate plan file.
- It is committed with the feature, so its tasks record the commits that hold them.
- `S#`, task ids, and `L#` are anchors inside this document only. They MUST NOT appear in code, comments, tests, or
  commit messages, where they turn into orphaned tokens after merge.

## Fixed order — stable content first, the growing log last

```markdown
# <Feature title>
Objective: <one line> · Branch: `<branch>` · Delivery: <ask-on-risk|auto-chain|single-pr|exception-ok> · Runner: `<test command>`
Chain: <stacked-to-main|feature-branch-chain|none> · Slices: <which commits each PR holds, once delivery applies>

## Specs
S1. "<the user's exact string, error message, or example>" — scope, acceptance criteria, applicable checks.
S2. …

## Tasks
- [x] T1 (S1) inline · <smallest coherent behavior with its tests and docs> · RED→GREEN · <commit>
- [ ] T2 (S2-S3) delegated · <unit> · writer trigger: parallelism

## Log
L1 <date> user (verbatim): > <the original request, unchanged>
L2 <date> T1 evidence: RED `<failure>`; GREEN `<runner result>`; Risk: none.
```

- **Header** — two or three lines: objective, branch, delivery strategy, test runner; the chain strategy and slice
  boundaries once they exist. The runner is the one the repository already uses; never invent one.
- **`## Specs`** — numbered `S1`..`Sn` with their authorized scope, acceptance criteria, and checks. Quote the user's
  exact strings, error messages, commands, and examples verbatim and in the user's language. Never summarize or reword
  those fragments, never add requirements the user did not ask for, and mark assumptions as assumptions.
- **`## Tasks`** — one line per task: a stable id, its linked `S#`, the route (`inline` or `delegated`) with the trigger
  evidence when delegated, the status, and the commit or RED/GREEN evidence once done.
- **`## Log`** — `L1` holds the original request verbatim. Later user corrections are logged verbatim with their date;
  problem analysis, rationale for meaningful accepted changes, verification evidence, feature-specific worker learnings
  ([delegation.md](./delegation.md#learnings)), progress, and the next step are appended. Routine corrections stay
  brief: this is a logbook, not a decision journal.

Validate after every edit; `check` fails on any departure from this shape:

```bash
python3 tools/odd_tasks/odd_tasks.py check <DOCS_ROOT>/odd/tasks/<feature-name>.md
python3 tools/odd_tasks/odd_tasks.py status <DOCS_ROOT>/odd/tasks/<feature-name>.md
```

## Changes

Accepted user, review, or verification changes update the affected intent and tasks together — never regenerate the
whole document:

- A requirement change appends its verbatim `## Log` entry, rewrites only the affected `S#`, and reopens only its
  linked task.
- Preserve valid completed and unrelated work. Add genuinely new tasks, or reopen invalidated ones with a reason, and
  revise their checks.
- Findings alone never authorize scope expansion or automatic acceptance. New business scope needs the user.
- Check off only observed outcomes with applicable proof. Record failed, unavailable, skipped, or pending checks
  honestly. A checkbox grants no approval and is no review receipt.

## The mirror

Keep a recovery copy of the full current document plus its repository-relative locator — not a summary — outside every
worktree:

```bash
python3 tools/odd_tasks/odd_tasks.py mirror write <DOCS_ROOT>/odd/tasks/<feature-name>.md
python3 tools/odd_tasks/odd_tasks.py mirror check <DOCS_ROOT>/odd/tasks/<feature-name>.md
```

The mirror lives under the git common directory, so it survives branch switches and is shared by every worktree of the
clone. When a persistent memory tool is configured in the runtime, mirroring the same full document there as well is
encouraged. The two writes are not atomic: read both back. If a write is unavailable, keep local progress and report
the mirror as pending — never claim it succeeded, and never block unrelated safe work. On irreconcilable edits,
preserve both versions and ask only about the real conflict.

## Resume

Before implementation or resume, the parent:

- reads the actual task file and the mirror (`mirror show`), and any configured memory copy;
- reconciles them with current requirements, code, and evidence — `git log`, `git diff`, test results — preserving
  pending mirrors and conflicting edits;
- continues with the next unfinished task, passing the locator, the task id, and the linked `S#` to whoever works it.

Workers read the document until `## Log` before editing and report which `S#` they covered. Small work without a
document still receives its authorized scope and checks.
