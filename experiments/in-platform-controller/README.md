# In-platform controller experiment

This experiment moves the research-lab controller from an operator workstation
into the OpenHands Enterprise deployment. OpenHands then owns both the
controller's execution schedule and the worker conversations it coordinates.

See [`results-2026-07-26.md`](results-2026-07-26.md) for the live Replicated
results, compatibility findings, and production-readiness boundary.

The experiment compares two controller placements while keeping the campaign,
worker API, validator, Git ledger, model profile, capacity guard, and attempt
budget fixed.

## Arms

### A. Persistent supervisor sandbox

One first-class OpenHands conversation starts a bounded supervisor process. The
supervisor stays in one sandbox, reconciles state frequently, launches at most
one worker at a time, and writes every durable transition to the Git state
branch.

This arm measures the best-case latency and warm-runtime behavior of a
long-lived controller. It also exposes the operational risk of relying on one
sandbox and one long-running process.

### B. Scheduled polling automation

A supported repository-backed OpenHands prompt automation runs on a cron
schedule. Every run starts from a fresh checkout, invokes one deterministic
controller command, reconciles incomplete work, completes at most one new or
recovered attempt, checkpoints the evidence, and exits. The automation service
records each controller run and cleans up according to the deployment's
configured lifecycle policy.

This is the recommended production shape for Rajistics. It survives controller
sandbox loss because Git, not the sandbox filesystem, is authoritative.

## Why Git is the memory layer

The repository already has a single-controller, append-only file ledger.
Rather than depend on OpenHands internal PostgreSQL tables, this experiment
checkpoints that ledger to a dedicated Git branch after:

- run creation;
- task selection;
- start-task creation;
- conversation readiness and terminal reconciliation;
- final-response capture;
- validation and immutable attempt recording;
- lesson promotion; and
- report or controller-state updates.

The task-selection checkpoint is pushed before a worker conversation starts.
If two controllers race, only one can push that claim. The losing controller
stops before launching a duplicate worker.

## Fixed test configuration

- OpenHands Enterprise: `0.24.0`
- Replicated automation service: `1.1.5`
- Reported automation SDK: `1.33.0`
- Campaign: `examples/in-platform-controller-pilot.json`
- Attempt budget: 4
- New attempts per controller tick: 1
- Runtime capacity: 10
- Launch lock: 7 active sandboxes
- Worker startup timeout: 600 seconds
- Worker execution timeout: 1,200 seconds
- Worker sandboxes: pause and verify after final response
- State branch: `experiment/in-platform-controller-state`

The first live pass should use manual dispatches so every run can be inspected.
After that passes, enable the hourly cron schedule.

The registration helper intentionally creates the automation with a dormant
January 1 schedule. This prevents an unattended run between registration and
the first manual inspection. After the manual failure and recovery tests pass,
`automation/enable-hourly.sh` changes it to `0 * * * *` in
`America/Chicago`.

Rajistics currently retains automation sandboxes for runtime-inactivity
cleanup. The request still sets `keep_alive: false`; the live evidence must
record the value the service actually stores and the time until the controller
sandbox is paused or reaped. That site-specific retention policy is part of the
resource comparison, not something this experiment should hide by editing
OpenHands database tables.

## Measurements

Record for each arm:

- controller-to-worker launch latency;
- task completion wall time;
- duplicate start tasks and conversations;
- missed or stale work;
- recovery after deliberately interrupting the controller;
- Git commits per attempt and push conflicts;
- active and queued sandboxes over time;
- controller and worker sandbox-hours;
- model cost and tokens;
- number of operator interventions;
- whether the final ledger explains every state transition; and
- whether all completed worker sandboxes return to `PAUSED`.

## Acceptance criteria

The polling arm passes when:

1. Four scheduled ticks finish one campaign without duplicate attempt
   sequences or duplicate conversations.
2. A controller interruption after `start_task_created` is recovered by the
   next tick without creating another conversation.
3. A deliberately concurrent second controller loses the Git claim and exits
   before worker launch.
4. All candidates remain subject to independent deterministic validation.
5. The state branch contains enough information to resume from a fresh
   sandbox.
6. The cluster never crosses the launch lock and returns to its pre-test active
   sandbox count.

## Automation package

`automation/prompt.txt` and `automation/register-preset.sh` use the supported
prompt-preset endpoint. OpenHands supplies the repository checkout, Git
authentication, stored secrets, SDK workspace, completion callback, and
sandbox cleanup. The prompt only invokes
`automation/preset_tick.py`; it does not make controller decisions.
It explicitly refreshes `origin/main` first because a reused Enterprise
sandbox can retain an older repository checkout.

`automation/preset_tick.py`:

1. checks out the dedicated state branch, or creates it from `main`, and
   merges the current `origin/main` controller code before resuming;
2. verifies that OpenHands injected the worker API credential explicitly
   referenced by the terminal command;
3. runs `run_tick.py` with worker-level sandbox cleanup deferred; and
4. returns the tick's exit status to the OpenHands automation lifecycle.

The deferred cleanup is required when Enterprise places the worker
conversation in the automation controller's sandbox. Pausing the "worker"
sandbox from inside the tick would pause the controller before it could record
validation. With `keep_alive: false`, the automation service is the single
owner that cleans up the shared sandbox after the tick exits and its callback
completes.

The branch preparation also unshallows the Enterprise repository checkout
before merging `origin/main`. Without that step, a valid state branch created
by an earlier run can appear to have unrelated history and Git exits before
the controller starts.

The controller's scheduler still makes domain decisions, and OpenHands workers
still use the configured model. The automation wrapper consumes a small amount
of model work to invoke the audited command; the research decisions remain in
deterministic code.

### Replicated 0.24.0 custom-tarball gap

The first live implementation used the lower-level custom tarball endpoint in
`automation/main.py`. Three bounded diagnostic runs established that:

- the service stored `keep_alive: false`;
- the custom sandbox received a working agent-server session key and runtime
  URL;
- its agent-server secret store was empty, so it could not retrieve
  `GITHUB_TOKEN` or `OPENHANDS_API_KEY`; and
- the documented direct callback credential returned HTTP 401.

Those runs were canceled and their sandboxes were cleaned up. The raw custom
path remains in the repo as reproducible evidence, but it is not the
recommended controller path on this Replicated build. The prompt preset binds
the run to the creating user and uses the generated SDK workspace lifecycle,
which is the current supported route for Git, secret, and callback handling.

The first prompt-preset run exposed a second Replicated version-alignment gap:
the automation service advertised SDK `1.33.0`, while the installed agent
server emitted the `1.36` event contract. SDK `1.33.0` rejected the
`extended_content` field before the controller command ran. The contained
`automation/patch-preset-sdk.sh` helper preserves the user-bound generated
preset but replaces only its setup script with `automation/setup-compat.sh`,
which pins the SDK packages to `1.36.0`. This is an experiment-local
compatibility overlay, not a database edit or an installation-wide patch.
