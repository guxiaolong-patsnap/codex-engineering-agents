---
name: security-review
description: Spawn security subagent to audit auth, injection, data exposure, and dependency risks.
---

# security-review

1. Scope files / endpoints / flows.
2. `Spawn security to review …`
3. Report findings Critical → Low with remediation.

Read-only unless the user authorizes a patch. No secrets in the report.

```text
$security-review the OAuth callback and session cookies on this branch
```
