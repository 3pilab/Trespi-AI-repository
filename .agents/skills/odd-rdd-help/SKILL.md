---
name: odd-rdd-help
description: Explain how to use Organic Driven Development (ODD) and Receipt-Driven Development (RDD) with this framework's skills — which skill fits, what task size, a feature document, a Risk line, an RDD tier, a review_due reason, or a refusal means, the exact prompt or command to run next in Claude Code, Cursor, or Agent Hub, and where an in-flight feature stands. Read-only; writes no files. Use when the user asks how ODD or RDD works, which skill to use, what to do next, or for example prompts.
preferred_profile: orchestrator
escalation_profile: investigator
---

# ODD and RDD help

## Mission

Answer the question with this repository's real skills, paths, and commands, and end with the one prompt or command
that moves the user forward. This skill teaches and points; it does not do the work.

## Modes

Pick the mode from the question; "what now?" is always mode C.

### A. How does it work?

Answer from [guide.md](./guide.md): the protocol, task size, the feature document, work-unit commits, the commit
boundary, RDD tiers, lenses, refuters, and delivery. Quote the section that answers the question and add the example
prompt that fits.

### B. Which skill should I use?

Use [guide.md](./guide.md) §Which skill. Name one skill, the reason, and the prompt to paste.

### C. Where am I and what is next?

Inspect the state read-only, then recommend the next step:

```bash
ls -t <DOCS_ROOT>/odd/tasks/ 2>/dev/null | head -5
python3 tools/odd_tasks/odd_tasks.py status <DOCS_ROOT>/odd/tasks/<feature>.md
python3 tools/odd_tasks/odd_tasks.py mirror check <DOCS_ROOT>/odd/tasks/<feature>.md
python3 tools/rdd_receipts/rdd.py mode status
python3 tools/rdd_receipts/rdd.py status --next
python3 tools/rdd_receipts/rdd.py boundary show
git status --short && git log --oneline -5
```

Report the next task and its handoff line, the gate the work waits on, and the exact prompt that resumes it. When
nothing is in flight, say so and offer the starter prompt.

### D. What does this output mean?

Explain a Risk line, an `odd_tasks.py check` finding, an RDD tier, a `review_due_reason`, or a refusal `code` from
[guide.md](./guide.md) §Reading the output, then give the `next_action` the output already names.

## Rules

- MUST NOT write, edit, or delete files, and MUST NOT run a command that changes state: no `odd_tasks.py new` or
  `mirror write`, no `rdd.py start`, `capture`, `refute`, `validate`, `export`, `boundary advance`, or `mode
  enable|disable`.
- Answer in the user's language. Commands, skill names, and paths stay exactly as written.
- Show both runtimes when invocation differs: Claude Code and Cursor.
- When the question is really a request to do the work, name the skill that does it and offer the prompt.

## Companion files

| File | Load it when | What it holds |
| --- | --- | --- |
| [guide.md](./guide.md) | Every mode | The shared ODD and RDD guide: protocol, diagram, chooser, runtimes, examples, output reference |
