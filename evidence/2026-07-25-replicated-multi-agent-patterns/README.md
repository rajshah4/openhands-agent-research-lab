# Replicated multi-agent deployment patterns

Date: 2026-07-25

This experiment asks a practical Enterprise question: for six first-class
OpenHands conversations, how much isolation and concurrency should an operator
configure on a small Replicated installation?

## Matched protocol

Every accepted arm used the same:

- six prompt-contained hard-transfer optimization tasks;
- Claude Haiku 4.5 model and deterministic validators;
- managed static task assignment with no duplicated work;
- 600-second execution timeout;
- one controller-wide request every 0.75 seconds;
- three successful replicates.

The repository mount was disabled in every accepted arm. The tasks never read
the checkout, and the installation's Git-provider integration began rejecting
the otherwise reachable public repository during preflight. Mixing
repository-mounted and prompt-only arms would have biased the comparison.

## Result

| Pattern | Valid | Runtimes per batch | Active agents | Mean wall | Mean throughput | Mean model cost | Controller retries |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Isolated, bounded | 18/18 | 6 | 4 | 284.9 s | 79.29 tasks/hr | $0.1929 | 12 |
| Grouped, bounded | 18/18 | 1 | 4 | 272.0 s | 80.71 tasks/hr | $0.2402 | 0 |
| Grouped, full | 18/18 | 1 | 6 | 280.1 s | 78.94 tasks/hr | $0.1552 | 0 |

Grouped-four used 83.3% fewer runtimes than isolated-four and had 4.5% lower
mean wall time. Raising the shared sandbox from four to six active agents did
not improve mean performance: grouped-six was 3.0% slower than grouped-four.

Model cost varied substantially between otherwise matched replicates, so the
cost ordering is not treated as a placement effect. Infrastructure cost was
not measured.

## What broke

The failures are part of the production result:

1. Six simultaneously active isolated runtimes produced repeated control-plane
   read timeouts and transient authentication errors. The stress batch recorded
   `0/6` valid attempts despite healthy, non-restarting runtime pods.
2. Bounded isolated execution succeeded, but its accepted replicates still
   needed nine transient-auth and three transport retries.
3. Grouped-four and grouped-six needed no controller retries across 36 accepted
   attempts.
4. Two repository-mounted starts failed at the Git-provider boundary. The
   runner now records the failed start's sandbox and pauses it.
5. One bounded isolated replicate was excluded after an agent finished without
   the required JSON contract. All of its sandboxes were still paused.

The hardened controller retries bounded transient failures, records start-task
sandbox IDs, continues cleanup after an individual pause failure, and provides
a standalone recovery command.

## Recommendation

For a trusted team, begin with:

- `FEWEST_CONVERSATIONS`;
- four active conversations per sandbox;
- a controller queue for additional work;
- one lifecycle owner that pauses the sandbox only after the batch drains;
- one organization-wide API limiter;
- sandbox recycling by age, job count, memory, or failure.

Use `NO_GROUPING` when code is untrusted, tenants differ, or failures need the
smallest possible blast radius. Keep isolated concurrency at four or lower on
an installation of this size and pause each sandbox as its worker completes.

Use six-active grouping only after the same workload passes a customer-specific
load test. It is a capacity mode, not the default: this experiment found no
mean speed advantage over four active agents.

## Reproduce it

The exact supported settings, launch, health, cap-verification, recovery, and
restore commands are in
[`docs/replicated-multi-agent-operations.md`](../../docs/replicated-multi-agent-operations.md).
No command reads or modifies the OpenHands internal database.

Machine-readable evidence is in [`results.json`](results.json).
