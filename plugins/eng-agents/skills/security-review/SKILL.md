---
name: security-review
description: Security-only audit — spawn the security subagent to review auth, injection, data exposure, and dependency risks on the current change or surface.
---

# security-review

## When to use

- Pre-merge security pass on a branch or diff
- Auth/API/design review without implementation work
- After coding changes when the user wants audit-only follow-up

## Steps

1. **Scope**
   - Identify files, endpoints, or flows under review
   - Note trust boundaries and sensitive data paths
2. **Spawn security**
   - `Spawn security to review …` with concrete scope (paths, APIs, auth flows)
3. **Report**
   - Severity-ordered findings (Critical → Low)
   - Remediation guidance; suggest `$issue-pipeline` or Spawn coding for fixes if needed

## Constraints

- Read-only unless the user explicitly authorizes a minimal patch plan
- No intrusive penetration testing without authorization
- Never include secrets or raw credentials in the report

## Example

```text
$security-review the OAuth callback handler and session cookie settings on this branch
```
