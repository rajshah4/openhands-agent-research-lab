# Framing: OpenHands Agent Research Lab

Status: 2026-07-25 · Project: building

## The ask, verbatim

Build, in stages, a production-minded multi-agent research organization that
uses OpenHands as far as its supported architecture allows. Use the NeuroGolf
case to demonstrate relevance to real-world agent work, identify OpenHands
infrastructure gaps, and document any workarounds required.

## Problem (no AI words), and what it costs today

Existing orchestration examples explain how work advances, but do not show how
an organization allocates repeated experiments, validates improvements, avoids
duplicated work, and preserves findings for future attempts.

The current cost has not been quantified. It is expected to appear as duplicated
experiments, poorly allocated worker capacity, and findings that cannot be
reused, but those quantities remain open and must be measured in the pilot.

## Stakeholder and decision (user and owner)

The intended users are practitioners building real multi-worker research and
optimization workflows. The project owner and first production adopter are not
yet confirmed.

The decision supported by the first release is whether OpenHands plus a small
coordination layer can improve repeated experimental work enough to justify a
production implementation.

## Goal and metric (chosen, rejected candidate, consequence)

Candidate primary metric, not yet confirmed: solution-quality improvement per
fixed agent-attempt budget.

Candidate secondary metrics: duplicate candidate rate, task coverage, invalid
attempt rate, and improvement latency.

No metric has yet been confirmed with a production stakeholder.

## Atomic unit

Current implementation assumption: one bounded worker attempt on one
deterministically validated task. This must be confirmed before expanding the
system to subjective research tasks.

## Failure modes and design controls

- Agents repeat prior work: hash candidates and retrieve validated lessons.
- Agent claims are treated as truth: deterministic validation gates promotion.
- Scheduler state is lost: write every completed attempt atomically.
- OpenHands list state is incomplete: reconcile terminal state from durable
  events and allow bounded final-response indexing grace.
- Storage becomes coupled to the demo: require all persistence through a store
  interface.
- OpenHands upgrades break the integration: use supported V1 APIs and record the
  tested Enterprise version.
- Sensitive data enters artifacts: sanitize metadata and never persist secrets.

## Operating assumptions

| Assumption | One-day test | If false | Status |
| --- | --- | --- | --- |
| Enterprise V1 can create and observe isolated worker conversations | Start one child and reconcile its terminal state and final response | Add a version-specific supported adapter or stop the live path | untested |
| A strict final contract can carry a small candidate and lesson | Run two children and validate both contracts deterministically | Move candidate transport to a committed artifact or object store | untested |
| Files are sufficient for one-controller Stage 1 | Complete an offline campaign and recover its report from artifacts | Implement PostgreSQL earlier | holding |
| Relevant lessons can be retrieved by explicit task tags | Compare retrieved lesson IDs with task-family expectations | Add structured feature extraction or embeddings later | untested |

## Simplest non-AI alternative (what it is, coverage %)

A deterministic scheduler, validator, and experiment ledger without agent
workers provides the control path and baseline. Its coverage has not yet been
measured. It remains the required comparison because agent orchestration is not
valuable when fixed heuristics solve the workload adequately.

## Alternatives and trade-offs

- Git/filesystem: transparent and portable, but single-writer and unsuitable for
  high-concurrency operational state.
- External PostgreSQL: production concurrency and queries, but additional
  deployment and migration responsibility.
- OpenHands internal database: rejected for writes because it creates unsupported
  product-schema coupling. A version-pinned read-only exporter is a last resort.

## Non-goals

- Reimplementing OpenHands conversation or sandbox management.
- Building a completely general multi-agent platform.
- Treating unvalidated agent statements as organizational memory.
- Depending on disputed or unclearly licensed competition solution code.
- Writing to OpenHands internal database tables.

## Signals

| Signal | Type | Number | Horizon | Agreed with |
| --- | --- | --- | --- | --- |
| Offline vertical slice passes deterministic tests | leading | all tests pass | Stage 1 | project assumption |
| Live conversations start, finish, and reconcile correctly | leading | 2 validated runs, with intermediate failures retained | Stage 2 smoke test | observed |
| Managed organization improves quality per attempt over baseline | success | open | at least 3 matched runs | open |
| Managed mode does not improve quality or duplication | stop | open | open | open |

## Decision log

- [0001 OpenHands is the execution plane](docs/framing/0001-openhands-execution-plane.md) - Use supported V1 conversations and events for worker execution.
- [0002 Keep storage replaceable](docs/framing/0002-replaceable-storage.md) - Begin with a file store, preserve a production database path, and never write OpenHands internal tables.
