# Enterprise sandbox grouping pilot

This experiment tests the OpenHands Enterprise sandbox grouping controls. It
keeps first-class Enterprise conversations, event history, and UI links while
allowing several conversations to share one runtime sandbox.

The pilot is intentionally bounded for a small installation:

- OpenHands Enterprise creates and records every conversation through V1.
- The user-visible runtime limit is 10.
- The controller refuses launches at seven active sandboxes.
- One clean sandbox is seeded before grouping is enabled.
- Sequential reuse is proven before concurrency is attempted.
- Concurrent testing is limited to two conversations.
- The shared sandbox is paused once, after every conversation is terminal.

## Why seed the sandbox first

`Group by Newest` attaches new conversations to the most recent eligible
sandbox. Enabling it while many historical sandboxes exist could select an old
workspace. The controlled sequence is:

1. Leave `Sandbox Grouping Strategy` on `No Grouping`.
2. Start one bounded conversation with `--keep-sandbox`.
3. Verify that it is the only active sandbox and save its immutable ID.
4. Change the setting to `Group by Newest`.
5. Confirm `/api/v1/users/me` reports `GROUP_BY_NEWEST`.
6. Start two sequential conversations and compare their sandbox IDs.
7. Start no more than two concurrent conversations in separate controller
   stores.
8. Wait until every conversation is terminal.
9. Pause the shared sandbox once through the supported V1 endpoint.
10. Verify zero active user-visible sandboxes and check cluster health.

## Acceptance criteria

- Every attempt has a distinct first-class Enterprise conversation ID.
- Every start task reaches `READY`.
- Every attempt records the same sandbox ID as the seed.
- Every candidate is independently validated.
- Concurrent attempts use distinct archived workspace paths.
- Active sandbox count never exceeds one.
- No conversation pauses the shared sandbox while another is running.
- The pool owner pauses the sandbox after the last lease is released.
- The API reaches `PAUSED`, and the runtime service confirms that the claimed
  runtime resources were removed.

## Production lifecycle rule

The repository's default one-conversation mode pauses a sandbox after each
attempt. Do not use that policy unchanged with grouping.

A grouped sandbox needs one lifecycle owner:

```text
acquire pool lease
  -> create first-class conversation
  -> run and validate
  -> mark conversation terminal
  -> release lease
  -> if lease count is zero, pause the sandbox
```

Until the controller implements that lease or reference-count boundary, grouped
campaigns must use `--keep-sandbox` for individual attempts and perform one
verified pause after the complete bounded batch.

## Trust boundary

Sandbox grouping is suitable for trusted agents working for the same user or
team. Conversations retain separate histories and workspace archive paths, but
they share runtime compute and therefore share a larger failure and security
boundary. Use one sandbox per conversation for untrusted code, different
tenants, or work requiring strong isolation.

See [results-2026-07-25.md](results-2026-07-25.md) for the live result.
