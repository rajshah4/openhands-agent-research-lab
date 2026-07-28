# Reusable OpenHands Enterprise workflow primitives

The campaign controller needs more than a conversation-start endpoint. It must
place work, identify it, observe completion, reconcile missed events, record
usage, and release resources. OpenHands Enterprise exposes supported APIs for
each of these operations.

The examples below were verified against OpenHands Enterprise `0.24.0` on the
Rajistics Replicated installation. Re-run the included probe after changing the
OpenHands version, runtime image, authentication configuration, or network
path.

## Recommended control flow

```text
check capacity
  -> select or create a sandbox
  -> attach a tagged conversation
  -> watch its event stream
  -> confirm terminal state
  -> retrieve and validate the final response
  -> record usage and durable artifacts
  -> pause for near-term recovery or delete after retention expires
  -> periodically reconcile through the app API
```

This extends the Git-backed controller already used in this repository. Git
remains the durable campaign ledger. OpenHands tags make its conversations
easier to correlate with that ledger; they do not replace it.

## 1. Make placement explicit when needed

The controller can create a sandbox independently, wait for it to reach
`RUNNING`, prepare it, and pass its ID to
`POST /api/v1/app-conversations`. This provides deterministic placement for a
small warm pool.

Use explicit attachment when:

- setup is expensive enough to justify pre-warming;
- the controller must choose a particular trust or resource pool;
- several trusted conversations intentionally share one prepared environment.

The instance-wide grouping strategy remains simpler when exact placement is
not required. Explicit attachment does not make a shared sandbox an isolation
boundary.

## 2. Correlate conversations with durable work

Write short identifiers such as:

```json
{
  "campaignid": "workflowprimitives",
  "taskid": "compatibilityprobe",
  "attemptid": "20260727t235611z",
  "controllerid": "externalprobe"
}
```

On the tested version, tags are written to the agent-side conversation and
appear later on the app-conversation record. The write must use a
read-modify-write operation because `PATCH` replaces the complete tag map.

Do not store prompts, credentials, full result contracts, or campaign state in
tags. Store those in the application ledger and use tags only as correlation
keys.

## 3. Use events for speed and REST for recovery

The agent-server WebSocket provides immediate execution-state events. Connect
with first-message session authentication and `resend_mode=all` so events
emitted between creation and connection are replayed.

A per-field `execution_status=finished` event is provisional because a stop
hook can resume execution. Wait for `full_state.execution_status=finished`.
`error` and `stuck` are terminal without that extra confirmation.

Do not remove periodic REST reconciliation. The controller must still recover
when:

- it restarts after a worker was created;
- the socket disconnects;
- a callback never arrives;
- the app record and event index converge at different times;
- the final response is indexed after the terminal event.

This is the same controller pattern used in other reliable systems: event
notifications reduce latency, while reconciliation restores the desired state.

## 4. Keep idle and completion separate

`GET /server_info` returns a sandbox-wide `idle_time`. The tested installation
also returned `runtime_idle_timeout_seconds=3600`.

Use this signal to decide whether an entire grouped sandbox has gone quiet.
Do not use it as proof that a particular conversation succeeded. Conversation
terminal state and its validated result remain the completion authority.

## 5. Record usage from the app conversation

The tested app-conversation record included:

- accumulated cost;
- prompt and completion tokens;
- cache token fields;
- reasoning tokens;
- context-window size.

Persist the raw sanitized metrics with the attempt. Reports should identify
whether a number came from the app record, an event fallback, or an
infrastructure estimate.

## 6. Separate pause from deletion

Use pause when a worker may need to resume during a bounded recovery window.
Pause releases active runtime capacity but retains conversation storage.

After the validated result and required workspace artifacts are in Git or
another durable store:

1. wait for the configured retention period;
2. confirm that no other conversation uses the sandbox;
3. delete the conversation;
4. verify that the sandbox disappeared or delete it explicitly if it remains.

On the final compatibility run, deleting the only conversation automatically
removed its prepared sandbox. A controller must treat an already-missing
sandbox as successful idempotent cleanup.

Never force-delete a shared sandbox based only on idle time.

## Verification

The executable probe, unit tests, intermediate failures, and sanitized final
result are in
[`experiments/enterprise-workflow-primitives`](../experiments/enterprise-workflow-primitives/README.md).
Run that probe before enabling these paths for a customer deployment.
