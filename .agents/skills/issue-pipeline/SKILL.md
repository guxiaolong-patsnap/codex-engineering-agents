---
name: issue-pipeline
description: Run an issue- or acceptance-criteria-driven SDLC handoff by dispatching coding implementation and security review without merging.
---

# Issue pipeline

## Steps

1. Restate issue/AC and out-of-scope.
2. `Spawn coding to implement …` — wait for handoff; do not merge.
3. `Spawn security to audit the coding change for OWASP risks`.
4. Summarize diffs, validation, security findings; next human action is open MR / fix / approve.

## Constraints

- The runtime must provide the catalog-declared `coding` and `security` agents
- No force-push or merge to protected branches
- No invented requirements; escalate AC gaps

```text
$issue-pipeline for issue #42: add rate limiting to POST /api/login
```
