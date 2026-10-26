---
name: odd
description: Organic Driven Development (ODD) — the default workflow for every request. Authorize, explore the existing code, resolve uncertainty (optional scoped research, one focused question, at most one assumption challenge), classify by task size, track large work in one feature document before the first write, implement task by task with test-first and work-unit commits, review each commit boundary with RDD when it is on, apply the delivery strategy, and close with verified results. Use on any request to change, fix, build, or investigate code, when resuming an interrupted feature, or when the user mentions ODD, a feature document, or task tracking.
preferred_profile: orchestrator
escalation_profile: investigator
---

# Organic Driven Development (ODD)

## Mission

Keep the ordinary flow — explore, implement, proportionate checks — and add exactly what the request earns. Small,
understood work runs inline with no durable artifact. Large authorized work keeps intent, progress, and evidence in one
feature document. Explanation, investigation, and proposal-only requests stay read-only.

ODD adds guidance, not a state engine or a mandatory planning phase. It never enables RDD; the RDD switch is the
user's.

## The protocol — every request, in this order

### 1. Authorize

Decide whether the request authorizes a change. Investigation, explanation, review, comparison, and proposal-only
requests stay read-only: no writer, no feature document, no commits. Ambiguous or conditional change intent gets one
clarification; stop and wait. A user who says they may stop you later is asking for notes and separate commits, not a
stop.

### 2. Explore

Explore the existing code and requirements first, proportionately to the request, before proposing or writing
anything. Read the files you will change yourself; delegate exploration only for a map you need to decide or route.
Load the standards the repository's `AGENTS.md` routes for the paths and activities in scope.

### 3. Resolve uncertainty

Each mechanism turns on only by its own trigger. Load [research.md](./research.md) when one holds:

- **Research** — recommend it only for a named uncertainty; it stays read-only and authorizes nothing.
- **One focused question** — only for a real unresolved product or design decision; ask it, then stop and wait.
- **One assumption challenge** — at most one scoped, independent, read-only challenge for a high-consequence unproven
  premise, even in a small security-critical change. Deterministic failures need fixes, not debate.

### 4. Classify

Size the task with [task-size.md](./task-size.md): small when understood, risk contained, and resumable from the
request plus `git diff`; large only when that resume test fails. File counts, commands, tests, fixes, or a requested
todo list never decide it. Small work follows the small path: inline, focused test and suite once, no document.

### 5. Track before the first write — large work only

Create the feature document and its mirror before the first source write, without asking permission for tasks or
storage, then tell the user in one line which document was created and how many tasks it holds:

```bash
python3 tools/odd_tasks/odd_tasks.py new <feature-name> --request "<the user's words, verbatim>" \
  --objective "<one line>" --runner "<the repository's test command>"
python3 tools/odd_tasks/odd_tasks.py check <DOCS_ROOT>/odd/tasks/<feature-name>.md
python3 tools/odd_tasks/odd_tasks.py mirror write <DOCS_ROOT>/odd/tasks/<feature-name>.md
```

The format, change rules, mirror, and resume protocol live in [feature-document.md](./feature-document.md).

### 6. Implement task by task

- Hand off by reference, never by paraphrase: `Spec: <document>, T2, S3-S4 — read until ## Log`. Without a document,
  pass the user's request verbatim.
- Route each task through the smallest topology — direct inline or delegated direct — per
  [delegation.md](./delegation.md). No trigger holds by default; when in doubt, work inline.
- Apply the default test-first policy in [test-first.md](./test-first.md): observed RED before implementation, GREEN,
  then refactor.
- Check a task off only after its outcome and checks were observed; update the document, run `check`, and rewrite
  the mirror after every task transition.
- Close each task with a work-unit commit and, when RDD is on, assess that commit boundary — see
  [delivery.md](./delivery.md) and the [work-unit-commits](../work-unit-commits/SKILL.md) skill.

### 7. Close

Report the verified outcome, every failed, skipped, or pending check, and the next step. End every code change with a
Risk line — `Risk: item N (reason)` or `Risk: none` — per [task-size.md](./task-size.md). Partial, blocked,
unavailable, or exhausted proof becomes one **Needs your decision** result naming the open blockers; that is a valid
stop, hedged wording is not. Never end with a tracked task pending unless you quote the user's explicit stop.

When the work is committed and nothing blocks it, end with the publish offer and wait —
[delivery.md](./delivery.md) §Publish:

```text
1) Open the draft pull request now (pr-builder; chained slices when the delivery strategy applies)
2) No, I will publish it myself
```

## Language

Talk to the user in the language they write in, prompts and questions included; commands, paths, skill names, and
answer tokens such as `1` and `2` stay literal. Write repository artifacts — code, comments, commit messages, pull
request titles and bodies, and the feature document's headings and summaries — in the repository's language, which
`AGENTS.md` sets and which defaults to English. Quotes of the user in `## Specs` and `## Log` stay verbatim in their
own language.

## Resume an interrupted feature

Read the actual task file and its mirror, reconcile them with current code and evidence, then continue the next
unfinished task — [feature-document.md](./feature-document.md) §Resume. Never infer active work from the newest file
or memory alone.

## Boundaries

- Work-unit commits on the feature branch are part of authorized large implementation; branch first when on the
  default branch. Push and draft pull requests happen only on the user's `1` to the publish offer. Marking ready and
  merge always stay the user's, as `AGENTS.md` §Agent versus human draws.
- New business scope needs the user's authorization. Findings alone never authorize expansion.
- Never toggle RDD. When it is off, keep implementing organically and report delivery as `disabled/unmanaged`.
- A blocking prompt from a subagent or tool reaches the user complete: every question, option, and the allowed answers,
  in order. Never summarize, reorder, or answer it on the user's behalf.

## Companion files

| File | Load it when | What it holds |
| --- | --- | --- |
| [task-size.md](./task-size.md) | Classifying, and writing the Risk line | Small vs large, the resume test, the six high-risk items, the small path |
| [research.md](./research.md) | A research, question, or challenge trigger holds | Research depth, sourcing, the one question, the one challenge |
| [feature-document.md](./feature-document.md) | Large work, or resuming | Format, change rules, mirror, resume protocol |
| [delegation.md](./delegation.md) | Choosing inline or delegated for a task | Triggers, writers, parallel writers, invariants, output budget |
| [test-first.md](./test-first.md) | Implementing a behavior change | RED → GREEN → REFACTOR, regression pins, differential check, scratch hygiene |
| [delivery.md](./delivery.md) | Committing a work unit or planning pull requests | Work-unit commits, RDD at the commit boundary, the 400-line delivery strategy |
