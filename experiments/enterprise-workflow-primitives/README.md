# Enterprise workflow primitives

This experiment verifies several lower-level OpenHands capabilities that a
multi-agent controller can use without querying OpenHands internal tables.
The probe was adapted from patterns in
[`jpshackelford/oh-examples`](https://github.com/jpshackelford/oh-examples),
which is MIT licensed.

## What was tested

The final probe ran against OpenHands Enterprise `0.24.0` on the Rajistics
Replicated installation on 2026-07-27. It created one sandbox and one short
conversation, then deleted both resources.

| Capability | Result | What the probe established |
| --- | --- | --- |
| Capacity gate | Passed | The controller observed zero active sandboxes before launch. |
| Explicit sandbox creation | Passed | `POST /api/v1/sandboxes` created a sandbox without creating a conversation. |
| Explicit conversation attachment | Passed | A V1 app conversation accepted that sandbox ID and ran in the prepared sandbox. |
| Conversation tags | Passed | Campaign, task, attempt, and controller IDs were written through the agent server and later appeared on the app-conversation record. |
| Agent-server idle signal | Passed | `/server_info` returned `idle_time` and a platform idle timeout of 3,600 seconds. |
| WebSocket completion | Passed | The event stream replayed a provisional `finished` event followed by an authoritative `full_state` confirmation. |
| REST reconciliation | Passed | The app record and durable event path independently reported the conversation as finished. |
| Usage metrics | Passed | The app record included cost and token metrics. |
| Cleanup | Passed | Deleting the last conversation also removed its prepared sandbox. |

The final run used 349 prompt tokens, 417 completion tokens, and $0.0080322 of
reported model cost. These figures describe the compatibility probe, not a
performance benchmark.

The sanitized result is in
[`results-2026-07-27.json`](results-2026-07-27.json). Three earlier probe
records are retained because they exposed response-shape details that customer
code should handle:

1. A tag `PATCH` returned an acknowledgement instead of the updated
   conversation. The client now re-reads the authoritative agent record.
2. Deleting the last conversation automatically deleted its sandbox, so a
   second sandbox deletion returned `404`.
3. A lookup for a recently deleted sandbox returned a null tombstone. The
   client now treats it as a missing resource.

None of these failures left an active sandbox.

## Run the probe

The script refuses to create a sandbox unless `--live` is present. Keep the
API key in an external environment file.

```bash
PYTHONPATH=src uv run --with 'websockets>=15,<16' \
  python experiments/enterprise-workflow-primitives/probe.py \
  --base-url https://app.your-openhands.example \
  --env-file /path/to/openhands.env \
  --output /tmp/workflow-primitives.json \
  --runtime-capacity 10 \
  --launch-lock-at 7 \
  --cleanup delete \
  --live
```

Use `--cleanup pause` when the resulting conversation must remain available for
inspection. Pausing releases active compute but retains the workspace storage.

## Controller integration

The reusable implementation is split between:

- [`research_lab.openhands`](../../src/research_lab/openhands.py), which handles
  explicit sandbox creation, attachment, tags, idle information, REST
  reconciliation, metrics, and cleanup; and
- [`research_lab.enterprise_events`](../../src/research_lab/enterprise_events.py),
  which handles first-message WebSocket authentication, event replay, and
  confirmed terminal-state detection.

The WebSocket is the fast path. A production controller still needs a periodic
REST reconciliation loop because a callback or socket can be lost when a
sandbox, connection, or controller process fails.

## Limits

- This was a one-conversation compatibility test, not a concurrency benchmark.
- The WebSocket helper has an optional `websockets` dependency; the rest of the
  project remains dependency-free.
- `idle_time` is a sandbox-wide heartbeat. It does not identify which
  conversation finished or distinguish success from failure.
- Tag keys on the tested agent server are lowercase alphanumeric strings. Tag
  values are limited to 256 characters. Agent-server writes become visible on
  the app server asynchronously.
- Prepared sandbox pooling, scoped secrets, finish callbacks, and shared
  workspace isolation need separate bounded load and failure tests before they
  are customer recommendations.

## Source examples

- [Clone and attach](https://github.com/jpshackelford/oh-examples/tree/main/clone-and-attach)
- [Conversation tags](https://github.com/jpshackelford/oh-examples/tree/main/conversation-tags)
- [Confirmed terminal state](https://github.com/jpshackelford/oh-examples/tree/main/watch-terminal-state)
- [Server idle information](https://github.com/jpshackelford/oh-examples/tree/main/server-info-idle)
- [Conversation metrics](https://github.com/jpshackelford/oh-examples/tree/main/conversation-metrics)
- [Sandbox archival and deletion](https://github.com/jpshackelford/oh-examples/tree/main/archive-sandbox)
