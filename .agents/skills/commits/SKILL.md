---
name: commits
description: Enforces commit conventions and when to create commits. Use when the user asks to create commits, write commit messages, or when discussing git commits, staging, or Conventional Commits. Do not run git commit or suggest committing unless the user explicitly asks.
---

# Commit rule

Guides the agent on when to create commits and how to format commit messages using Conventional Commits. Ensures granular, traceable commits and forbids tool or language references in messages.

## When to commit

- **Do not create commits** unless the user explicitly asks (e.g. "create the commits", "commit these changes").
- If the user does not mention commits, do not run `git commit` or suggest committing.

## Message format

- Use **Conventional Commits** in English: short and descriptive: `type: short description`.
- Common types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`.
- Keep the message **brief** (like a title), in English.

**Examples:**

```
feat: add user validation in signup
fix: prevent null in profile resolver
refactor: extract auth logic to service
```

**Forbidden:**

- Including "Made with Cursor" or any Cursor references in the message.
- Long messages or messages in another language when the project standard is English.

## Granular commits

- When the user asks to create commits, **do not** put all changes in a single commit.
- Make **one commit per logical change** (per distinct feature, fix, or refactor) for better traceability.
- Review changes (`git status` / diff) and group by files or blocks that belong to the same change.

**Example:** If there are changes in `auth.service.ts`, `user.controller.ts`, and `README.md`:

- One commit for auth: `refactor: move validation to auth service`
- One commit for user: `fix: handle missing user in controller`
- One commit for docs: `docs: update API section in README`

## Summary

| What           | How                                                       |
| -------------- | --------------------------------------------------------- |
| When to commit | Only when the user asks                                   |
| Message        | `type: short description in English`                      |
| Forbidden      | "Made with Cursor" in the message                         |
| Structure      | Multiple granular commits, not one commit with everything |
