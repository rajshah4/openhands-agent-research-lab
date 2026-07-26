# Replicated bounded scale study

This exploratory study asks how the tested OpenHands Enterprise/Replicated
deployment behaves when a six-task batch becomes a longer queue. It does not
claim that this small installation can run 100 agents simultaneously.

## Test boundary

- OpenHands Enterprise `0.24.0`
- server `1.46.2`
- agent-server `1.36.0-python`
- Claude Haiku 4.5 through the same LiteLLM profile
- 12 prompt-contained tasks made by cycling the same six hard-transfer
  problems with unique attempt IDs
- four active agents at most
- `0.75` seconds between application API requests
- ten-runtime capacity assumption and launch lock at seven active sandboxes
- deterministic validation of every final answer

The 12-task workload doubled the earlier six-task matched batch without raising
instantaneous agent concurrency.

## Result

| Pattern | Valid | Sandboxes | Wall time | Throughput | Controller retries |
| --- | ---: | ---: | ---: | ---: | ---: |
| Isolated queue | 12/12 | 12 | 421.3 s | 104.8 tasks/hour | 4 |
| Long-lived shared pool | 10/12 | 2 | 834.7 s | 52.0 tasks/hour | 0 |
| Two bounded shared cells | 12/12 | 2 | 558.3 s | 77.9 tasks/hour | 1 |

All recorded sandboxes were paused after their arm. No runtime pod restarted.
Observed node memory stayed at or below 50% during the runs.

The isolated queue kept four sandboxes active and paused each one immediately
after its task. It completed all 12 tasks. Three transient authentication
responses and one transport timeout were retried successfully.

The long-lived shared pool filled one sandbox with six conversations and
rolled into a second sandbox. Two of the second-cell start tasks never became
ready within 600 seconds. After the run they still reported
`PREPARING_REPOSITORY` and `STARTING_CONVERSATION`, even though the workload
explicitly selected no repository. The other ten tasks validated. Both
sandboxes paused cleanly.

The bounded-cell pattern ran two separate six-task shared batches. Each batch
owned one sandbox, admitted four active agents, drained, verified its six
answers, and paused the sandbox before the next cell began. Both cells
completed 6/6.

## What this changes

For this tested Enterprise version, do not submit a 100-job workload as one
long-lived shared pool and assume automatic sandbox rollover will be reliable.

The production choices supported by this evidence are:

1. Use an isolated four-active queue when isolation and reliable placement are
   more important than runtime density.
2. Use bounded shared work cells for trusted work when reducing runtime count
   matters. Give each cell one lifecycle owner and recycle it after at most six
   conversations.
3. Do not run parallel shared cells under one user until the platform provides
   and the installation verifies an explicit sandbox-pool or sandbox-targeting
   contract. A global placement strategy is not a lease.

At the measured exploratory rates, 100 queued tasks would take about 57 minutes
in the isolated pattern or 77 minutes as sequential bounded shared cells.
Those are linear planning estimates, not capacity promises. Model latency
varied materially between runs, and there is only one accepted 12-task
replicate per pattern.

The bounded shared estimate uses 17 six-conversation sandboxes over the life of
the queue, one at a time. The isolated estimate uses 100 sandboxes over the
life of the queue, four at a time. Running 100 tasks simultaneously was not
tested and is not recommended on this installation.

## Stop decision

The planned 24-task point was not launched. The two stuck start tasks met the
predeclared control-plane stop condition. Increasing the queue before
understanding the rollover failure would have produced more load, not better
evidence.

## Reproduce

Use the exact commands in
[`docs/replicated-multi-agent-operations.md`](../../docs/replicated-multi-agent-operations.md#run-the-bounded-scale-study).
The sanitized numeric result is in [`results.json`](results.json).

