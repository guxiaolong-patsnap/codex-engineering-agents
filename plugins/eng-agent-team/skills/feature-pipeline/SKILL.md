---
name: feature-pipeline
description: Run a proportional feature pipeline using project subagents design → coding → eval; no merge without human intent.
---

# feature-pipeline

## Routing

1. Clarify AC with `design` if needed
2. Implement with `coding`
3. Gate with `eval`
4. `sre` only if explicitly requested for release/observe

Emit board steps via `$board-report`. Never merge without human intent.
