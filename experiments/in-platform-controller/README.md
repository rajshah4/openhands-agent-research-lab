# In-platform controller experiment

This experiment moves the research-lab controller from an operator workstation
into the OpenHands Enterprise deployment. OpenHands then owns both the
controller's execution schedule and the worker conversations it coordinates.

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

A custom OpenHands automation runs on a cron schedule. Every run starts from a
fresh checkout of the Git state branch, reconciles incomplete work, completes
at most one new or recovered attempt, checkpoints the evidence, and exits. The
automation service records each controller run and cleans up according to the
deployment's configured lifecycle policy.

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

`automation/main.py` is a deterministic custom automation. It does not use an
LLM for controller decisions. It:

1. fetches the stored OpenHands and GitHub credentials through the agent
   server;
2. clones the dedicated state branch, or creates it from `main`;
3. runs `run_tick.py`;
4. reports completion through the automation callback on every exit path.

The controller's scheduler still makes domain decisions, and OpenHands workers
still use the configured model. The hourly health/reconciliation loop itself
does not consume model tokens.
