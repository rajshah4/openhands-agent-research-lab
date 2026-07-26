# Operating multi-agent workloads on OpenHands Enterprise/Replicated

This runbook reproduces the three deployment patterns evaluated by this
repository without querying or modifying OpenHands' internal database. It uses
the supported V1 application API for conversations, user settings, sandbox
discovery, and sandbox pause.

The tested installation was OpenHands Enterprise `0.24.0`, deployed with
Replicated. The OpenHands app reported server `1.46.2` and agent-server
`1.36.0-python`. Recheck commands and API behavior after an upgrade.

## Choose a pattern

| Pattern | User setting | Batch controls | Best fit |
| --- | --- | --- | --- |
| Isolated | `NO_GROUPING` | six tasks, four dispatched | Untrusted code, tenants, or strongest failure isolation |
| Bounded shared | `FEWEST_CONVERSATIONS` | six tasks, four dispatched | Trusted agent teams; recommended starting point |
| Throughput shared | `FEWEST_CONVERSATIONS` | six tasks, six dispatched | Trusted, short, independent work after load testing |

`GROUP_BY_NEWEST`, `LEAST_RECENTLY_USED`, and `ADD_TO_ANY` are alternative
placement selectors. They do not create a different isolation boundary, so the
matched benchmark uses `FEWEST_CONVERSATIONS` for both shared patterns and
changes the controller's dispatch limit.

## Prerequisites

Run commands from the repository root. Keep the Enterprise API key in an env
file outside the repository. The scripts read named assignments from the file;
they do not print the key or require shell-sourcing it.

```bash
export RESEARCH_ENV_FILE=/path/to/install_replicate/.env
export REPLICATED_HOST=ubuntu@your-replicated-host
export REPLICATED_SSH_KEY=/path/to/replicated.pem
```

Install the project and run the non-mutating preflight:

```bash
make init

PYTHONPATH=src .venv/bin/python -m research_lab.cli preflight \
  --campaign examples/hard-transfer-live.json \
  --worker openhands \
  --base-url https://app.replicated.rajistics.com \
  --env-file "$RESEARCH_ENV_FILE" \
  --runtime-capacity 10 \
  --launch-lock-at 7
```

Do not begin a batch unless the authenticated user's active sandbox count is
below seven. The benchmark runner repeats this capacity gate before launching.

## Verify the Enterprise per-sandbox cap

The tested installation allows at most six conversations in one sandbox. Read
the deployed value before a shared six-task run:

```bash
ssh -i "$REPLICATED_SSH_KEY" "$REPLICATED_HOST" \
  'sudo /var/lib/embedded-cluster/bin/kubectl get deployment openhands \
  -n openhands -o jsonpath="{.spec.template.spec.containers[0].env[?(@.name==\"OH_APP_CONVERSATION_MAX_NUM_CONVERSATIONS_PER_SANDBOX\")].value}{\"\n\"}"'
```

Expected output for this experiment is `6`. Changing this deployment value is
an installation operation and is outside the experiment runner.

## Safely change the grouping strategy

Drain and pause experiment sandboxes before changing placement. The helper
refuses to mutate settings when the API still reports an active sandbox.

Use isolated placement:

```bash
PYTHONPATH=src .venv/bin/python \
  experiments/enterprise-sandbox-grouping/scripts/set-grouping-strategy.py \
  --strategy NO_GROUPING \
  --env-file "$RESEARCH_ENV_FILE" \
  --live
```

Use least-busy shared placement:

```bash
PYTHONPATH=src .venv/bin/python \
  experiments/enterprise-sandbox-grouping/scripts/set-grouping-strategy.py \
  --strategy FEWEST_CONVERSATIONS \
  --env-file "$RESEARCH_ENV_FILE" \
  --live
```

Both commands use `POST /api/v1/settings`, verify the result through
`GET /api/v1/users/me`, and print only safe before/after state.

## Run the matched patterns

Use a new store path for every replicate. The examples use the same campaign,
model, six-task budget, timeout, and API pacing. The runner seeds the first
conversation, records every conversation and sandbox ID, independently
validates outputs, and returns a failure if the valid-task, sandbox-count, or
cleanup contract is not met. Isolated workers pause their own sandboxes as they
finish. The controller pauses a grouped sandbox once after the batch drains.

For tasks whose complete input is in the prompt, add `--no-repository` to every
arm to remove Git-provider availability and checkout time from the scheduling
comparison. Do not mix repository-mounted and prompt-only arms in one matched
result. For coding workloads, omit this flag and first verify the repository is
selectable from the Enterprise UI.

### 1. Isolated sandboxes, four active and two queued

First set `NO_GROUPING`, then run:

```bash
PYTHONPATH=src .venv/bin/python \
  experiments/enterprise-sandbox-grouping/scripts/run-concurrent.py \
  --campaign examples/hard-transfer-live.json \
  --store .lab-replicated-patterns/isolated/isolated-haiku-r1 \
  --env-file "$RESEARCH_ENV_FILE" \
  --no-repository \
  --model litellm_proxy/us.anthropic.claude-haiku-4-5-20251001-v1:0 \
  --request-interval 0.75 \
  --poll-seconds 2 \
  --concurrency 6 \
  --dispatch-limit 4 \
  --expected-sandboxes 6 \
  --require-grouping-strategy NO_GROUPING \
  --execution-timeout 600 \
  --live
```

