---
name: bugfix-lite
description: Lightweight bugfix loop: coding investigates and patches; eval verifies; stop after 1–2 failed loops.
---

# bugfix-lite

1. Reproduce or confirm failure evidence
2. Spawn `coding` for a minimal fix
3. Spawn `eval` to verify
4. After 1–2 failed loops, return `DEBUG_BLOCKER` to parent

No merge without human intent.
