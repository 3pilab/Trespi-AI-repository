---
name: simplify
description: Review changed code for reuse, quality, and efficiency, then fix issues. Use after edits or before a PR when you want a structured multi-angle cleanup of the current diff.
metadata:
  tags: refactor, code-review, DRY, performance, cleanup
  platforms: Cursor
---

# Simplify: code review and cleanup

## When to use

- After a batch of local changes (before commit or PR).
- When the user explicitly asks to “simplify”, “clean up the diff”, or review quality / reuse / performance of touched code.

## Phase 1: identify changes

Run `git diff` (or `git diff HEAD` if there are staged changes). If there is no diff, review files the user mentioned or you edited earlier in the conversation.

Copy or summarize the full diff—the following steps need it as zcontext.

## Phase 2: three reviews in parallel

Launch **three tasks in parallel** (for example three task-agent invocations in a single turn, or three focused passes if subagents are not available). Give each **the same diff / context**.

### Reviewer 1: reuse

1. Search for existing utilities and helpers that could replace newly written code.
2. Flag new functions that duplicate existing behavior; point to the existing API.
3. Flag inline logic that could use utilities (strings, paths, env, ad-hoc type guards, etc.).

### Reviewer 2: quality

1. Redundant or derivable state; effects that could be direct calls.
2. Unnecessary parameter growth instead of restructuring.
3. Copy-paste with small variations that should be unified.
4. Leaky abstractions or exposed internal details.
5. Magic strings where constants, unions, or safer types already exist.
6. Unnecessary nested JSX (wrappers with no layout value).
7. Comments that only narrate wha¶t the code does or the task; keep only non-obvious why.

### Reviewer 3: efficiency

1. Redundant work: recomputation, repeated reads, duplicate calls, N+1.
2. Independent operations run sequentially that could run in parallel.
3. New work on hot paths (startup, per-request, per-render).
4. State/store updates without “no change” guards; updaters should honor same-reference no-ops where applicable.
5. Existence checks before operating (TOCTOU); prefer try and handle errors.
6. Memory: unbounded structures, missing cleanup, listener leaks.
7. Overly broad operations (read whole files, load everything to filter one).

## Phase 3: apply fixes

When all three reviews finish, **merge** findings and fix what makes sense in the code. If something is a false positive or not worth changing, skip it without arguing.

When done, briefly summarize what you fixed or confirm the code was already clean.

## Extra arguments

If the user adds text with the request (e.g. “focus on services X”), treat it as **additional scope or priority** under an “Additional focus” section and apply it in phases 2 and 3.
