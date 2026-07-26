# Planning a full 400-task NeuroGolf campaign

This is a capacity model for running the entire 2026 NeuroGolf Championship as
a managed OpenHands research organization. It separates facts, measured
OpenHands behavior, and planning assumptions so the numbers can be changed
without changing the architecture.

The interactive version is in the dashboard's **Planner** view.

## Competition facts

- The competition contained 400 ARC-AGI-1 tasks.
- Each task required a correct ONNX graph.
- Optimization rewarded smaller parameter and inference-memory cost.
- Candidate work could run in parallel, but archive assembly, full 400-task
  audit, and submission promotion needed a serial release gate.
- The project postmortem found that only 151 tasks received an independent
  attempt; 249 never did. Coverage therefore has to be a controller invariant,
  not a prompt suggestion.

Sources:

- [Official IJCAI competition description](https://2026.ijcai.org/competitions/)
- [NeuroGolf agent-management postmortem](https://www.kaggle.com/competitions/neurogolf-2026/writeups/155th-place-what-i-learned-about-managing-ai-codi)

## Default planning scenario

The dashboard defaults to a serious but adjustable campaign:

| Input | Default |
| --- | ---: |
| Competition tasks | 400 |
| Agent attempts per task | 12 |
| Total agent attempts | 4,800 |
| Parallel work cells | 4 |
| Agents per cell | 4 |
| Active agents | 16 |
| ONNX workload factor versus the prompt-heavy benchmark | 3× slower |
| Model cost per attempt | $0.025 |
| Evidence retained per attempt | 5 MB |

This is not a claim that 12 attempts is sufficient to win. The planner provides
coverage, serious-campaign, and intensive-search presets and lets the operator
change every uncertain assumption.

## Projected requirements for the default

| Requirement | Projection |
| --- | ---: |
| First-coverage attempts | 400 |
| Follow-up optimization attempts | 4,400 |
| Application ledger lifecycle records | about 48,000 |
| Artifact storage | about 23.4 GB |
| Model calls | 4,800 |
| Estimated model spend | about $120 |
| Shared sandboxes over campaign lifetime | 800 |
| Isolated sandboxes over campaign lifetime | 4,800 |

With four parallel four-agent work cells, the worker allocation assumption is
16 vCPU and 32 GB RAM. Adding 30% headroom gives a planning target of about
21 vCPU and 42 GB RAM for workers. OpenHands platform services, PostgreSQL,
object storage, observability, and backups are additional.

Using the exploratory 12-job measurements and the 3× ONNX workload factor:

| Placement | Estimated duration | Simultaneous sandboxes |
| --- | ---: | ---: |
| Isolated queue | 1.4 days | 16 |
| Bounded shared cells | 1.9 days | 4 |

The isolated result was faster in the one scaled replicate but used one sandbox
per attempt. Bounded cells reduced runtime creation by 83% and completed every
task, but the two cells ran sequentially. Parallel shared cells have not been
validated on this Enterprise installation.

Model latency varied substantially in the measured experiments. These duration
figures are capacity-planning estimates, not service-level objectives.

## What 100 agents at once would require

One hundred active agents is different from 100 queued jobs.

| Boundary | Isolated | Four-agent shared cells |
| --- | ---: | ---: |
| Active agents | 100 | 100 |
| Simultaneous sandboxes | 100 | 25 |
| Worker allocation before headroom | about 200 vCPU / 400 GB | about 100 vCPU / 200 GB |
| Worker allocation with 30% headroom | about 260 vCPU / 520 GB | about 130 vCPU / 260 GB |

The shared estimate assumes 4 vCPU and 8 GB per four-agent ONNX work cell. The
isolated estimate assumes 2 vCPU and 4 GB per agent runtime. Both need to be
replaced with measured resource profiles from real ONNX builds and validators.

At one status request every four seconds, 100 agents would generate about 1,500
controller requests per minute before lifecycle bursts. The tested controller
was deliberately held near 80 requests per minute. A real 100-agent deployment
therefore needs event-driven status, a substantially higher tested API budget,
or sharded control planes. Increasing Kubernetes capacity alone does not solve
the application API boundary.

## Production architecture at 100-agent scale

```text
400-task registry
       |
application-owned PostgreSQL
  - queue and leases
  - coverage counters
  - attempts and candidate state
  - idempotency and lifecycle
       |
external scheduler
  - task ownership
  - global and per-cell limits
  - provider and API budgets
       |
bounded OpenHands work cells
  - one task owner per agent
  - four trusted agents per sandbox
  - six conversations maximum per cell
  - drain, verify, pause, recycle
       |
independent validation pool
  - official cases
  - independent rule
  - synthetic and metamorphic tests
       |
object storage
  - ONNX and builder artifacts
  - validation logs and counterexamples
  - content hashes and provenance
       |
single-writer promotion pipeline
  - differential audit
  - full 400/400 archive audit
  - submission budget and quarantine
```

This is the target when several controllers must claim work concurrently. Do
not use Git as the runtime queue and do not write to OpenHands internal
database tables. Git remains the release and audit layer. At this scale the
research application owns PostgreSQL and object storage.

For the current four-active-sandbox deployment, an application-owned database
is not required yet. The hardened 4,800-attempt resilience test completed in
19.08 seconds, fit in 94 MB, and retained 24,013 parseable JSON records without
corruption. The runner now keeps an indexed in-memory run view, caches validated
lessons, takes an exclusive controller lock, resumes the same run and attempt
IDs, and reattaches to a persisted OpenHands start task after a restart.

Those changes make the files-first path a credible **single-controller
production pilot**. They do not turn files into a distributed queue. Keep
exactly one controller responsible for campaign ownership. Move to
application-owned PostgreSQL with leases and idempotent claims when multiple
controllers, multiple tenants, or operational queries become requirements.

The 400-task deterministic scale simulation also completed 4,800 attempts in
each arm: 9,600 total attempts, exactly 12 per task, in 16.01 seconds. It proves
the bookkeeping shape of a full NeuroGolf campaign, not ONNX or model
performance.

## OpenHands product gap

The 12-job shared-pool test stalled two start tasks during automatic sandbox
rollover. Two explicit six-job cells completed 12/12.

Until the installed version provides and verifies an explicit sandbox-pool or
sandbox-targeting lease:

1. keep each shared cell bounded;
2. give one controller sole lifecycle ownership;
3. drain and pause it at the six-conversation boundary;
4. use isolated placement where parallel cell ownership cannot be guaranteed;
5. do not treat `FEWEST_CONVERSATIONS` as a lease.

The next infrastructure scale gate is not 100 agents. It is a matched 24-job
test after the rollover failure is fixed, followed by two explicitly leased
shared cells running in parallel. The next domain gate is a licensed NeuroGolf
workload adapter with ONNX execution, adversarial validation, artifact
quarantine, and a single-writer archive audit.
