# Task size and the Risk line

Load this file when classifying a request (protocol step 4) and when closing a code change with its Risk line.

## Small or large

A task is **small** when all three hold:

- **Understood** — the outcome is specified, what and where to change is known, and no product or design decision is
  open. Prove it within one bounded read batch: at most three calls and roughly 10k tokens of evidence.
- **Contained risk** — it touches no high-risk item below.
- **Resumable from the diff** — if the session stopped now, someone could finish the work from the original request
  and `git diff` alone.

A task is **large** only when the resume test fails: several sessions, waiting on something external, separate
deliverables the user wants apart (never several features asked at once), or requirements too long to survive context
compaction.

The number of files, commands, tests, fixes, or changed lines never decides size, and neither does a requested todo
list. A large task gets tracking; it gets a delegated writer only by the Writer trigger in
[delegation.md](./delegation.md).

After any mechanism resolves — a question answered, a map returned, a challenge settled — re-evaluate size. Stay small
while the three criteria hold.

## The small path

Work inline. Read and edit, several files of one understood change included. Observe RED inline before the fix, then
run the focused test and the suite inline, once each. No explorer, worker, or verifier; no feature document, mirror, or
commits unless the user asks. A todo list is optional.

## High-risk items

A mistake would be hard to detect, hard to undo, or reaches beyond the change. The change touches:

- **Item 1 — data or irreversible effects** that cannot be rebuilt: migrations, changing or deleting stored data,
  persisted format changes. Saving new records, or a dev or test database a seed rebuilds, is not this item.
- **Item 2 — security:** auth, permissions, credentials, secrets, guards, sandboxing.
- **Item 3 — contracts others consume:** changing or removing a public API, CLI flag, config format, published export,
  or a mirrored prompt or contract others already consume. Adding a flag, command, or optional field is not this item;
  an unrequested break in shared code is.
- **Item 4 — concurrency:** locks, races, async ordering.
- **Item 5 — delivery or environment:** installers, release, CI, deploy, dependencies.
- **Item 6 — no test would catch a regression** in what changes.

Count "unclear" as high only when a bounded look cannot tell whether items 1 to 5 apply. When RDD is on, its assessed
tier decides native review and the agent may only raise it — `rdd.py assess --escalate-item <N> --escalate-reason
"<line>"` — never lower it.

## The Risk line

Close every code change, small path or delegated, with one line:

```text
Risk: item 3 (renames the --limit flag that the export command also parses)
Risk: none
```

Before writing `Risk: none`, check whether the diff changes code that existing behavior the request did not mention
also uses — shared options, parsers, helpers. If it does, that is item 3. Any named item fires the Verification trigger
in [delegation.md](./delegation.md).
