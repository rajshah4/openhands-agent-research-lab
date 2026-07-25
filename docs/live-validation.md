# Live validation log

## Rajistics Enterprise smoke test 1

Date: 2026-07-25

Environment:

- OpenHands Enterprise `0.24.0`
- Replicated deployment
- Base URL: `https://app.replicated.rajistics.com`
- Repository: `rajshah4/openhands-multi-agent-demo`
- Branch: `main`
- Attempt budget: `1`

Result:

- V1 `/api/v1/users/me` preflight passed.
- App-conversation start task reached `READY`.
- A sandbox and first-class app conversation were created.
- Conversation list state reached `finished`; event recovery was not required.
- Final-response retrieval observed 290 events and returned a strict JSON
  contract.
- The independent graph-coloring validator accepted the candidate.
- Score: 3 colors for the five-node cycle.
- The improving result promoted one validated lesson.
- No secret-bearing fields were found in persisted artifacts.

Immutable identifiers:

- Run: `graph-coloring-demo-20260725T195920Z-ec0d0e49`
- Start task: `7e4d104205824c339a97c9776ac7a1a2`
- Conversation: `69a96a0fd2ba4428a8ed50355e199826`
- Sandbox: `7ZccyucXHrZ9mgqWJdCAwT`

Conversation:

`https://app.replicated.rajistics.com/conversations/69a96a0fd2ba4428a8ed50355e199826`

Metadata confirmed on this deployment:

- conversation, parent-conversation, sandbox, repository, and branch IDs
- creation and update timestamps
- execution and sandbox status
- trigger, tags, agent kind, profile, and model
- accumulated cost, token usage, and task budget
- event kinds and counts

The application stores sanitized metadata snapshots and aggregate event counts,
not complete event payloads. Prompt-bearing fields are redacted from new
snapshots.

Next gate:

- Run one second child from the same store.
- Confirm that the validated lesson from smoke test 1 is retrieved and its ID is
  recorded in the second scheduler decision and attempt.

## Rajistics Enterprise smoke test 2

Date: 2026-07-25

Result:

- The scheduler retrieved the validated lesson from smoke test 1.
- The lesson ID was written to the scheduler decision before conversation
  creation.
- Start-task, sandbox, conversation, terminal state, and final response were all
  observed successfully.
- The agent returned a valid JSON contract after explanatory prose, violating
  the preferred exact-JSON transport.
- The original strict parser rejected the response, and the attempt remained a
  recorded failure instead of being silently inferred as successful.

Immutable identifiers:

- Run: `graph-coloring-demo-20260725T200118Z-14f9d892`
- Start task: `eb160812097c4ac2b57e4c9a0582bcba`
- Conversation: `f6613f0094234acb814f6baa2e2594b6`
- Sandbox: `Rbkfa31UPzvKz8zQxufJe`

Workaround:

- Continue to require exact JSON in the prompt.
- Accept a contract only when there is one structurally valid JSON object at
  the end of the response.
- Record this as `trailing-json-fallback` and
  `transport_compliant: false`.
- Continue to require independent deterministic validation before promotion.

Next gate:

- Run one bounded child with the compatibility parser and verify end-to-end
  validation while preserving the transport-compliance signal.

## Rajistics Enterprise smoke test 3

Date: 2026-07-25

Result:

- The validated lesson was retrieved again.
- The agent produced a valid fenced JSON contract.
- At the moment the conversation became terminal, the event index contained
  streaming deltas but not yet the completed agent `MessageEvent`.
- The original final-response extractor accepted a streaming fragment as if it
  were complete, so contract parsing failed.
- A later read of the same conversation showed the complete final
  `MessageEvent`, confirming an indexing race rather than an agent or validator
  failure.

Immutable identifiers:

- Run: `graph-coloring-demo-20260725T200320Z-65113b62`
- Conversation: `bd169539d6d4418480b271f8bc81284e`

Fix:

- `StreamingDeltaEvent` is no longer eligible as a final response.
- Only `FinishAction` or a completed agent `MessageEvent` can end the
  final-response grace loop.
- When neither is present, the client refetches events for a bounded number of
  retries.

Next gate:

- Run one bounded child to validate the corrected terminal-to-final indexing
  path end to end.

## Rajistics Enterprise smoke test 4

Date: 2026-07-25

Result:

- The full runner completed after the event-indexing fix.
- The scheduler retrieved `lesson-5d17ff7acf29e711`, which originated in smoke
  test 1.
- The child explicitly reported using the odd-cycle lesson.
- The completed `MessageEvent` was retrieved through the bounded final-response
  path.
- Contract transport was `exact-json` and compliant.
- The independent validator accepted the candidate with score 3.
- The artifact contains 255 aggregate events, lifecycle metadata, cost/token
  metric fields, and no detected secret-bearing keys.

Immutable identifiers:

- Run: `graph-coloring-demo-20260725T200523Z-662d6ad4`
- Start task: `137ce2d294c4420fada8362bf99ce655`
- Conversation: `0b0b9de0217c4df4b60067c9664c7d09`
- Sandbox: `6S4YZF2aYswyugkm2F9UvB`

Conversation:

`https://app.replicated.rajistics.com/conversations/0b0b9de0217c4df4b60067c9664c7d09`

Stage 2 conclusion:

- Supported V1 APIs are sufficient for the current execution and metadata
  path.
- Cross-conversation validated memory works without an external database.
- No access to OpenHands internal PostgreSQL tables was required.
- The file store remains intentionally single-controller; database work is not
  justified until concurrent writers or multi-tenant operational queries are a
  confirmed requirement.

Next gate:

- Publish this repository or choose its permanent remote.
- Add a matched naive-versus-managed experiment with fixed model, attempt,
  timeout, and concurrency budgets.
- Expand the benchmark beyond two illustrative graph instances.

## Stage 3 comparison pilot

Date: 2026-07-25

The first three-attempt-per-arm live comparison was stopped after the first
recorded attempt rather than spending the remaining budget on a repeated
protocol failure.

- Conversation `c8fb1f1a7108491cb08316439f7e35cd` finished with one valid
  five-field contract inside a terminal `json` fence after explanatory prose.
  The strict parser rejected the fence even though it already supported one
  trailing raw JSON object.
- Conversation `61bea580a3d546ecbd98434beca35a1f` had already started when the
  controller was interrupted. Its terminal output had the same shape and was
  reconciled from the durable event stream.

The fix accepts exactly one terminal fenced object only when its top-level
fields exactly match the worker contract. It labels the transport
`fenced-json-fallback`, so protocol compliance remains measurable rather than
silently treating the response as exact JSON. Failed attempt records now retain
the worker kind, conversation metadata, sanitized execution metadata, and a
SHA-256 plus length for the final response without persisting raw model text.

The hardened parser passed the full offline suite and both already-finished live
responses. A fresh matched run is the next live gate.
