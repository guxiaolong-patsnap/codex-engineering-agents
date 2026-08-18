---
name: issue-pipeline
description: Issue- or AC-driven SDLC — spawn coding to implement, then security to audit, then hand back for human merge request.
---

# issue-pipeline

## Steps

1. Restate issue/AC and out-of-scope.
2. `Spawn coding to implement …` — wait for handoff; do not merge.
3. `Spawn security to audit the coding change for OWASP risks`.
4. Summarize diffs, validation, security findings; next human action is open MR / fix / approve.

## Constraints

- Agents must exist in `.codex/agents/` (open/Trust this product repo after `$eng-agents-setup`)
- No force-push or merge to protected branches
- No invented requirements; escalate AC gaps

```text
$issue-pipeline for issue #42: add rate limiting to POST /api/login
```
