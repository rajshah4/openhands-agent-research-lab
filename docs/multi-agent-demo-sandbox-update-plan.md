# Sandbox capacity update for `openhands-multi-agent-demo`

The existing demo teaches how agents coordinate: parent-child delegation,
polling, event-driven work, and Agent Canvas. The update should add a second,
independent decision: **where those agents run**.

## The four placement choices to teach

| Placement | Conversation record | Runtime boundary | Best fit |
| --- | --- | --- | --- |
| Isolated Enterprise | One per agent | One sandbox per conversation | Untrusted code, mixed tenants, strongest failure isolation |
| Bounded Enterprise cell | One per agent | Several trusted conversations share one sandbox | Production controls with fewer containers |
| Agent Canvas | Canvas session and agent records | Shared backend/workspace | Lightweight demonstrations and tightly coupled trusted work |
| Subagents in one conversation | One parent context with delegated work | One sandbox | Lowest infrastructure overhead when separate audit histories are unnecessary |

Orchestration style and sandbox placement should not be conflated. A polling
parent can use isolated sandboxes or bounded cells. Event-driven scheduling does
not by itself reduce container count.

## Replicated evidence to add

Matched six-task batches:

| Setup | Valid | Mean wall time | Runtimes per batch | Controller retries |
| --- | ---: | ---: | ---: | ---: |
| Isolated, four active | 18/18 | 284.94 s | 6 | 12 |
| Grouped, four active | 18/18 | 272.01 s | 1 | 0 |
| Grouped, six active | 18/18 | 280.06 s | 1 | 0 |

Twelve-task scale check:

| Setup | Valid | Wall time | Sandboxes | Finding |
| --- | ---: | ---: | ---: | --- |
| Isolated queue | 12/12 | 421.26 s | 12 | Fastest, highest container churn |
| One long-lived shared pool | 10/12 | 834.70 s | 2 | Automatic rollover stalled two starts |
| Two explicit six-task cells | 12/12 | 558.25 s | 2 | Reliable bounded density |

The practical recommendation for this tested version is a bounded cell of at
most six trusted conversations, with explicit drain, pause, and recycle.
`FEWEST_CONVERSATIONS` is a user-scoped placement heuristic, not a lease and
not a signal that a sandbox has safe remaining capacity.

## Repository changes

1. Add `docs/sandbox-capacity.md` with the table above and a decision guide.
2. Add “orchestration versus placement” to the main README.
3. Extend the pattern chooser with isolation, audit-history, and container
   budget questions.
4. Add a small benchmark that runs the same work in isolated and bounded-cell
   modes with a strict active-runtime gate.
5. Persist conversation, sandbox, start-task, pause, retry, wall-time, and
   validity evidence.
6. Add a warning that grouping applies to new conversations for the
   authenticated user and should not be treated as instance-wide capacity
   management.
7. Link back to this research lab for full results and failure evidence.

## Safe example default

- four active agents;
- six conversations maximum in a trusted cell;
- one lifecycle owner per cell;
- stop new launches at seven active runtimes on a ten-runtime cluster;
- validate every result outside the agent;
- pause only after the whole cell drains;
- use isolated placement for untrusted or cross-tenant work.

## Controller lesson to add

The demo should show that orchestration and placement are separate choices.
OpenHands runs the agents, while one small controller owns the campaign:

```text
files + Git checkpoint
        |
        v
single controller
        |
        +-- Enterprise conversations
        +-- Agent Canvas work cells
        `-- bounded native subagents
```

For the demo, files plus Git are enough because one controller owns claims and
checkpoints. The tested ledger handled 4,800 attempts and 24,013 parseable
records, and a second controller process resumed the same Canvas run. If the
demo later introduces multiple controller replicas or tenants that can claim
work concurrently, add application-owned database leases rather than using
OpenHands internal tables.

The customer-facing examples should include both Enterprise controller
placements:

- an external V1 controller service for sustained campaigns, tested at four
  active conversations with two queued in one grouped sandbox;
- an in-platform prompt automation for bounded scheduled cells, accepted at
  two child conversations. The four-child automation completed, but only 3/4
  child contracts were independently verifiable, so it should be retained as
  failure evidence rather than the default.
