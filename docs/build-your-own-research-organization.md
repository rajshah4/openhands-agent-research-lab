# Build a production-shaped agent research organization

This is the shortest path from the repository to a repeatable OpenHands
experiment. It preserves the parts that matter in production: fixed budgets,
isolated workers, deterministic validation, traceable conversations, earned
memory, capacity guards, and recoverable evidence.

## What you are building

```text
campaign registry
  -> external scheduler
  -> validated-memory retrieval
  -> one bounded OpenHands conversation
  -> strict result contract
  -> independent deterministic validator
  -> promote or reject
  -> immutable evidence ledger
```

OpenHands owns model execution, the sandbox, conversation history, and runtime
lifecycle. The research lab owns experiment selection, validation, memory
policy, measurement, and the audit ledger. Keeping that boundary explicit
avoids depending on OpenHands database internals.

## 1. Prove the control plane offline

The repository has no required Python dependencies for its core workflow.

```bash
git clone https://github.com/rajshah4/openhands-agent-research-lab.git
cd openhands-agent-research-lab

PYTHONPATH=src python3 -m unittest discover -s tests -v

PYTHONPATH=src python3 -m research_lab.cli compare \
  --campaign examples/multi-family-scale.json \
  --store .lab-scale \
  --worker local
```

The example exercises graph coloring, set cover, and bin packing. Both arms
receive the same tasks and attempt budget. Their stores are isolated so memory
cannot leak from one arm to the other.

The deterministic reference worker is not a model-quality claim. It verifies
that scheduling, retrieval, validation, promotion, metrics, and persistence
behave as designed before any live agent budget is spent.

## 2. Define a campaign

A campaign fixes the variables that would otherwise make a comparison
uninterpretable:

- task instances and known target scores
- repository and branch
- scheduler policy
- attempt budget
- model profile, when explicitly selected
- execution and concurrency limits

Use `examples/multi-family-live-pilot.json` as the smallest live template. Each
task is public, deterministic, and cheap to validate. To add another problem
family, implement its validator independently from the worker and register the
task type before adding prompts or scheduling heuristics.

## 3. Treat the worker output as an untrusted proposal

Each worker receives a self-contained prompt containing stable run, attempt,
task, repository, and retrieved-lesson identifiers. It must end with one
five-field contract:

```json
{
  "status": "done",
  "candidate": {},
  "lesson": null,
  "summary": ["Produced one candidate."],
  "next_gate": "validate"
}
```

The parser records whether the model returned exact JSON or required a bounded
compatibility fallback. Parsing never proves correctness. Only the
family-specific deterministic validator can accept the candidate, calculate
its score, and permit lesson promotion.

Examples in a prompt must use the actual task identifiers. A live pilot found
that placeholder identifiers such as `item-a` can be copied into otherwise
well-formed output; exact-ID examples removed that ambiguity.

## 4. Preflight OpenHands without creating a sandbox

Set credentials outside the repository:

```bash
export OPENHANDS_BASE_URL="https://app.your-openhands.example"
export OPENHANDS_API_KEY="..."

PYTHONPATH=src python3 -m research_lab.cli preflight \
  --campaign examples/multi-family-live-pilot.json \
  --worker openhands
```

Preflight confirms authentication, repository configuration, task count, and
visible sandbox capacity. It does not create a conversation.

For a small installation, keep the runtime limit explicit and conservative.
The Rajistics reference run used:

- runtime limit: 10
- launch lock: 7 active sandboxes
- new research concurrency: 1
- sandbox action after completion: pause and verify `PAUSED`

Pausing releases runtime capacity without deleting the OpenHands conversation
or the lab's evidence.

## 5. Run a matched live comparison

Live execution requires an explicit flag:

```bash
PYTHONPATH=src python3 -m research_lab.cli compare \
  --campaign examples/multi-family-live-pilot.json \
  --store .lab-live-seed-1 \
  --worker openhands \
  --live \
  --start-timeout 600 \
  --execution-timeout 1200 \
  --poll-seconds 5
```

Use a new store for every replicate. Run preflight between replicates and stop
if the capacity gate closes. Three post-fix replicates are the minimum used by
the reference example; harder benchmarks should use enough replicates to
estimate variance.

## 6. Inspect and publish safe evidence

Each comparison creates two isolated ledgers:

```text
.lab-live-seed-1/
  comparisons/<comparison-id>/
    comparison.json
    report.md
    arms/
      naive/
        runs/<run-id>/attempts/
        runs/<run-id>/lifecycle/
        lessons/validated/
      managed/
        runs/<run-id>/attempts/
        runs/<run-id>/lifecycle/
        lessons/validated/
```

Export a public-safe bundle:

```bash
PYTHONPATH=src python3 -m research_lab.evidence \
  --comparison .lab-live-seed-1/comparisons/<comparison-id>/comparison.json \
  --output evidence/seed-1.json
```

The exporter recursively removes credentials and secret-bearing fields. It
retains stable IDs, task outcomes, validator results, transport compliance,
retrieved lesson IDs, and verified pause state.

## 7. Know when files stop being enough

`FileResearchStore` is a production-shaped choice for one controller:

- immutable attempt records
- atomic writes
- append-only lifecycle events
- human-readable recovery and audit
- no dependency on OpenHands internal PostgreSQL tables

Move to an application-owned PostgreSQL store when two controllers can claim
work concurrently, multiple tenants need access control, operators need
cross-campaign queries, or retention volume makes file scans impractical. Keep
the same `ResearchStore` contract and add leases, uniqueness constraints,
idempotency keys, migrations, and tenant-scoped authorization.

Do not manipulate the OpenHands database. Its schema belongs to OpenHands and
is not the research application's persistence contract.

## 8. Production acceptance checklist

- Fixed tasks, model configuration, timeouts, and budget for both arms
- Independent deterministic validation for every task family
- Immutable attempt and lifecycle identifiers
- Failed attempts retained, not silently retried away
- Validated lessons only; invalid output never enters shared memory
- No raw credentials or environment dumps in evidence
- Capacity checked before every conversation launch
- Completed sandboxes paused and pause state verified
- Controller restart cannot erase completed evidence
- Public evidence exported through the sanitizer
- Quality claims separated from orchestration-reliability claims
- Database introduced only when concurrent ownership requires it

## Reference result

The final Rajistics run used OpenHands Enterprise 0.24.0 and three matched,
post-fix replicates. The public evidence directory records every sanitized
attempt and the aggregate result. On these six intentionally small live tasks,
both arms reached the target on every attempt. That proves the execution,
validation, memory, evidence, and lifecycle paths; it does not prove a managed
quality advantage.

The 12-task offline mechanism benchmark is more discriminating: normalized
solution quality was `0.670` for naive scheduling and `0.889` for the managed
organization. That establishes the expected direction under a controlled
worker. The next research gate is to repeat the live comparison on harder tasks
where retrieved techniques can change solution quality.
