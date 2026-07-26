# OpenHands Agent Research Lab

A production-shaped reference implementation for coordinating OpenHands agents
across repeated, measurable experiments.

The project is inspired by the organizational dynamics of NeuroGolf: a bounded
pool of workers explores candidates, deterministic validators decide what
improved, and only evidence-backed lessons become memory for future attempts.
It does not depend on Kaggle competition solutions or disputed solution dumps.

## What the current stages prove

- OpenHands conversations are first-class, isolated worker attempts.
- The application owns scheduling, deterministic validation, and promotion.
- Every worker returns a strict machine-readable contract.
- Execution metadata and immutable identifiers are preserved with each attempt.
- Storage is replaceable. The included filesystem store is a restartable,
  single-controller pilot backend; distributed production stores implement the
  same interface.
- The entire vertical slice can be tested offline before spending agent budget.
- Naive and managed organizations can be compared with isolated stores and the
  same tasks, worker, model configuration, and attempt budget.

## Architecture

```text
Campaign
  -> scheduler selects one task and relevant validated lessons
  -> worker backend runs one bounded attempt
       -> local deterministic worker (offline development)
       -> Agent Canvas shared backend (trusted single-tenant execution)
       -> OpenHands V1 conversation (Enterprise/Cloud)
  -> deterministic validator scores the candidate
  -> storage records the immutable attempt
  -> improved, valid attempts may promote a lesson
```

OpenHands is the execution plane. This project is the research coordination and
learning plane.

## Quickstart

Run the offline vertical slice without installing dependencies:

```bash
PYTHONPATH=src python3 -m research_lab.cli run \
  --campaign examples/graph-coloring-campaign.json \
  --store .lab \
  --worker local
```

Inspect the generated report:

```bash
cat .lab/runs/*/report.md
```

Run the offline test suite:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Run the matched offline comparison:

```bash
PYTHONPATH=src python3 -m research_lab.cli compare \
  --campaign examples/graph-coloring-campaign.json \
  --store .lab-comparison \
  --worker local
```

Validate configuration for a live OpenHands run without creating a sandbox:

```bash
export OPENHANDS_BASE_URL="https://app.your-openhands.example"
export OPENHANDS_API_KEY="..."
PYTHONPATH=src python3 -m research_lab.cli preflight \
  --campaign examples/graph-coloring-campaign.json \
  --worker openhands
```

When preflight passes, a live run requires an explicit flag:

```bash
PYTHONPATH=src python3 -m research_lab.cli run \
  --campaign examples/graph-coloring-campaign.json \
  --store .lab \
  --worker openhands \
  --live
```

Live execution creates real OpenHands conversations and may incur model and
infrastructure cost. The CLI will not create conversations without `--live`.
After each final response, the controller pauses the sandbox through the
supported V1 API and verifies it reached `PAUSED`. Use `--keep-sandbox` only
when a bounded debugging session intentionally needs the runtime to remain
available.

## Agent Canvas comparison backend

Agent Canvas provides a shared, persistent execution backend without creating
one Enterprise sandbox per attempt. It uses a different supported protocol from
Enterprise, so the research lab provides a separate `CanvasClient` and
`CanvasWorker` behind the same worker contract.

Preflight an existing local Canvas backend without making a model call:

```bash
export CANVAS_API_KEY="..."
PYTHONPATH=src python3 -m research_lab.cli preflight \
  --campaign examples/graph-coloring-campaign.json \
  --worker canvas \
  --base-url http://127.0.0.1:8000
```

After preflight confirms the backend is healthy, ready, and has model access:

```bash
PYTHONPATH=src python3 -m research_lab.cli run \
  --campaign examples/graph-coloring-campaign.json \
  --store .lab-canvas \
  --worker canvas \
  --base-url http://127.0.0.1:8000 \
  --canvas-workspace-root .lab-canvas-workspaces \
  --live
```

Canvas attempts receive distinct workspace directories, but they share the
backend process and host trust boundary. The parent remains the only writer to
the experiment ledger, and deterministic validation is unchanged.

## Storage boundary

`FileResearchStore` is intentionally limited to a single controller. It writes
immutable attempt documents atomically and keeps validated lessons separate
from proposed claims. It locks controller ownership, resumes an existing run,
reconciles incomplete attempts, and can reattach to a persisted OpenHands start
task after a restart. A second controller is rejected rather than allowed to
race.

A production PostgreSQL implementation can replace it without changing:

- worker prompts or contracts
- OpenHands lifecycle handling
- schedulers
- validators
- reports

The project never writes to OpenHands internal database tables.

## Current status

Stage 1 is an offline-tested vertical slice. Stage 2 has also passed against the
Rajistics OpenHands Enterprise 0.24.0 Replicated deployment, including
cross-conversation retrieval of a validated lesson. Two intermediate failed
attempts were retained and led to hardened contract-envelope and final-event
indexing behavior. Stage 3 adds the matched naive-versus-managed harness and a
deterministic offline result: managed memory improves normalized solution quality
from 0.889 to 1.000 under the same four-attempt budget. Duplicate work remains
tied, identifying experiment diversification as the next scheduler improvement.
The first matched live Rajistics pilot also completed: both arms solved all
three tasks optimally, while only the managed arm retrieved validated lessons.
That tie shows the execution and memory architecture works but the bundled
three-task benchmark is not yet discriminating enough for a production claim.

The hardened scale path now covers the shape of a full NeuroGolf campaign:
400 task owners, 4,800 attempts per arm, and exactly 12 attempts per task.
A fresh 4,800-attempt file-ledger run completed in 8.44 seconds with
24,013 parseable records in 94 MB. A live failure-injection test killed the
controller after Replicated created the start task; restart reattached to the
same conversation, completed one attempt, and paused the sandbox. These are
orchestration and recovery results, not ONNX or Kaggle performance.

See [the design](docs/design.md), [the framing record](FRAMING.md), and the
[live validation log](docs/live-validation.md). The metric definitions and
comparison limits are in [the matched-comparison note](docs/matched-comparison.md).

For production multi-agent deployment on OpenHands Enterprise/Replicated, see
the [three-pattern result](evidence/2026-07-25-replicated-multi-agent-patterns/README.md),
the [12-task scale study](evidence/2026-07-25-replicated-scale-study/README.md),
the [full 400-task capacity plan](docs/neurogolf-full-competition-capacity-plan.md),
and the [operator runbook](docs/replicated-multi-agent-operations.md).
The [controller deployment guide](docs/controller-deployment-patterns.md)
shows how the same control loop fits Enterprise automations, Agent Canvas on
Kubernetes, and bounded native subagents.
The [controller load report](experiments/controller-load/results-2026-07-26.md)
records the 4,800-attempt ledger test, the Enterprise failure and recovery
sequence, the final 6/6 four-active external-controller load, the accepted
two-child in-platform automation cell, and the two-tick Canvas resume test.
The [Kaggle parity review](docs/kaggle-neurogolf-parity-review.md) separates
what is now proven from the ONNX workload, adversarial validation, artifact
quarantine, and submission gate still required. The
[multi-agent demo update plan](docs/multi-agent-demo-sandbox-update-plan.md)
shows how to add sandbox placement and container-efficiency guidance to the
companion demo.
