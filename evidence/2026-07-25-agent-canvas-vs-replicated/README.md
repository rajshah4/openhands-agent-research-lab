# Agent Canvas versus Replicated deployment comparison

Date: 2026-07-25

This matched comparison asks a deployment question, not a scheduling question:
after managed scheduling has already assigned six distinct tasks, how do a
shared Kubernetes Agent Canvas backend and a grouped OpenHands Enterprise
runtime behave?

## Matched protocol

Both arms used:

- the six-task `hard-transfer-live` campaign;
- one preassigned task per agent with no overlap;
- six concurrent OpenHands agents;
- Claude Haiku 4.5 from the same dated model family;
- the same worker prompt contract and deterministic validators;
- a 600-second execution timeout;
- three successful replicates;
- isolated controller ledgers.

The provider paths differed. Canvas used
`anthropic/claude-haiku-4-5-20251001` directly. Replicated used
`litellm_proxy/us.anthropic.claude-haiku-4-5-20251001-v1:0` through its
Bedrock-backed LiteLLM service.

## Result

| Aggregate metric | Agent Canvas on GKE | Enterprise/Replicated |
| --- | ---: | ---: |
| Successful replicates | 3/3 | 3/3 |
| Independently valid | 18/18 | 18/18 |
| Mean task coverage per batch | 6/6 | 6/6 |
| Mean batch wall time | 140.7 s | 270.5 s |
| Wall-time range | 104–171 s | 231.5–320.9 s |
| Effective throughput | 153.55 tasks/hour | 79.86 tasks/hour |
| Mean attempt latency | 101.1 s | 169.9 s |
| Mean reported model cost | $0.2008 | $0.2028 |
| Reported cost per valid result | $0.03347 | $0.03380 |
| Runtime or workload restarts | 0 | 0 |

Canvas had 48.0% lower mean batch wall time and 92.3% higher effective
throughput. Reported model cost was effectively tied: Canvas was 1.0% lower,
well inside the run-to-run variation.

This is evidence about these deployed stacks. It is not a pure container
benchmark. Canvas calls one shared agent server directly. Enterprise creates
first-class app conversations through an authenticated asynchronous control
plane, applies global request limits, manages sandbox lifecycle, and preserves
additional governance metadata.

## Resource observations

Canvas used one persistent StatefulSet pod for every batch:

- pod requests: `500m` CPU and `1 GiB` memory;
- pod limits: `2 CPU` and `4 GiB` memory;
- one-second peak across the managed runs: `341m` and `839 MiB`;
- restarts: `0`.

Each Replicated batch used one grouped runtime:

- runtime limits: `1 CPU` and `2 GiB` memory;
- intermittent observed peak: `161m` and `463 MiB`;
- runtime restarts: `0`;
- all three pools were paused after their final conversation.

The resource samples are not directly comparable. Canvas was sampled every
second and retains its pod and PVC between batches. Replicated was sampled
intermittently, creates a replacement warm runtime, and relies on a larger
Enterprise control plane that is not included in the runtime-only number.
Infrastructure cost was not measured.

## Control-plane limit found

An initial Replicated run used a request every 0.25 seconds. All six
conversations reached the same sandbox, but the controllers then exceeded a
second Enterprise limit:

```text
Rate limit exceeded: 100 per 1 minute
```

Five attempts lost status before recording terminal evidence. The pool was
paused and that run was excluded from the matched performance result.

The shared controller now requires at least 0.65 seconds between requests and
defaults to 0.75 seconds. The three accepted Replicated replicates then
completed with zero `429` retries.

This is a production finding: grouped runtime capacity does not remove the need
for one organization-wide app-API limiter.

## Deployment tradeoff

Choose Kubernetes Agent Canvas when:

- one trusted team accepts a shared process, filesystem, and PVC boundary;
- compact deployment and high shared-backend throughput matter most;
- Enterprise identity, tenancy, and per-sandbox isolation are not required.

Choose OpenHands Enterprise/Replicated when:

- authentication, organizations, permissions, and governed conversation
  records are requirements;
- workloads may be untrusted or need an isolated-sandbox option;
- operators need supported lifecycle, archive, and UI-visible app-conversation
  controls;
- the organization can centralize scheduling and API backpressure.

The production-shaped Enterprise setting remains a sandbox capacity of six
with a default active dispatch limit of four. Six active conversations are
appropriate for bounded, trusted, latency-tolerant batches such as this test.

## Bottom line

Agent Canvas is the efficient shared execution backend. Replicated is the
governed deployment platform. Grouping lets Replicated approach Canvas's
runtime density, but it does not eliminate the control-plane work that buys
authentication, lifecycle management, auditability, and stronger isolation
choices.

The `agent-canvas-pilot` GKE cluster remains running. This experiment does not
authorize deleting its namespace, workload, or persistent volume.
