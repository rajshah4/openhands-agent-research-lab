# Controller deployment patterns

The controller is the part that decides what work should run next, checks
capacity, starts agents, validates their outputs, records the result, and
recovers incomplete work. It is separate from the agent that solves an
individual task.

This repository supports three useful placements. They share the same campaign,
worker contract, validators, and experiment ledger. They differ in who operates
the controller and how much isolation each worker receives.

## Recommendation

| Pattern | Put the controller here | Use it when |
| --- | --- | --- |
| OpenHands Enterprise | A prompt automation or a small service using the supported V1 API | Conversation history, access control, sandbox lifecycle, and operator visibility matter |
| Agent Canvas | A Kubernetes Deployment or CronJob beside the Canvas service | One trusted team accepts a shared process, filesystem, volume, and credentials |
| Native subagents | Keep the durable controller outside the parent; let one parent delegate a bounded group of subtasks | Two to four trusted specialists can share one workspace and one parent lifecycle |

For a large campaign, use a hybrid. The durable controller owns top-level work
items. Each top-level item becomes an Enterprise conversation or Canvas
conversation. That work-cell owner may use a small number of native subagents
for read-only exploration, testing, or synthesis.

Do not put a hundred subagents under one parent. It concentrates context,
workspace state, retries, and failure handling in one conversation.

## Common controller contract

Every placement should implement the same loop:

```text
acquire one controller lease
  -> read campaign state
  -> reconcile incomplete attempts
  -> check execution capacity
  -> claim bounded work
  -> start first-class work cells
  -> wait for durable terminal output
  -> validate independently
  -> record attempt and lifecycle evidence
  -> release capacity
  -> checkpoint state
```

The controller must have one durable source of truth. In this reference:

- one controller uses `FileResearchStore`;
- Git checkpoints make scheduled Enterprise ticks restartable and auditable;
- an application-owned database is required when multiple controllers can
  claim work concurrently;
- OpenHands internal database tables are never the application contract.

## 1. Enterprise controller

The tested in-platform implementation uses a repository-backed OpenHands prompt
automation. The automation runs one deterministic controller tick, stores
sanitized campaign state on a dedicated Git branch, creates workers through the
supported V1 conversation API, and exits. `keep_alive: false` lets the
automation service release the controller sandbox.

The complete example is in
[`experiments/in-platform-controller`](../experiments/in-platform-controller/README.md).
The main files are:

- `automation/register-preset.sh`: register a dormant scheduled automation;
- `automation/preset_tick.py`: refresh code and the state branch;
- `run_tick.py`: reconcile state and run one bounded attempt;
- `automation/setup-compat.sh`: version-pinned SDK compatibility for the tested
  Replicated installation.
- `automation/register-load-preset.sh`: register a dormant two-worker
  in-platform load cell whose outer automation owns cleanup.

Registering the example does not enable an hourly production schedule:

```bash
export OPENHANDS_HOST="https://app.your-openhands.example"
export OPENHANDS_API_KEY="..."

./experiments/in-platform-controller/automation/register-preset.sh
```

Production rules:

- use `concurrencyPolicy: Forbid` or an equivalent single-owner lease;
- checkpoint before advancing to another work item;
- retry only failures known to be safe to retry;
- do not retry an ambiguous conversation-create timeout, because the first
  request may have created a worker;
- check the existing start-task ID before creating a replacement;
- if controller and workers share a sandbox, the outer automation owns cleanup;
- pace V1 reads and record retry counts;
- queue work above the tested sandbox and API limits.

On the tested Replicated build, an external controller passed with four active
children in one grouped sandbox. The in-platform prompt automation passed with
two active children; its four-active diagnostic produced only 3/4 independently
verifiable contracts even though the automation status was `COMPLETED`. Start
in-platform cells at two and queue the remainder.

Use one sandbox per conversation for different tenants, untrusted code, or
separate credentials. Use bounded sandbox grouping for trusted work cells when
runtime density matters. Grouping keeps separate conversation histories, but
it does not create a security or failure boundary.

## 2. Agent Canvas controller

Agent Canvas does not require Enterprise. The same controller can run as a
small Kubernetes workload beside Canvas and call its supported API.

A simple scheduled tick looks like this:

