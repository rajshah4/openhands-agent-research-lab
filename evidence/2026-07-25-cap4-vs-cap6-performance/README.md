# Sandbox cap 4 versus cap 6

Date: 2026-07-25

This comparison asks whether allowing six OpenHands conversations in one
sandbox improves a bounded research campaign compared with the earlier limit
of four.

The comparison uses the same:

- Rajistics Replicated OpenHands Enterprise installation;
- `FEWEST_CONVERSATIONS` grouping strategy;
- public benchmark repository and `main` branch;
- managed scheduler;
- Conversation V1 lifecycle;
- deterministic validators;
- five-second controller polling interval;
- ten-runtime installation ceiling and seven-sandbox launch lock.

The cap-4 evidence contains five sequential conversations. The cap-6 run
contains seven sequential conversations so the sixth slot and automatic
rollover are both exercised. The first four tasks form a directly matched
subset. This is an infrastructure comparison, not a statistically powered
model-quality benchmark.

## Result

| Measure | Cap 4 | Cap 6 |
| --- | ---: | ---: |
| Conversations | 5 | 7 |
| Valid candidates | 5/5 | 7/7 |
| Sandboxes used | 2 | 2 |
| Conversations per observed sandbox | 2.5 | 3.5 |
| Mean startup observation | 10.646 s | 10.671 s |
| Median startup observation | 10.677 s | 10.651 s |
| Mean end-to-end attempt | 52.081 s | 51.855 s |
| Cold-sandbox selections | 2/5 | 2/7 |
| Duplicate candidates | 0 | 1 |
| Final unhealthy pods | 0 | 0 |
| Final running runtime pods | 1 warm runtime | 1 warm runtime |

The duplicate in the cap-6 run was the intentional seventh attempt after all
six benchmark tasks had coverage. Its candidate remained valid; it did not
represent a runtime or validation failure.

## Matched first-four task timing

| Task | Cap 4 | Cap 6 | Change |
| --- | ---: | ---: | ---: |
| `color-bipartite-8` | 51.782 s | 42.772 s | -17.4% |
| `color-cycle-7` | 61.755 s | 62.583 s | +1.3% |
| `cover-campus` | 50.413 s | 44.023 s | -12.7% |
| `cover-grid` | 50.469 s | 51.238 s | +1.5% |
| **Mean** | **53.605 s** | **50.154 s** | **-6.4%** |

The paired results move in both directions. Model execution dominates these
short tasks, so the 6.4% mean reduction should not be attributed to the
sandbox cap without repeated runs.

Startup observation for the matched subset was 10.633 seconds under both
limits. The controller polls every five seconds, and the installation
maintains a warm runtime, so this measurement cannot resolve small startup
differences. It does show that raising the cap did not add a measurable
startup penalty.

## Cap-6 lifecycle

The first six conversations used sandbox `7f75DQBvPTisvIWsdB3yrm`. The seventh
conversation was correctly placed in a new sandbox
`5s8ytFBTrc4PYQ6n87JpRa`.

| Sequence | Task | Conversation | Sandbox | Result |
| ---: | --- | --- | --- | --- |
| 1 | graph coloring | [f92064bf](https://app.replicated.rajistics.com/conversations/f92064bf3abe419ba888b0d16cf80bf4) | `7f75DQBvPTisvIWsdB3yrm` | valid, score 2 |
| 2 | graph coloring | [1d6863d7](https://app.replicated.rajistics.com/conversations/1d6863d74d484222a38280d015d0ea00) | `7f75DQBvPTisvIWsdB3yrm` | valid, score 3 |
| 3 | set cover | [70e9578d](https://app.replicated.rajistics.com/conversations/70e9578d74c44d0da27225d32a8798a5) | `7f75DQBvPTisvIWsdB3yrm` | valid, score 2 |
| 4 | set cover | [5ed6c3e7](https://app.replicated.rajistics.com/conversations/5ed6c3e7f1c241088ecd7db22b9d0bcc) | `7f75DQBvPTisvIWsdB3yrm` | valid, score 2 |
| 5 | bin packing | [388acf30](https://app.replicated.rajistics.com/conversations/388acf301df249219f63d307f713b65d) | `7f75DQBvPTisvIWsdB3yrm` | valid, score 2 |
| 6 | bin packing | [278365dc](https://app.replicated.rajistics.com/conversations/278365dc682d43d8ad647f9f9d1ddde5) | `7f75DQBvPTisvIWsdB3yrm` | valid, score 2 |
| 7 | graph coloring | [1b835c1f](https://app.replicated.rajistics.com/conversations/1b835c1f52464eaeb7bf77de49eb9814) | `5s8ytFBTrc4PYQ6n87JpRa` | valid duplicate, score 3 |

Both sandboxes were paused once all conversations were terminal. The final
cluster check found zero unhealthy pods and one warm runtime.

## Interpretation

Raising the cap from four to six improved runtime packing, not agent speed:

- observed conversations per sandbox increased by 40%;
- theoretical capacity per sandbox increased by 50%;
- the share of attempts that required a new sandbox fell from 40% to 28.6%;
- a five- or six-conversation batch now fits in one sandbox instead of two;
- per-attempt startup and end-to-end timing remained effectively unchanged;
- validation reliability remained 100%.

Cap 6 is therefore a better default for sequential, trusted research agents on
this installation. It should not yet be treated as approval for six agents to
execute concurrently in one runtime. Concurrent production scheduling still
needs a separate live-work limit, resource telemetry, draining, and pool
leases.

The cap remains a direct Kubernetes deployment override:

```text
OH_APP_CONVERSATION_MAX_NUM_CONVERSATIONS_PER_SANDBOX=6
```

It should be promoted into Replicated configuration or a version-controlled
deployment overlay before being considered durable.
