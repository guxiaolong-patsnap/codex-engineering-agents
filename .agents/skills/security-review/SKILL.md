---
name: security-review
description: Dispatch the security subagent to audit authentication, injection, data exposure, and dependency risks without changing code.
---

# Security review

1. Scope files / endpoints / flows.
2. `Spawn security to review …`
3. Report findings Critical → Low with remediation.

Read-only unless the user authorizes a patch. No secrets in the report.

```text
$security-review the OAuth callback and session cookies on this branch
```
