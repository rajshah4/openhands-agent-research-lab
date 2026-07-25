# 0004: Use Enterprise sandbox grouping for trusted worker pools

## Status

Accepted for a bounded production pilot.

## Context

One sandbox per conversation gives the strongest isolation and the simplest
lifecycle, but short trusted research attempts pay repeated runtime allocation
cost and can exhaust a small installation's container limit.

OpenHands Enterprise 0.24.0 exposes a user-level Sandbox Grouping Strategy.
`Group by Newest` can add new first-class app conversations to the most recent
eligible sandbox. This preserves Enterprise conversation history and supported
V1 APIs while reusing runtime compute.

A live Rajistics test ran five conversations in one sandbox, including two
concurrent problem families. All five candidates passed independent validation,
peak active sandbox count remained one, and a final pool-level pause released
the claimed runtime resources.

## Decision

Use Enterprise sandbox grouping as the preferred efficient execution mode for
trusted, single-team research agents.

Start with a pool of two or three sandboxes:

- one active conversation per sandbox by default;
- at most two concurrent conversations per sandbox after validation;
- a fresh first-class conversation for every attempt;
- distinct workspace paths keyed by conversation ID;
- deterministic validation outside the worker;
- pool-level draining, pause, and recycling;
- one-sandbox-per-conversation fallback for untrusted or isolated work.

The research controller, not an individual attempt, owns grouped sandbox
lifecycle. It must acquire a lease before launch and pause only when the lease
count reaches zero.

## Consequences

Benefits:

- fewer active runtime containers;
- retained Enterprise UI, events, metadata, and conversation links;
- no dependency on OpenHands internal database tables;
- simpler production integration than a separately operated Agent Canvas
  backend.

Costs:

- a wider runtime trust and failure boundary;
- lifecycle requires leases, draining, and reconciliation;
- resource contention becomes a per-sandbox scheduling concern;
- physical runtime deletion can lag the V1 state transition and must be
  observed separately.

## Rejected alternatives

- Manipulating the OpenHands database: unsupported ownership boundary.
- Reusing one conversation: contaminates context and experiment validity.
- Pausing after every grouped attempt: can interrupt another active
  conversation.
- One unlimited shared sandbox: excessive blast radius and no bounded capacity.
