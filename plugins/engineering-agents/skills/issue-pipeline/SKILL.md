---
name: issue-pipeline
description: Issue- or AC-driven SDLC — spawn coding to implement, then security to audit, then hand back for human merge request.
---

# issue-pipeline

## When to use

- User supplies an issue, ticket URL, or acceptance criteria
- Feature work, bugfix, or refactor with a clear done definition
- After `$project-install` when working in a repo without agents yet

## Prerequisites

- `coding` and `security` subagents available (plugin sync or project install)
- `[features] multi_agent_v2 = true` and `[agents] enabled = true` in config
- User has trusted the project when using project-scoped agents

## Steps

1. **Parse goal**
   - Restate issue/AC and out-of-scope
   - Identify target repo paths and validation commands if known
2. **Spawn coding**
   - `Spawn coding to implement …` with explicit AC and constraints
   - Wait for handoff; do not merge
3. **Spawn security**
   - `Spawn security to audit the coding change for OWASP risks`
   - Read-only; prioritize exploitable findings
4. **Synthesize**
   - Summary of diffs, validation run, security findings (severity order)
   - Next human action: open MR, fix blockers, or approve

## Constraints

- Do not force-push or merge protected branches
- Do not invent requirements; escalate AC gaps to the user
- No secrets in summaries or board output

## Example

```text
$issue-pipeline for issue #42: add rate limiting to POST /api/login; include unit tests
```
