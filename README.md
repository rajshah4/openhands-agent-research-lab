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
- Storage is replaceable. The included filesystem store is a single-writer
  development backend; production stores implement the same interface.
- The entire vertical slice can be tested offline before spending agent budget.
- Naive and managed organizations can be compared with isolated stores and the
  same tasks, worker, model configuration, and attempt budget.

## Architecture

```text
Campaign
  -> scheduler selects one task and relevant validated lessons
  -> worker backend runs one bounded attempt
       -> local deterministic worker (offline development)
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

## Storage boundary

`FileResearchStore` is intentionally limited to a single controller. It writes
immutable attempt documents atomically and keeps validated lessons separate
from proposed claims.

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

See [the design](docs/design.md), [the framing record](FRAMING.md), and the
[live validation log](docs/live-validation.md). The metric definitions and
comparison limits are in [the matched-comparison note](docs/matched-comparison.md).
