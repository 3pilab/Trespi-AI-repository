---
name: worktree-branch-review
description: >-
  Create a Git worktree for a target branch, run a multi-agent code review
  against dev (unless the user clearly names another base), validate that
  origin/dev reflects the latest remote state (and flag stale local dev if
  present), deliver a consolidated report, then remove the worktree. Optionally
  post comments to GitHub via gh when the user explicitly asks. Use for PR/pull
  request review phrasing (e.g. “review this pull request on branch X”) or any
  isolated branch review with several reviewers.
metadata:
  tags: git, worktree, code-review, pr-review, multi-agent
  platforms: Cursor
---

# Worktree branch review (multi-agent)

## When to use (triggers)

Use this skill when the user’s message **clearly means a PR or branch review**, including paraphrases such as:

- “Review this **pull request** …” / “**PR** review …” / “review **this PR** …”
- “Review the changes on branch **X**” / “code review **branch X**”
- Same intent in Spanish: “revisar el **pull request**”, “**PR**”, “revisar la **rama** …”

Infer the **target branch** from the message (branch name, or PR number—see below). If the branch is missing, ask once; otherwise proceed.

---

## Default compare base: `dev`

- **Always** diff and scope the review **against `dev`**, using **`origin/dev`** as the base ref after fetch.
- **Only** use a different base if the user **explicitly** says so, e.g. “compare to `main`”, “against `origin/staging`”, “base branch is `release/1`”. Vague wording does **not** override the default—still use `dev`.

Before Phase 2, ensure `origin/dev` exists: `git fetch origin dev` (or `git fetch origin`).

If `origin/dev` is missing after fetch, say so and stop (or ask whether they use another default).

### Keep `dev` current (mandatory validation)

The review base must be **the latest `dev` on the remote**, not an outdated ref.

1. **Always** run `git fetch origin dev` (or `git fetch origin`, which updates all remote-tracking branches including `origin/dev`) **before** Phase 2 merge-base / diff. If fetch fails (network, auth), say so and either retry or state clearly that `origin/dev` may be stale.
2. Treat **`origin/dev`** after that fetch as the canonical base. Do not use a local `dev` checkout unless it is verified in step 3.
3. **If a local branch `dev` exists**, compare it to `origin/dev` from `REPO_ROOT`:
   - `git rev-parse --verify dev 2>/dev/null` — if this fails, skip (no local `dev`).
   - `BEHIND=$(git rev-list --count dev..origin/dev 2>/dev/null || echo 0)` — if `BEHIND` is greater than 0, **report in the Phase 4 header** that local `dev` is behind `origin/dev` by that many commits; the review still uses **`origin/dev`**. Optionally note that they can align with `git checkout dev && git pull origin dev` (do not run destructive git commands unless the user asked).
   - If local `dev` is **ahead** of `origin/dev` (unpushed commits on `dev`), mention that unusual state in the report so it is not mistaken for the shared base.

---

## Inputs (ask or infer)

1. **Target branch** to review (e.g. `feature/foo`, or `pr-123` after fetching the PR head).
2. **Base ref** — default: **`origin/dev`**. Override only on explicit user request (see above).
3. **Optional focus** (area, service, security, performance, public API).

**PR number only** (no branch name):  
`git fetch origin pull/<N>/head:pr-<N>` then target branch = `pr-<N>`. Still compare that tip to **`origin/dev`** unless they name another base.

---

## Phase 1: Fetch and create the worktree

1. Resolve repo root: `git rev-parse --show-toplevel`. Abort if not a Git repo.
2. **Fetch so `origin/dev` and the target are current:**
   - Run `git fetch origin` (or at least `git fetch origin dev` plus whatever updates the target ref) so **`origin/dev` matches the remote** before any merge-base—the mandatory “latest dev” check at the remote-tracking level.
   - If the **target branch is not available** after that (no `refs/heads/<branch>` and no `refs/remotes/origin/<branch>`), fetch it explicitly, e.g.  
     `git fetch origin "<branch>"`  
     or for a PR:  
     `git fetch origin pull/<N>/head:pr-<N>`.
   - Prefer checking with:  
     `git rev-parse --verify "origin/${BRANCH}" 2>/dev/null` or `git ls-remote --heads origin "${BRANCH}"`.
3. **Validate local `dev` vs `origin/dev`** (when base is default `dev`): follow **Keep `dev` current** above; record any local-behind/ahead note for the report.
4. Choose a **sibling path** (outside the main worktree):

   ```bash
   REPO_ROOT="$(git rev-parse --show-toplevel)"
   cd "$REPO_ROOT"
   BRANCH="<target-branch>"
   SAFE_SUFFIX="$(echo "$BRANCH" | tr '/' '-')"
   WT_PATH="$(dirname "$REPO_ROOT")/$(basename "$REPO_ROOT")-wt-${SAFE_SUFFIX}"
   ```

5. Add the worktree (remote-tracking first if the branch only exists on the remote):

   ```bash
   git worktree add "$WT_PATH" "origin/${BRANCH}" || git worktree add "$WT_PATH" "${BRANCH}"
   ```

6. Tell the user the **absolute path** of `WT_PATH`. All review reads use **`WT_PATH`** as context.

**Errors:** If the path exists or the branch is checked out elsewhere, adjust or stop—still plan **Phase 5** if a worktree path was created.

---

## Phase 2: Scope the change set

Use **`BASE_REF=origin/dev`** unless the user clearly chose another base.

