# 0003: Keep the ledger file-backed until controllers become concurrent

Date: 2026-07-25

## Status

Accepted after the multi-family scale milestone.

## Context

The Rajistics instance is deliberately limited to roughly ten runtime
containers. The research controller therefore launches one worker at a time,
locks new launches at seven active sandboxes, and pauses each completed
sandbox. The 12-task offline comparison and bounded live comparison both use
one controller and append-only attempt records.

The public dashboard is read-only. It consumes a sanitized release snapshot,
not credentials or a live connection to the OpenHands control plane.

## Decision

Keep `FileResearchStore` as the reference implementation for the current
single-controller deployment. Use Git for versioned task definitions, schemas,
sanitized evidence bundles, and dashboard releases—not for runtime locking.

Do not manipulate the PostgreSQL database internal to OpenHands. It is an
implementation detail of the installed product, not the research lab's data
contract.

Add a separate application-owned PostgreSQL implementation only when one of
these triggers is real:

- more than one scheduler/controller can claim work
- multiple tenants need isolated retention and access policies
- atomic leases, retries, or idempotency must span controller processes
- operational queries exceed what immutable run bundles can serve safely

At that boundary, PostgreSQL becomes the coordination system of record. The
same immutable records can still be exported to Git/object storage for public
evidence and reproducibility.

## Consequences

- The current solution has no separate database to install, back up, or expose.
- A controller restart can recover from the append-only lifecycle and attempt
  ledger, but two controllers must not share one file-store root.
- The dashboard remains safe to publish because it receives a sanitized
  snapshot rather than privileged runtime access.
- Production adopters have an explicit scale boundary instead of an accidental
  promise that filesystem locking is distributed coordination.
