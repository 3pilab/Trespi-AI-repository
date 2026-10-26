# Resolving uncertainty

Load this file when protocol step 3 has a trigger: a named uncertainty, an open product decision, or a
high-consequence unproven premise. Each mechanism turns on only by its own trigger; none is a phase, and none is
mandatory.

## Research depth without a new phase

Establish the problem, the intended outcome, the constraints, and the current evidence, then inspect the relevant code.
Depth adapts to uncertainty and consequence — no fixed questionnaire, no mandatory rounds.

- Recommend research only for a **named** uncertainty. If the user declines, continue within authorized scope only
  where it is safe without the missing evidence, disclose what stays uncertain, and pause only the decisions that
  depend on it.
- When the question needs external evidence, use the documentation and web tools the runtime authorizes, preferring
  primary sources. Attribute every material claim to a URL or a `path:line`. Distinguish verified facts, assumptions,
  contradictions, freshness, and gaps.
- When tools are unavailable, say so. Never invent access or evidence.
- Return concise findings: the recommendation, tradeoffs, open questions, and implementation implications. Offer a
  short proposal only when a real scope or product decision needs it; route a proposal the stakeholders must approve
  to [proposal-builder](../proposal-builder/SKILL.md).
- When delegating research, send these instructions to a fresh read-only exploration worker — in Claude Code the
  `Explore` subagent, in Cursor a read-only subagent, or the `investigator` profile. Do not create a specialized
  research agent. Research stays read-only and its findings authorize nothing.

## One focused question

The parent owns product decisions. Ask one focused question only for a real unresolved product or design decision,
then stop and wait. Use the runtime's question tool when it can carry the full choice set; otherwise print the whole
question with its options and the answer syntax. Workers return gaps to the parent; they never assume a choice.

### Desired ✅

```text
One decision blocks T2: should an over-limit request return 429 or queue the job?
1) 429 with Retry-After  2) Queue and return 202
Reply 1 or 2.
```

## One assumption challenge

Use at most one scoped, independent, read-only challenge for a high-consequence unproven premise — even in a small
security-critical change. Name the premise, the evidence, and the consequence if it is false. Do not start a debate
loop.

| Kind | Use it for |
| --- | --- |
| Counter-evidence search | "Nothing else calls X" — search every caller with `--hidden` or explicit paths, and show a hit for a string known to exist |
| Reproduction | "The bug is in X" — run the failing input and capture the output |
| Throwaway test | "The library already handles Y" — a scratch test outside the worktree, deleted after |
| Source read | "The API returns Z on error" — quote the implementation or vendor docs |

A challenge MUST be able to fail. A premise that does not hold changes the plan before anyone builds on it.
Deterministic failures — a red test, a compiler error — need fixes, not a challenge. RDD's own refuter owns review
claims; never duplicate or bypass it.

Validate consequential premises against available evidence before building, and reuse sibling investigation instead
of repeating it.
