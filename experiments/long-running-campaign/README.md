# Long-running controller campaign

This experiment qualifies the Git-backed OpenHands controller over an
eight-hour campaign instead of a single short batch.

## Test shape

- One OpenHands automation trigger per hour.
- One temporary controller conversation per trigger.
- One longer, tool-using research worker per controller tick.
- Eight attempts drawn from six Kaggle-shaped optimization tasks.
- A unique Git state branch and state directory.
- `keep_alive: false` so the automation service releases each completed
  controller sandbox.
- `RESEARCH_DEFER_SANDBOX_CLEANUP=false` so the controller explicitly pauses
  an isolated worker sandbox after every attempt. In a grouped controller and
  worker sandbox, leave the default enabled and let the automation service own
  cleanup of the shared sandbox.

The worker compares an exact baseline, a greedy heuristic, and a seeded search
across at least 12 deterministic trials. Independent application code still
validates the final candidate. This bound keeps the worker's terminal contract
inside the Enterprise app's searchable event history. The controller then keeps the work cell alive
until ten minutes have elapsed since conversation readiness. That controlled
dwell period tests long-lived controller state, timeouts, and runtime stability;
it is recorded separately and is not presented as research complexity.

## Durable state

The controller stores the campaign manifest, task decisions, attempt and
conversation identifiers, lifecycle events, validation results, lessons, and
reports under `.campaign-state/endurance-controller`. Each transition is
committed to `experiment/endurance-controller-state`.

Each worker also pushes its compact result contract to a unique
`experiment/worker-artifact/<attempt-id>` branch. The controller fetches and
validates that Git artifact. Conversation events remain useful for status and
diagnostics, but they are not the sole result channel because the Enterprise app
retains only a bounded searchable event history for very long conversations.

The automation is stateless. Every hourly run checks out that branch,
reconciles incomplete work, completes at most one attempt, checkpoints the
result, and exits.

## Safe rollout

1. Run the offline tests and controller tick.
2. Register the automation with its dormant January 1 schedule.
3. Dispatch one manual live canary.
4. Confirm deterministic validation, Git checkpointing, and zero active
   experiment sandboxes.
5. Enable the hourly schedule.
6. After the second successful tick, interrupt one controller after worker
   creation and verify the next tick reattaches without creating a duplicate.
7. Stop the schedule when eight attempts are recorded or any safety gate
   fails.

The automation timeout is 30 minutes and each worker has a 20-minute execution
timeout. This is a controller endurance test, not a claim that the simplified
optimization tasks reproduce the complete ONNX workload.