Inside the worktree (or `git -C "$WT_PATH"`):

1. `git fetch origin` as needed so **`BASE_REF`** is up to date. When **`BASE_REF` is `origin/dev`**, this re-confirms the worktree sees the same fresh `origin/dev` as the main repo (shared remote-tracking refs after fetch from `REPO_ROOT` are usually enough; if in doubt, fetch again from `REPO_ROOT` or `git -C "$WT_PATH" fetch origin`).
2. `BASE_SHA=$(git merge-base HEAD "${BASE_REF}")`.
3. **Review context** (changes on the reviewed branch vs where it branched from `dev`):
   - `git diff "${BASE_SHA}...HEAD"`
   - `git diff --name-only "${BASE_SHA}...HEAD"`
4. State in the report header: **Base: `<BASE_REF>`** (normally `origin/dev`).
5. If the diff is huge, prioritize high-risk paths; still share the full file list with every reviewer.

---

## Phase 3: Multi-agent parallel review

Launch **three tasks in parallel** (for example three task-agent invocations in a single turn, or three focused passes if subagents are not available). Give each **the same diff / context** (or truncated diff + full file list), the **worktree root `WT_PATH`**, and any optional user **focus**.

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
7. Comments that only narrate what the code does or the task; keep only non-obvious why.

### Reviewer 3: efficiency

1. Redundant work: recomputation, repeated reads, duplicate calls, N+1.
2. Independent operations run sequentially that could run in parallel.
3. New work on hot paths (startup, per-request, per-render).
4. State/store updates without “no change” guards; updaters should honor same-reference no-ops where applicable.
5. Existence checks before operating (TOCTOU); prefer try and handle errors.
6. Memory: unbounded structures, missing cleanup, listener leaks.
7. Overly broad operations (read whole files, load everything to filter one).

### Additionally (good to keep in mind)

While running the three reviewers above, **also surface** findings in these areas when the diff makes them relevant (any reviewer may flag them; dedupe in Phase 4):

- **Correctness & behavior** — Logic bugs, edge cases, error handling, race/timeouts, off-by-one, null/undefined paths; consistency with domain rules (read related files under `WT_PATH` / main repo as needed).
- **Security & data** — Injection, authZ/authN gaps, secrets/logging PII, unsafe deserialization, path traversal, dependency risk in touched code.
- **Tests & observability** — Coverage for new behavior, brittle tests, logging/metrics where relevant (complements Reviewer 2).
- **API, contracts & ops** — Breaking public APIs, config/env migrations, backward compatibility, flags/rollout, obvious performance regressions.

**Output format:** Short, actionable findings, file paths (repo-relative), severity (block / major / minor / nit).

---

## Phase 4: Consolidated report

Merge into one report: summary, blockers, major/minor/nits, follow-ups. No code changes unless the user asked to apply fixes. Mention **base = `dev` (`origin/dev`)** unless overridden. If local `dev` was behind/ahead of `origin/dev`, repeat that **one-line** status in the header so the base is unambiguous.

---

## Optional: post the review to GitHub

**The skill file does not call GitHub by itself**—only the agent can, using tools the user has configured.

**When:** Only if the user **explicitly** asks to post/publish comments on GitHub (e.g. “leave this on the PR”, “comment on GitHub”). Otherwise keep the report in chat only.

**Requirements:**

- [GitHub CLI](https://cli.github.com/) `gh` installed and logged in (`gh auth status` OK).
- Remote is GitHub (`origin` → `github.com/...`).
- Resolve the PR: user gives a number, or run `gh pr list --head "<branch>" --json number,url` / `gh pr view --json number` from `REPO_ROOT`.

**Before removing the worktree**, capture the **head commit** of the reviewed branch (needed for line comments):

```bash
PR_HEAD_SHA="$(git -C "$WT_PATH" rev-parse HEAD)"
```

### A) One consolidated PR comment (simplest)

Post the Phase 4 summary as a single comment (trim if near GitHub size limits):

```bash
gh pr comment <PR_NUMBER> --repo "<owner>/<repo>" --body-file review.md
# or --body "..." for shorter text
```

### B) Inline / line comments

GitHub needs: **`commit_id`** (`PR_HEAD_SHA`), **`path`** (repo-relative), **`line`** (or `start_line` / `line` for multiline), and **`body`**.

Use `gh api` with the [create review comment](https://docs.github.com/en/rest/pulls/comments?apiVersion=2022-11-28#create-a-review-comment-for-a-pull-request) endpoint, or submit a full review via [create a review](https://docs.github.com/en/rest/pulls/reviews?apiVersion=2022-11-28#create-a-review-for-a-pull-request) with a `comments` array.

Map each finding to the correct **line in the PR diff** (new file side); wrong SHA or line yields a failed API call—verify against the file at `PR_HEAD_SHA`.

**Limits / policies:** Respect team norms (no spamming dozens of nits); prefer one summary comment unless the user asked for inline feedback. Do not post if `gh` is missing or unauthenticated—say so in chat.

---

## Phase 5: Remove the worktree (mandatory)

From **`REPO_ROOT`**:

```bash
git worktree remove "$WT_PATH"
git worktree prune
```

Use `--force` only if needed and after warning about discarding uncommitted changes in the worktree.

---

## Extra arguments

Scope text (e.g. “only `services/foo`”) applies in Phases 2–4 under **Review scope**.  
**Changing the diff base** requires explicit wording; otherwise stay on **`origin/dev`**.
