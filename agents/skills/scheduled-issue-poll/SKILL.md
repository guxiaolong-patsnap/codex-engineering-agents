---
name: scheduled-issue-poll
description: Poll configured GitLab projects for eligible engineering issues and route one safely through the repository's issue pipeline during a scheduled run.
---

# Scheduled issue poll

Use this skill only inside a runtime project prepared by the `eng-agents` control-plane plugin. The runtime owns project bindings, schedule state, credentials, locking, and claim persistence; this catalog owns only the workflow behavior.

## Workflow

1. Read the runtime-provided project bindings and issue-selection policy. If either is unavailable, stop with `BLOCKED`; do not invent a repository or configuration.
2. Use the catalog-declared `company-gitlab` integration to list eligible open issues. Keep the query read-only and narrow to the configured projects and policy.
3. Select at most one unclaimed issue deterministically using the runtime policy. If there is no eligible issue, report `NO_WORK` and stop.
4. Form a claim key from the stable project ID, issue IID, and GitLab `updatedAt` (or another configured immutable issue revision), then use the generated helper from the runtime instance (`.eng-agents/runtime_state.py`) to run `claim-acquire --issue <project-iid-revision> --owner <scheduled-run-owner-id>`. Retain the returned fencing token. If it returns `BUSY` or `ALREADY_COMPLETED`, report `NO_WORK` and stop; never process the same issue revision concurrently or twice.
5. Invoke `$issue-pipeline` with the selected issue, its acceptance criteria, repository binding, and explicit out-of-scope notes.
6. If work approaches the lease/claim TTL, run `lease-renew` and `claim-renew` with the same owner and each acquisition's `--token` before expiry; stop safely if renewal fails.
7. On successful handoff, run `claim-complete` with the same issue, owner, and claim token. On a retryable failure, run `claim-release` with the same fencing data. Return the pipeline handoff and stable issue identity; the runtime owns cursors, claims, run records, expiry recovery, and schedule state.

## Constraints

- Do not create, update, close, label, or comment on GitLab issues unless the scheduled-task policy separately grants that mutation.
- Do not clone repositories, create schedules, choose models, or write runtime configuration.
- Do not expose credentials or token-cache contents.
- Do not merge or force-push.
- Stop after one issue per invocation.
