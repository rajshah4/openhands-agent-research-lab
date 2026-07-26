# Six concurrent agents in one Enterprise runtime

Date: 2026-07-25

This stress test asks whether six trusted OpenHands agents can execute
concurrently inside one grouped Enterprise runtime on the small Rajistics
Replicated installation.

## Environment

- Sandbox grouping strategy: `FEWEST_CONVERSATIONS`
- Conversations per sandbox: `6`
- Grouped runtime limit: `1 CPU`, `2 GiB`
- Installation runtime limit: `10`
- Controller launch lock: `7` active user-visible sandboxes
- Six distinct deterministic benchmark tasks
- First-class Conversation V1 records and independent validators

## Naive launch result

Launching five independent CLI controllers at the same moment as a seed
conversation did not reliably reach the runtime:

- three conversation creations received HTTP `429`;
- the seed controller later received `429` while polling conversation state;
- only three conversations reached `READY`;
- the runtime stayed healthy and did not restart.

The observed Enterprise response was:

```text
Rate limit exceeded: 10 per 1 second
```

This is an orchestration-plane limit, not a sandbox failure. Independent
controllers each perform capacity checks, creation, start-task polling,
conversation polling, and event retrieval. Their synchronized request bursts
can exceed the API limit before runtime capacity is tested.

The partial sandbox was paused before retrying.

## Rate-aware launch result

A single controller globally paced requests, retried `429` responses with
bounded backoff, seeded one sandbox, and launched five followers as soon as the
seed reached `READY`.

| Task | Conversation | Sandbox | Result |
| --- | --- | --- | --- |
| graph coloring | [1b2b1fc3](https://app.replicated.rajistics.com/conversations/1b2b1fc3a17048ccbf582f72876ac9d1) | `1HXjaQTFWCJR1Nsx0KgiSP` | valid, score 3 |
| graph coloring | [423001f8](https://app.replicated.rajistics.com/conversations/423001f8b9224abfb4a650e728201196) | `1HXjaQTFWCJR1Nsx0KgiSP` | valid, score 2 |
| set cover | [5a089325](https://app.replicated.rajistics.com/conversations/5a089325974f4712bf8b255b7b35cf59) | `1HXjaQTFWCJR1Nsx0KgiSP` | valid, score 2 |
| set cover | [759a9788](https://app.replicated.rajistics.com/conversations/759a97881e5f4aa8a095fa17d82967a6) | `1HXjaQTFWCJR1Nsx0KgiSP` | valid, score 2 |
| bin packing | [c4da38d5](https://app.replicated.rajistics.com/conversations/c4da38d517494625a3373598e7db2c77) | `1HXjaQTFWCJR1Nsx0KgiSP` | valid, score 2 |
| bin packing | [ba280432](https://app.replicated.rajistics.com/conversations/ba28043235b74b29b889669f049dc701) | `1HXjaQTFWCJR1Nsx0KgiSP` | valid, score 2 |

Acceptance results:

- six of six conversations reached terminal state;
- six of six candidates passed deterministic validation;
- all six conversations used the same sandbox;
- lifecycle timestamps prove maximum ready-to-terminal concurrency of six;
- the runtime recorded zero restarts;
- the cluster recorded zero unhealthy pods;
- the pool owner paused the sandbox after all six completed;
- final physical state returned to one warm runtime.

The rate-aware controller still encountered and successfully recovered from 36
HTTP `429` responses. The API rate limit therefore needs to be treated as a
shared production scheduling constraint even with moderate client-side
pacing.

## Sequential versus concurrent performance

The comparison uses the same six tasks from the earlier sequential cap-6 run.

| Measure | Sequential six | Concurrent six | Change |
| --- | ---: | ---: | ---: |
| Valid candidates | 6/6 | 6/6 | unchanged |
| Batch wall time | 307.127 s | 199.551 s | -35.0% |
| Throughput | 70.33 tasks/hour | 108.24 tasks/hour | +53.9% |
| Mean attempt latency | 51.185 s | 121.814 s | +138.0% |
| Median attempt latency | 51.071 s | 132.112 s | +158.7% |
| Maximum attempt latency | 62.583 s | 187.461 s | +199.5% |

Six-way concurrency improves batch throughput while making each individual
conversation much slower. This is expected on a one-CPU runtime: agents spend
time waiting on both shared compute and globally paced API access.

## Runtime observations

The grouped conversation URL mapped to physical runtime
`runtime-oksipfbgbqfbfnty`.

Observed samples during the test:

- peak grouped-runtime CPU: approximately `104m`;
- peak grouped-runtime memory: approximately `456 MiB`;
- configured limit: `1 CPU`, `2 GiB`;
- runtime restarts: `0`;
- unhealthy cluster pods: `0`.

The runtime did not approach its memory limit. These short optimization tasks
spend substantial time waiting for model responses, so this does not establish
that six concurrent compilation, browser, or test-heavy agents will be safe.

## Decision

Six conversations per sandbox remains a good storage and sequential-reuse cap.
For active execution:

- use one or two concurrent agents for interactive work;
- allow up to six only for trusted, latency-tolerant batch research;
- enforce one global request limiter across the organization;
- use bounded `429` retry and jitter;
- retain runtime health, restart, and memory gates;
- drain and pause the sandbox after the batch;
- fall back to isolated sandboxes for untrusted or resource-heavy work.

The runtime passed. The first scaling bottleneck was the Enterprise API rate
limit, followed by higher per-agent latency—not CPU exhaustion, memory
exhaustion, or container instability.
