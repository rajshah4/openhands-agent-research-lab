# OpenHands Agent Research Lab Design

## 1. Introduction

### 1.1 Problem Statement

Multi-agent orchestration examples show how work moves between agents, but
production research organizations also need to choose experiments, preserve
evidence, validate candidates independently, avoid duplicated work, and reuse
only findings that have earned trust.

### 1.2 Proposed Solution

Provide a small application that coordinates bounded OpenHands conversations as
experimental workers. An external scheduler selects tasks, a deterministic
validator measures each candidate, and a storage interface records attempts and
validated lessons. OpenHands supplies isolated execution, lifecycle metadata,
events, model configuration, and human-visible audit trails.

Stage 1 uses a single-writer filesystem store so the entire workflow is
inspectable and testable offline. The storage boundary is designed for a later
PostgreSQL implementation without changing domain behavior.

## 2. New Concepts

### Campaign

A fixed set of tasks, scheduler policy, model profile, repository, and attempt
budget.

### Attempt

One bounded worker execution on one task. Its result is immutable after
validation.

### Candidate

The structured solution returned by a worker. Candidates are content-hashed so
duplicates can be measured.

### Lesson

A proposed reusable statement with tags and evidence. A lesson becomes
retrievable memory only when associated with a valid, improving attempt.

### Storage implementation

A replaceable mechanism for recording attempts and validated lessons. The file
store is single-writer; a database store will provide atomic claims and
multi-controller concurrency.

## 3. Technical Design

### 3.1 Component boundaries

```text
CLI
  -> CampaignRunner
       -> SchedulerPolicy
       -> ResearchStore
       -> WorkerBackend
            -> LocalHeuristicWorker
            -> OpenHandsWorker
                 -> OpenHands V1 Client
       -> BenchmarkValidator
       -> ReportBuilder
```

### 3.2 Worker contract

Workers must finish with one JSON object:

```json
{
  "status": "done",
  "candidate": {"assignments": {"0": 0}},
  "lesson": {
    "statement": "Color high-degree vertices first.",
    "tags": ["graph-coloring"],
    "evidence": "Produced a valid candidate."
  },
  "summary": ["Generated one candidate."],
  "next_gate": "validate"
}
```

Missing fields, unknown enumerations, conflicting shapes, or absent JSON output
are contract failures. The preferred transport is exactly one JSON object. For
model compatibility, the parser may accept one structurally valid contract only
when it is the unique trailing JSON object; that attempt is marked
`transport_compliant: false`. A contract is not a validation result.

### 3.3 OpenHands lifecycle

1. Build a self-contained prompt with task, repository, branch, run ID, attempt
   ID, retrieved lesson IDs, limits, and final contract.
2. Create an app conversation through the V1 endpoint.
3. Poll the returned start task to `READY`.
4. Persist start-task, sandbox, and app-conversation IDs.
5. Poll the app-conversation record with a bounded execution timeout.
6. If list state becomes incomplete, inspect durable events for terminal state.
7. Allow bounded grace for the final response to appear in the event index.
8. Parse the strict contract and pass the candidate to the deterministic
   validator.

Live execution requires an explicit CLI flag.

### 3.4 Storage layout

```text
.lab/
  runs/<run-id>/
    manifest.json
    attempts/<attempt-id>.json
    lifecycle/<attempt-id>/<event-id>.json
    report.md
  lessons/validated/<lesson-id>.json
```

Attempt records are immutable. An append-only lifecycle journal records
selection, start-task creation, conversation readiness, terminal state, and
final-response availability so a partial live run remains recoverable. Writes
use a temporary file and atomic replace. The controller is the only writer.

### 3.5 Metadata and redaction

Persist stable identifiers, timestamps, statuses, repository, branch, event
counts, model name, and cost/token fields when exposed. Remove API keys, session
keys, authorization headers, credentials, and environment values recursively.
Do not store complete event payloads by default.

### 3.6 Scheduling

Stage 1 includes:

- `round_robin`: chooses the task with the fewest attempts, then task ID.
- `managed`: prioritizes unattempted tasks, then tasks with the weakest valid
  score, and retrieves validated lessons by explicit tag overlap.

The policy version and rationale are recorded with every attempt.

### 3.7 Validation and promotion

The included benchmark validates graph-color assignments:

- every graph node must have an assignment
- adjacent nodes must use different colors
- score is the number of distinct colors; lower is better

A lesson is promoted only when the candidate is valid and strictly improves the
best prior score for that task.

## 4. Implementation Plan

All milestones require offline tests to pass and must not print secret values.

### 4.1 Stage 1: Offline vertical slice

- Domain models and strict worker contract
- File-backed research store
- Graph-coloring validator and sample tasks
- Deterministic local worker
- Scheduler policies and report
- Dependency-free OpenHands V1 client
- Offline lifecycle and orchestration tests

Demo: run a complete local campaign and inspect immutable attempts and promoted
lessons.

### 4.2 Stage 2: Bounded Enterprise smoke test

- Confirm authentication separately from conversation creation
- Run preflight against OpenHands Enterprise 0.24.0
- Create one campaign with two child conversations
- Confirm repository and branch selection
- Reconcile terminal state from list records and durable events
- Confirm final-response indexing grace
- Capture which metadata fields are actually available

Demo: open both child conversations in the Enterprise UI and correlate them to
the generated report.

### 4.3 Stage 3: Comparative experiment

- Add naive and managed matched-run command
- Fix attempt, model, timeout, and concurrency budgets
- Run at least three matched seeds
- Report score improvement per attempt, duplicates, coverage, and invalid rate

Demo: reproduce a complete evidence report from immutable artifacts.

### 4.4 Stage 4: Production hardening

- Confirm first production user and tenancy model
- Implement PostgreSQL store if concurrent writers are required
- Add leases, idempotency keys, migrations, retention, and access control
- Package Kubernetes resources and compatibility checks

Demo: recover a running campaign after controller restart without duplicate
attempts.
