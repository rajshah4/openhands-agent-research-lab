# 0001: OpenHands is the execution plane

Date: 2026-07-25

## Status

Accepted.

## Decision

Use first-class OpenHands V1 app conversations as isolated worker attempts.
Create children through `POST /api/v1/app-conversations`, poll asynchronous
start tasks, observe conversation records, and reconcile terminal state and
final output from durable events.

Keep task selection, deterministic validation, candidate promotion, and
organizational memory in the research-lab application.

## Consequences

- Every live attempt appears in the OpenHands UI with an immutable conversation
  identifier and link.
- The integration remains on supported APIs instead of private tables.
- Version-specific behavior must be captured in compatibility tests and notes.
- OpenHands is the primary worker backend, while the domain model remains
  independent enough to support offline tests and future adapters.
