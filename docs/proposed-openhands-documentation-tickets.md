# Proposed OpenHands documentation tickets

These are documentation gaps identified while adapting
[`jpshackelford/oh-examples`](https://github.com/jpshackelford/oh-examples) to
the tested OpenHands Enterprise `0.24.0` Replicated deployment. They are
proposals, not filed issues.

## OH-DOCS-1: Document explicit sandbox preparation and conversation attachment

**Suggested location**

- OpenHands Cloud API V1 guide
- App-conversation start reference
- Sandbox lifecycle guide

**Add**

- The complete sequence: create sandbox, wait for `RUNNING`, prepare the
  workspace, start an app conversation with `sandbox_id`, poll the start task.
- A warning that start-task ID, app-conversation ID, and sandbox ID are
  different identifiers.
- Guidance on when explicit attachment is preferable to automatic grouping.
- A statement that attachment controls placement but does not create an
  isolation boundary.

**Evidence**

The local probe attached conversation `64417ebe...` to prepared sandbox
`22YfigLm...` on Enterprise `0.24.0`.

## OH-DOCS-2: Document conversation tags across app and agent APIs

**Suggested location**

- Conversation API reference
- Observability and external workflow integration guide

**Add**

- Tags are written on the agent-side conversation and surfaced later on the app
  conversation.
- Agent-server URL and per-sandbox session authentication are required.
- Allowed key syntax, value limit, and eventual-consistency behavior.
- `PATCH` replaces the complete map, so clients must read, merge, write, and
  then re-read.
- The tested Enterprise version returns an acknowledgement rather than the
  updated conversation from `PATCH`.

## OH-DOCS-3: Define authoritative terminal-state handling

**Suggested location**

- Agent Server WebSocket guide
- Conversation lifecycle reference
- Hooks guide

**Add**

- Both `ConversationStateUpdateEvent` shapes.
- Per-field `finished` is provisional when a stop hook can resume execution.
- `full_state.execution_status=finished` is the confirmation.
- `error` and `stuck` are immediately terminal.
- First-message WebSocket authentication keeps session keys out of URLs and
  proxy logs.
- `resend_mode=all` closes the create-to-connect race.
- WebSocket or callback notification must be paired with bounded REST
  reconciliation.

## OH-DOCS-4: Explain idle state versus conversation completion

**Suggested location**

- Runtime lifecycle guide
- Agent Server `/server_info` reference

**Add**

- `idle_time` is a sandbox-wide activity signal.
- `runtime_idle_timeout_seconds` is the platform reaping threshold when
  available.
- Idle does not distinguish finished, error, stuck, waiting, or a long model
  call.
- Use conversation state for correctness and idle state for sandbox resource
  management.

## OH-DOCS-5: Clarify pause, delete, workspace retention, and shared sandboxes

**Suggested location**

- Enterprise sandbox lifecycle guide
- Kubernetes installation storage guide

**Add**

- A resource table for running, paused, stopped, and deleted states.
- Which states retain PVC or archived workspace data.
- Deleting the last conversation may automatically delete its sandbox.
- A missing sandbox after conversation deletion is successful cleanup, not an
  error requiring a retry.
- Force-deleting a sandbox can affect every attached conversation.
- Recommended pause, retention, artifact-export, and deletion sequence.

## OH-DOCS-6: Publish an API compatibility matrix

**Suggested location**

- V1 API overview
- Enterprise release notes

**Add**

- Minimum product and agent-server versions for `sandbox_id`, create-time
  secrets, plugins, conversation tags, WebSocket replay, metrics, and idle
  timeout fields.
- App-server authentication versus agent-server session authentication.
- Expected response shapes that differ across supported releases.

This would prevent Cloud examples from being copied into an older Enterprise
installation without a capability check.

## OH-DOCS-7: Add a production controller recipe

**Suggested location**

- Multi-agent or delegation guide
- Enterprise automation guide

**Add**

- Capacity gate and bounded concurrency.
- Immutable controller, campaign, task, attempt, start-task, conversation, and
  sandbox identifiers.
- Event-driven completion plus reconciliation polling.
- Final-response grace period and strict output contracts.
- Shared-sandbox cleanup ownership.
- Durable application state outside OpenHands internal tables.
- Failure injection and idempotent cleanup acceptance tests.

The reference implementation is
[`docs/enterprise-workflow-primitives.md`](enterprise-workflow-primitives.md)
and
[`experiments/enterprise-workflow-primitives`](../experiments/enterprise-workflow-primitives/README.md).
