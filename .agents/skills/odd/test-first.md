# Test-first and checks

Load this file when implementing a behavior change. One default policy applies to every ODD behavior change; the
repository's own testing standards, routed by its `AGENTS.md`, still decide the layer and the tools.

## RED → GREEN → REFACTOR

When a relevant runnable deterministic test and a clear expected outcome exist: observe RED before implementing,
implement GREEN, then refactor while the tests stay green. Record the runner in the feature document and forward the
policy and runner to every implementation worker. Never invent a runner or RED/GREEN evidence.

Tests or frameworks merely being present do not establish applicability. For passive documentation, an unavailable
runner, or no meaningful runnable RED, state the exception and run proportionate functional or structural checks.

## What the tests assert

- Write one RED test per requested rule, covering the cases the rule itself names — its examples, boundaries, and
  errors.
- Assert every observable effect of the rule through the public interface, never internal storage: exit code, exact
  stdout and stderr, response status and body, and that rejected input leaves stored data and counters unchanged.
- For every existing command or option the change touches — it shares the code you changed: options, parsers,
  helpers, validation — add one test proving its previous behavior still holds. Add no other cases.
- When a user reports a failure, reproduce it before deciding it already works.
- When you add or change a command, option, or message, update the help text and docs that describe it.

## Differential check

Before finishing, run each existing command that shares the changed code with the new or changed input — for example
a new option passed to a sibling subcommand — against the previous code and against the change, comparing stdout,
stderr, and exit code. Build the previous code in a scratch directory from the base commit; never commit that copy,
and committed tests never read git history or a fixed commit. Any difference nobody asked for is a regression to fix
and pin with a test.

## Shared state

A record, list entry, file, or setting that other commands also create or read goes through the existing function
that already handles it, keeping its invariants — ordering, uniqueness, validation, normalization. Writer prompts name
those helpers ([delegation.md](./delegation.md) §Parallel writers).

## Scratch hygiene

Keep test scratch state — temporary directories, `HOME`, `TMPDIR`, tool caches — outside the worktree in a `mktemp -d`
directory. When it must live inside the worktree, use a path git ignores and remove it before finishing. Workers never
delete scratch: they report the exact paths, and the parent removes them.

## Checks per task

Run focused checks while iterating and every applicable full check at task closure. A checkbox does not trigger a
review cycle; the review candidate is a work-unit commit or a pull request slice — see [delivery.md](./delivery.md).
Keep spend proportional; there is no hard spend or line gate on checks.
