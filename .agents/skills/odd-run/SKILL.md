---
name: odd-run
description: Run the whole Organic Driven Development (ODD) flow on one request in a single invocation — authorize, explore, resolve uncertainty, classify by task size, track large work in a feature document, implement every task test-first with work-unit commits, assess each commit with RDD when it is on, apply the delivery strategy, and close — stopping only at the gates where the user must answer. Use when the user wants one command from request to delivered change, says "ODD run" or "do the whole thing", or resumes a feature with "continue".
preferred_profile: orchestrator
escalation_profile: investigator
---

# ODD Run — one full pass

## Mission

Carry one request through the whole flow in one invocation, following [odd](../odd/SKILL.md) exactly. This skill adds
no rule; it removes the pauses between steps and names where the pass must stop.

## The pass

```mermaid
flowchart TD
    A[Request] --> B{Implementation authorized?}
    B -->|No| C[Explore or explain without task artifacts]
    B -->|Yes| D[Explore existing code]
    D --> E{Research useful and selected?}
    E -->|Yes| F[Scoped research]
    E -->|No| G[Resolve real scope decisions only]
    F --> G
    G --> H{High-consequence unproven premise?}
    H -->|Yes| I[One independent assumption challenge]
    H -->|No| J{Substantial implementation?}
    I --> J
    J -->|Yes| K[One feature document and full mirror]
    J -->|No| L[Small work without durable task artifacts]
    K --> TT[Resolve applicable test-first policy and runner]
    L --> TT
    TT --> M[Implement next authorized task]
    M --> N[Applicable proportionate checks]
    N --> Q[Record truthful results]
    Q --> QC[Commit work units in reviewable slices, high-risk units alone]
    QC --> R{Tracked feature?}
    R -->|No| O{RDD user-enabled at work-unit commit boundary?}
    R -->|Yes| T[Update intent, tasks and full mirror]
    T --> U{Work remains or requirements changed?}
    U -->|Yes| V[Revise affected tasks within authorized scope]
    V --> M
    U -->|No| O
    O -->|Yes| P{Candidate risk assessment}
    O -->|No| AB[Ordinary checks and policy]
    P -->|Passive| AC[Silent structural checks; no reviewer or prompt]
    P -->|Medium or high| AD{Candidate consent}
    P -->|Unavailable| AE[Treat as due; never assume low]
    AD -->|Granted| AF[Review plan: lenses, refuters, one correction]
    AD -->|Declined| AB
    AC --> Y[Existing delivery gates]
    AF --> Y
    AE --> AD
    AB --> Y
    Y --> AG{Running authored lines over 400?}
    AG -->|Yes| AH[Apply delivery strategy: chained PR slice]
    AG -->|No| S{Publish offer}
    AH --> S
    S -->|1| PR[Push and open draft PR with pr-builder]
    S -->|2| BR[Branch and evidence; you publish]
    W[Resume interrupted feature] --> X[Read task file and mirror; reconcile evidence]
    X --> TT
```

Before each phase, print one line naming it — authorizing, exploring, researching, deciding, implementing, checking,
reviewing, closing — and only when the phase actually changes.

## Gates — where the pass stops

- **Authorize** — ambiguous change intent: one clarification, then wait.
- **Ask trigger** — a real product or design decision: one focused question, then wait.
- **RDD consent** — a medium or high candidate: the consent question, then wait.
- **Chain strategy** — `ask-on-risk` and the budget is exceeded with no cached chain strategy: ask once, then wait.
- **Needs your decision** — partial, blocked, unavailable, or exhausted proof, or an escalated review.
- **Publish** — the close offer: `1` pushes and opens the draft pull request or chained drafts, `2` ends with the branch
  and its evidence. Marking ready and merge always stay the user's.

A pass MUST NOT skip a gate to finish faster, and MUST NOT end with a tracked task pending unless it quotes the user's
explicit stop.

## Resuming

"Continue" resumes from durable state, never from memory: the feature document and its mirror —
`odd_tasks.py status` and `mirror check` — then `git log` and `rdd.py status --next`. Reconcile, name the phase being
resumed, and carry on from the gate that stopped the pass.

## Final report

```text
ODD — <feature or request>
Size: <small | large> · Route: <inline | delegated per task>
Outcome: <verified result>
Tasks: <done>/<total> · Document: <DOCS_ROOT>/odd/tasks/<feature>.md · Mirror: <written | pending>
Checks: <command → result>, … · Not run: <…>
RDD per commit: <sha — tier, outcome>, … | disabled/unmanaged
Delivery: <strategy> · <lines>/400 · slices: <…> · PR: <draft links | not published>
Risk: <item N (reason) | none>
Next: <the user's decision, or none>
```
