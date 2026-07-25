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

## Stage 3 matched live result

Date: 2026-07-25

Comparison:

- ID: `graph-coloring-demo-comparison-20260725T205154Z-ba746980`
- Fixed budget: three OpenHands conversations per arm
- Same public repository, branch, model configuration, tasks, and timeouts
- Isolated stores prevented evidence leakage between arms

Result:

| Metric | Naive | Managed |
| --- | ---: | ---: |
| Problems solved | 3 | 3 |
| Coverage | 1.000 | 1.000 |
| Normalized solution quality | 1.000 | 1.000 |
| Quality AUC | 0.667 | 0.667 |
| Duplicate experiments | 0 | 0 |

All six candidates passed independent validation at the known target scores.
The naive arm retrieved no lessons. The managed arm retrieved one validated
lesson on its second task and two on its third task, proving the intended
cross-conversation memory path without a separate database.

Managed conversations:

- `da32d5a75f9f4637b6470a0c8804cd19`
- `524c6c7129594cbc812bcee1af6111c4`
- `b3c0af97f3af4d77aa85ad23b0a9d202`

Naive conversations:

- `ac9f02dfe633481c97f9022cfcebc14f`
- `13f4db27cc3e47a58635bffc36da7ebc`
- `5906755d68ea4883b9640ea0b3f2159e`

Conclusion:

- The production-shaped execution, validation, metadata, and memory paths work.
- This three-task benchmark is too easy for the configured model to distinguish
  managed quality from naive quality.
- The next stage should add a larger task set and harder instances where agents
  must choose among strategies, then repeat the matched comparison.

## Automatic sandbox pause

Date: 2026-07-25

The deployed OpenHands Enterprise 0.24.0 schema exposes supported V1 sandbox
lifecycle endpoints:

- `GET /api/v1/sandboxes?id=<sandbox-id>`
- `POST /api/v1/sandboxes/<sandbox-id>/pause`

The worker now requests a pause after capturing the terminal response, verifies
that the sandbox reaches `PAUSED`, and records both the request and result in the
append-only lifecycle journal. A pause failure is recorded without discarding a
valid experiment result. `--keep-sandbox` is an explicit debugging opt-out.

Before validation, eight finished research-lab sandboxes were still `RUNNING`.
All eight were verified terminal and paused through the supported API. Cluster
runtime pods dropped from nine to one, with zero unhealthy OpenHands pods.

One fresh end-to-end validation then confirmed:

- Run: `graph-coloring-demo-20260725T211735Z-a4632ed7`
- Conversation: `b34bc3d136be42e4b5bb50da29d39433`
- Sandbox: `7gGjgKvBw3ua1bYckzk1lU`
- Candidate: independently valid, score 3
- Lifecycle: `sandbox_pause_requested` followed by `sandbox_paused`
- Final sandbox status: `PAUSED`
- Cluster after completion: one running runtime pod, zero unhealthy pods

This closes the retained-sandbox capacity leak for research-lab initiated
conversations while preserving their OpenHands conversation history and local
evidence.

## Stage 3 final post-fix reference

Date: 2026-07-25

Three fresh matched comparisons were run after the task-bound identifier fix.
Each replicate used six public tasks per arm across graph coloring, set cover,
and bin packing. The arms used the same repository, branch, worker backend,
model configuration, timeouts, and six-attempt budget. Their stores were
isolated.

| Aggregate metric | Naive | Managed |
| --- | ---: | ---: |
| Attempts | 18 | 18 |
| Independently valid | 18/18 | 18/18 |
| Problems solved | 18/18 | 18/18 |
| Mean normalized solution quality | 1.000 | 1.000 |
| Mean quality AUC | 0.583 | 0.583 |
| Retrieved validated lessons | 0 | 9 |
| Duplicate experiments | 0 | 0 |

Operational result:

- 36/36 conversations produced independently valid candidates.
- 36/36 improving attempts were recorded.
- 36/36 sandboxes reached the verified `PAUSED` state.
- No invalid lesson was promoted.
- Final preflight: 0 active, 148 paused, 6 missing, launch gate open.
- Contract transport: 2 exact JSON, 21 fenced-JSON fallback, 13 trailing-JSON
  fallback.

Comparison IDs:

- `multi-family-live-pilot-comparison-20260725T220810Z-994beb58`
- `multi-family-live-pilot-comparison-20260725T222010Z-5d5ecc3e`
- `multi-family-live-pilot-comparison-20260725T223247Z-8a7fd212`

Conclusion:

The production-shaped orchestration path is reliable across repeated live
conversations, validated memory crosses conversation boundaries, and capacity
is released without deleting conversation history. The six-task live benchmark
does not separate organization quality because both arms reach every target.
The next live gate is a harder benchmark where retrieved techniques can alter
solution quality. Multi-controller work should introduce an application-owned
database behind `ResearchStore`, not manipulate OpenHands internal tables.
