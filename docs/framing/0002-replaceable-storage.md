# 0002: Keep storage replaceable

Date: 2026-07-25

## Status

Accepted.

## Decision

Define a research-store interface for campaigns, attempts, lessons, and reports.
Ship a single-writer filesystem implementation in Stage 1. Add PostgreSQL only
when concurrent controllers, multiple tenants, or operational query volume
requires it.

Do not write to OpenHands internal database tables. If a supported API gap
cannot otherwise be closed, a read-only, version-pinned exporter may be
considered and must remain optional.

## Consequences

- Offline development requires no infrastructure.
- Git can audit versioned configuration, lessons, and reports.
- Production concurrency remains a known Stage 3 capability rather than an
  accidental promise of the file implementation.
- Storage migration does not change worker prompts, validators, or scheduler
  policies.