### 2. One shared sandbox, four active and two queued

Set `FEWEST_CONVERSATIONS`, then run:

```bash
PYTHONPATH=src .venv/bin/python \
  experiments/enterprise-sandbox-grouping/scripts/run-concurrent.py \
  --campaign examples/hard-transfer-live.json \
  --store .lab-replicated-patterns/grouped-four/grouped-four-haiku-r1 \
  --env-file "$RESEARCH_ENV_FILE" \
  --no-repository \
  --model litellm_proxy/us.anthropic.claude-haiku-4-5-20251001-v1:0 \
  --request-interval 0.75 \
  --poll-seconds 2 \
  --concurrency 6 \
  --dispatch-limit 4 \
  --expected-sandboxes 1 \
  --require-grouping-strategy FEWEST_CONVERSATIONS \
  --execution-timeout 600 \
  --live
```

### 3. One shared sandbox, six active

Keep `FEWEST_CONVERSATIONS`, then run:

```bash
PYTHONPATH=src .venv/bin/python \
  experiments/enterprise-sandbox-grouping/scripts/run-concurrent.py \
  --campaign examples/hard-transfer-live.json \
  --store .lab-replicated-patterns/grouped-six/grouped-six-haiku-r1 \
  --env-file "$RESEARCH_ENV_FILE" \
  --no-repository \
  --model litellm_proxy/us.anthropic.claude-haiku-4-5-20251001-v1:0 \
  --request-interval 0.75 \
  --poll-seconds 2 \
  --concurrency 6 \
  --dispatch-limit 6 \
  --expected-sandboxes 1 \
  --require-grouping-strategy FEWEST_CONVERSATIONS \
  --execution-timeout 600 \
  --live
```

The shared request interval of `0.75` seconds is deliberate. A faster pilot
encountered the installation's observed `100 requests/minute` application API
limit and was excluded as a protocol failure.

On the tested small installation, a six-active isolated stress run also
overloaded the application control path: repeated read timeouts and transient
authentication errors left `0/6` valid attempts even though the runtime pods
did not restart. Keep the isolated default at four or lower, and let each
isolated worker pause its own sandbox immediately after completion. The runner
does this automatically under `NO_GROUPING`.

## Watch cluster health during a batch

Count live runtime pods and check restarts:

```bash
ssh -i "$REPLICATED_SSH_KEY" "$REPLICATED_HOST" \
  'sudo /var/lib/embedded-cluster/bin/kubectl get pods -n openhands \
  -o custom-columns=NAME:.metadata.name,READY:.status.containerStatuses[0].ready,RESTARTS:.status.containerStatuses[0].restartCount,STATUS:.status.phase \
  | grep "^runtime-"'
```

Sample runtime CPU and memory:

```bash
ssh -i "$REPLICATED_SSH_KEY" "$REPLICATED_HOST" \
  'sudo /var/lib/embedded-cluster/bin/kubectl top pods -n openhands \
  | grep "^runtime-"'
```

On the tested 10-runtime installation, stop launching new isolated work if the
capacity gate closes, runtimes restart, or the node becomes resource
constrained. One warm runtime may exist in addition to experiment runtimes.

## Verify cleanup and restore the recommended setting

After every batch, rerun preflight and require zero active user-visible
sandboxes. The batch summary must have an empty `pause_errors` object and one
`PAUSED` entry in `pause_results` for every ID in `sandbox_ids`.

```bash
PYTHONPATH=src .venv/bin/python -m research_lab.cli preflight \
  --campaign examples/hard-transfer-live.json \
  --worker openhands \
  --base-url https://app.replicated.rajistics.com \
  --env-file "$RESEARCH_ENV_FILE" \
  --runtime-capacity 10 \
  --launch-lock-at 7
```

Restore `FEWEST_CONVERSATIONS` after isolated testing with the safe settings
command above. This is the recommended default for trusted multi-agent pools;
the controller—not an individual worker—must own the grouped sandbox lifecycle
and pause it only after all leases have been released.

If a controller is interrupted after creating sandboxes, copy the recorded IDs
from its `summary.json` and use the recovery helper. It retries transient API
errors, spaces pause requests, and verifies each final state:

```bash
PYTHONPATH=src .venv/bin/python \
  experiments/enterprise-sandbox-grouping/scripts/pause-sandboxes.py \
  SANDBOX_ID_1 SANDBOX_ID_2 \
  --env-file "$RESEARCH_ENV_FILE" \
  --live
```

## Production boundaries

- Keep first-class Enterprise conversations even when compute is shared.
- Use one controller as the lifecycle owner for each sandbox pool.
- Enforce a per-sandbox dispatch limit and queue excess work.
- Recycle shared sandboxes by job count, age, memory, or failure signal.
- Do not mix tenants or untrusted work in one runtime.
- Store experiment state and sanitized evidence outside the OpenHands database.
- Treat Git as the release and audit layer, not as a runtime lock manager.
- Re-run this load test after changing images, models, limits, or versions.