```bash
PYTHONPATH=src python3 -m research_lab.cli run \
  --campaign examples/hard-transfer-live.json \
  --store /state/research-lab \
  --worker canvas \
  --base-url http://agent-canvas:8000 \
  --canvas-remote-workspace \
  --canvas-workspace-root /home/openhands/workspace/research-lab \
  --resume-run "$RUN_ID" \
  --max-new-attempts 1 \
  --live
```

Omit `--resume-run` on the first tick. Persist the returned run ID with the
controller state and pass it on later ticks. The tested example ran two
separate processes this way and resumed the same run.

Mount `/state` on durable storage or replace the file store with an
application-owned database. Keep only one CronJob or Deployment replica while
using the file store. Store the Canvas API key in a Kubernetes Secret, not in
the repository or campaign ledger.

The tested GKE controller assigned six distinct tasks before launch. Across
three matched replicates, managed scheduling covered all six tasks while six
independent controllers repeatedly chose one task. Managed scheduling reduced
mean wall time by 22.9% and mean model cost by 23.8%.

Those tests ran the controller outside the Canvas pod. Deploying the same
controller command as a Kubernetes CronJob beside Canvas is implemented in
[`experiments/agent-canvas-kubernetes/controller`](../experiments/agent-canvas-kubernetes/controller/README.md).
The checked-in CronJob is suspended by default, runs one attempt per tick,
prevents overlapping controller jobs, and keeps its single-writer ledger on a
dedicated PVC.

The in-cluster controller completed six separate ticks against one durable
campaign: 6/6 valid attempts, six tasks covered, no duplicate candidates, and
no Agent Canvas restarts. The campaign used 140,228 prompt tokens, 15,423
completion tokens, $0.1748943 of model cost, and 509.953 seconds from the first
attempt start to the last finish.

A zero-grace controller termination was also recovered. The replacement
attached to the persisted Canvas conversation, recorded
`recovered_after_controller_restart: true`, and did not create another
conversation. In a separate overlap test, one of two simultaneous controllers
acquired the file ledger and the other was rejected before it could launch a
worker. Full evidence is in
[`results-2026-07-27.md`](../experiments/agent-canvas-kubernetes/controller/results-2026-07-27.md).

Canvas is efficient because conversations share one Agent Server pod and
volume. That is also its trust boundary. Use it for one trusted team, not as a
replacement for Enterprise tenancy or isolated execution.

## 3. Native subagent controller

Native subagents are an execution detail inside one work cell, not a durable
campaign controller. The parent conversation decides which child specialists
to call and aggregates their results. The top-level controller still owns
campaign scheduling, task claims, validation, retry, and long-term state.

The measured Agent Canvas example is in
[`experiments/agent-canvas-tasktool`](../experiments/agent-canvas-tasktool/results-2026-07-26.md).
Four parallel native children completed strict visible contracts in 333.9
seconds, compared with 501.4 seconds for sequential native children and 374.4
seconds for four first-class Canvas conversations in that replicate.

Choose native subagents when:

- the specialists are trusted;
- the tasks can safely share a workspace and credentials;
- one parent history is easier to operate than several histories;
- child-level human handoff and independent service levels are unnecessary.

Choose first-class conversations when each worker needs independent ownership,
retry, permissions, history, or operator handoff.

The tested Replicated profile persisted the “enable sub-agents” setting but did
not advertise the task tool in newly launched conversations. Do not recommend
native Enterprise delegation for that installed version until the profile
exposes the capability and the same acceptance tests pass.

## Acceptance test before customer use

Run these gates after every platform, image, model, or controller change:

1. Offline: run the full campaign-shaped ledger and verify every record parses,
   IDs and sequences are unique, and restart resumes the same run.
2. Live single worker: verify output contract, deterministic validation,
   lifecycle evidence, and cleanup.
3. Live bounded concurrency: increase through 1, 2, and 4 workers; stop on
   errors, restarts, latency growth, or capacity pressure.
4. Failure injection: interrupt the controller after worker creation and prove
   restart reattaches rather than creating a duplicate.
5. Terminal-output recovery: test a conversation with more than one event page
   and verify the final durable message is still retrieved.
6. Cleanup: require zero active experiment sandboxes and no pause errors.
7. Evidence: publish sanitized results, including failures and retries.

Passing the execution tests does not prove competition performance. A full
NeuroGolf run still needs the real ONNX workloads, adversarial validators,
artifact quarantine, and a submission gate.
