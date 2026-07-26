# Four concurrent agents in one Enterprise runtime

Date: 2026-07-25

This experiment tests a practical operating point for the Rajistics
Replicated installation: keep the sandbox capacity at six conversations, but
dispatch no more than four active agents into one runtime.

## Result

Two four-agent batches completed successfully:

- eight of eight candidates passed deterministic validation;
- every batch placed all four conversations in one sandbox;
- lifecycle records prove four ready-to-terminal conversations overlapped;
- both sandbox pools were paused after their final conversation;
- the runtime recorded zero restarts and no unhealthy pods;
- one run recovered from nine HTTP `429` responses and the repeat saw none.

The two batches had materially different tail latency. The first contained one
230-second conversation; the repeat's slowest conversation took 111 seconds.
That variance is important: one live agent response can determine the wall time
of a small concurrent batch.

## Performance

The sequential baseline uses the same four graph-coloring and set-cover tasks.
The four-agent aggregate pools both live runs. The six-agent result is included
as an operational reference and contains two additional bin-packing tasks.

| Measure | Sequential four | Concurrent four, run 1 | Concurrent four, run 2 | Four-agent aggregate | Concurrent six |
| --- | ---: | ---: | ---: | ---: | ---: |
| Valid candidates | 4/4 | 4/4 | 4/4 | 8/8 | 6/6 |
| Batch wall time | 200.622 s | 230.414 s | 123.069 s | 176.742 s average | 199.551 s |
| Effective throughput | 71.78/hour | 62.50/hour | 117.01/hour | 81.48/hour | 108.24/hour |
| Mean attempt latency | 50.153 s | 124.837 s | 75.271 s | 100.054 s | 121.814 s |
| Maximum attempt latency | 62.581 s | 230.414 s | 110.965 s | 230.414 s | 187.461 s |
| Recovered HTTP 429s | not recorded | 9 | 0 | 4.5/run | 36 |

Across the two runs, four-way dispatch improved effective throughput by 13.5%
over sequential execution while doubling mean individual latency. The
six-agent batch achieved higher throughput, but it also generated substantially
more API backpressure.

## Runtime observations

The two grouped pools mapped to physical runtimes
`runtime-epomytedjjzmhnbh` and `runtime-auykccjyqkkedsfk`.

Observed samples:

- peak grouped-runtime CPU: approximately `107m`;
- peak grouped-runtime memory: approximately `436 MiB`;
- configured limit: `1 CPU`, `2 GiB`;
- runtime restarts: `0`;
- unhealthy cluster pods: `0`.

The physical runtime was not close to its CPU or memory limit. These benchmark
tasks spend much of their time waiting for model and API responses, so the
result does not establish the same safety margin for build-heavy workloads.

## Decision

Use six as the sandbox storage/reuse cap and four as the default batch dispatch
limit for trusted, model-wait-heavy work.

This separates two controls that solve different problems:

- sandbox capacity six preserves reuse and leaves room for queued work;
- active concurrency four reduces request bursts and retains runtime headroom;
- interactive work should use one or two active agents;
- six active agents remains an opt-in mode for latency-tolerant throughput runs.

A production scheduler should treat four as a ceiling, not a promise. It should
queue additional work, apply one shared API request limiter, reduce concurrency
when `429` responses or tail latency rise, and pause the pool after it drains.
