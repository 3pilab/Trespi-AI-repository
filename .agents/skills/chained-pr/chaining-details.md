# Chaining details

Load this file when creating chained branches or writing a chained pull request body.

## Strategies

| | Stacked pull requests to main | Feature-branch chain |
| --- | --- | --- |
| Speed | Each slice ships in order | The whole feature waits for the tracker merge |
| Rollback | Revert individual main pull requests | Revert or hold the whole feature branch |
| Risk | Partial behavior may land | Nothing lands until the chain completes |
| Complexity | Simpler retarget and rebase flow | Needs a tracker and strict diff hygiene |

## Feature-branch chain

Use it when the feature branch accumulates the final integration while child pull requests are reviewed as focused
slices.

```text
main
 └── feat/my-feature              ← tracker and final integration branch
      ↑ PR 1 base: feat/my-feature
      └── feat/my-feature-01-core
           ↑ PR 2 base: feat/my-feature-01-core
           └── feat/my-feature-02-shared
                ↑ PR 3 base: feat/my-feature-02-shared
                └── feat/my-feature-03-slice
```

- Create the tracker branch from main and open its pull request to main as a draft marked do-not-merge.
- Create child 1 and target it at the tracker branch.
- Create each later child from the previous child's branch and target it at that parent.
- Integrate children in order; merge the tracker only after the chain is complete.

## Stacked pull requests to main

Use it when each slice can land on main in order.

```text
main <- PR 1: foundation
          └── PR 2: feature slice built on PR 1
                └── PR 3: docs and tests built on PR 2
```

After a parent merges, rebase or retarget the next pull request so it shows only its own slice.

## Chain Context section

Append it to the repository's pull request template; never replace required sections.

````markdown
## Chain Context

| Field | Value |
| --- | --- |
| Chain | <feature or stack name> |
| Tracker PR | <#NNN or "Not needed"> |
| Position | <N of total> |
| Base | `<target branch>` |
| Depends on | <PR or link, or "None"> |
| Follow-up | <next PR or "None"> |
| Review budget | <changed lines> / 400 |
| Starts at | <branch, PR, or state this builds on> |
| Ends with | <standalone result this PR delivers> |

### Chain overview

```text
main
 └── #NNN Previous PR
      └── 📍 #NNN This PR
           └── #NNN Next PR
```

### Scope
- Includes: <focused unit>
- Excludes: <deferred work>

### Autonomy
- [ ] CI is expected to pass for this branch
- [ ] This PR has one deliverable scope
- [ ] This PR can be rolled back without unrelated changes
- [ ] Tests, docs, or manual verification cover this unit
````

## Commands

Resolve the `gh` invocation from the repository's `AGENTS.md`; some repositories require an explicit repository or a
cleared token.

```bash
gh pr view <number> --json additions,deletions,changedFiles,title,url
gh pr create --draft --base feat/my-feature --title "<repository title convention>" --body-file <body.md>
gh pr create --draft --base feat/my-feature-01-core --title "<repository title convention>" --body-file <body.md>
```

## Reviewer guidance

- Ask for a split when a pull request exceeds 400 changed lines without a size exception.
- Recommend a feature-branch chain when work must integrate before main; stacked pull requests when each slice can
  merge on its own.
- Review a child against its immediate parent branch; a polluted diff is a branching bug.
