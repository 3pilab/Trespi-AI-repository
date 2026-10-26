# Routing and delegation

Load this file when choosing how a task runs. Every authorized change takes exactly one implementation route: **direct
inline** or **delegated direct**. Tests, builds, installs, and review actors may still use fresh workers without
changing that route.

- **Direct inline** — small tasks, and large tasks with no Writer trigger, which follow their feature document. Decide
  or verify with one parallel batch: at most three calls and roughly 10k tokens of evidence. Use bounded searches and
  line ranges, not whole large files. One understood change stays inline even when it spans files.
- **Delegated direct** — understanding that needs more evidence takes one read-only explorer, then size is
  re-evaluated; a writer is delegated only by the Writer trigger.
- File count, changed lines, size, or perceived risk alone never forces a heavier route.

## Runtime mapping

| Role | Framework profile | Cursor | Claude Code |
| --- | --- | --- | --- |
| Read-only explorer, RDD reviewer, refuter | `investigator` | the `investigator` subagent, by name | `Explore` subagent for mapping; general-purpose subagent told it is read-only for review |
| Writer | `implementer` | the `implementer` subagent, by name | general-purpose subagent |
| Independent verifier | `qa-verifier` | the `qa-verifier` subagent, by name | general-purpose subagent told it is read-only |

Every subagent runs on the model the repository pins for its profile, never on the parent's by inheritance. In Cursor,
launch the profile's custom subagent by its name — `.cursor/agents/<profile>.md` carries the pinned `model:` — rather
than a generic subagent. In Claude Code, pass the profile's pin from the repository's model assignment file as the
subagent's model. When the named subagent does not exist in the repository, report it and pass the pin explicitly.

## Triggers

Each trigger holds only when its condition truly holds, and then it is mandatory. No trigger holds by default; when in
doubt, work inline. When one fires, stop and delegate before continuing — executing past a fired trigger inline is a
routing defect even when the work succeeds. When it resolves, re-evaluate task size.

- **Ask** — an open product or design decision gets one focused question; stop and wait.
- **Mapping** — understanding exceeds the inline batch or needs more than about five sequential lookups: delegate one
  read-only explorer before deciding or writing. It returns at most about 2k tokens with `path:line` evidence; the
  parent spot-checks once and does not reread the mapped evidence. Never explore files you will read anyway.
- **Verification** — only a change whose Risk line names a high-risk item gets an independent verifier, after the
  change's own checks, as rarely as possible. A risk tier, an unclear or failed assessment, or the writer's model never
  add one by themselves. Otherwise whoever made the change runs its focused test and suite inline.
- **Tracking** — a large task gets the feature document, its mirror, and work-unit commits.
- **Writer** — a writer is delegated only for a named reason, one bounded writer per unit: (a) parallelism — two or
  more independent units with disjoint edit surfaces, each needing several minutes of work (several files or roughly
  100+ changed lines), launched together; (b) context — the long-session backstop. A unit is one behavior with its
  code, tests, and docs together; never split one behavior into test, docs, and code writers. Units of about 100
  changed lines or less always run inline. Never delegate for size, file count, or a large task alone.
- **Preparation** — when the Writer trigger delegates a write, delegate the reading that prepares it with or ahead of
  the write. Inline writes read inline.

## Parallel writers

- Work in another repository goes in a fresh worktree based on that repository's main, never in a checkout someone else
  may be using.
- Parallel units in one repository run in the same tree with declared disjoint edit surfaces. The parent owns git;
  writers run no repository-wide formatters, generators, or installs; a shared file has one owner, or the parent edits
  it at the end; the parent checks each writer's diff against its surface; one seam check — the full suite, once —
  runs at the end. Units that need the same file use isolated worktrees.
- **Invariants** — each writer prompt names the existing helpers its unit must reuse for shared state (for example the
  function that adds an entry other commands also add) and the invariants they keep: ordering, uniqueness, validation,
  normalization. Parallel units cannot see each other, so the prompt is the only place they learn them.

## Budgets

- Keep parent shell output bounded to counts, `--stat`, `tail`, or summaries. On a large task, delegate long suites and
  builds and return concise observed results, failures included.
- Long-session backstop: around 150k parent-context tokens, pause and delegate the next bounded unit. This is advisory;
  do not claim it is measured or enforced.
- For large work, record the chosen route per task and the trigger evidence in the feature document, so skipped
  delegation is observable rather than silent.
- An applicable quick check runs once. An unavailable verifier or subagent is reported as unavailable — never retried
  or escalated into extra ceremony.

## Learnings

- Every explorer, writer, and verifier prompt asks the worker to close its final response with a `## Key Learnings`
  block: one to five numbered, standalone factual sentences about the repository or its toolchain that a later session
  would otherwise rediscover — a command that fails silently, a hidden dependency, a convention the code does not
  state. A worker that learned nothing reusable omits the block; never pad it.
- A worker that must return strict JSON — an RDD reviewer or refuter returning its findings ledger — never receives
  this instruction.
- The parent confirms each item against the code or a command, drops any that a test, the diff, or an existing
  document already states, and routes the rest:
  - feature-specific — one `## Log` line in the feature document, when the task has one;
  - a repository-wide hazard that cost real work — propose it to the user as an `AGENTS.md` environment hazard or a
    standards edit; never write it unasked;
  - anything else — the runtime's persistent memory when one is configured; otherwise drop it.
