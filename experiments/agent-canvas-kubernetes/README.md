# Agent Canvas on Kubernetes experiment

This experiment measures the efficiency of one shared, persistent Agent Canvas
backend against OpenHands Enterprise workers that receive isolated sandboxes.
It uses the official Agent Canvas Helm chart and the same research campaign,
worker contract, immutable ledger, and deterministic validators as the other
backends.

## Trust boundary

Agent Canvas is a single-tenant deployment. Every conversation shares one pod,
filesystem, shell, and PVC. This experiment is suitable only for a trusted team
and trusted workloads. It is not a replacement for Enterprise authentication,
multi-tenancy, or per-run sandbox isolation.

The pilot intentionally uses:

- one replica
- a dedicated namespace
- an internal-only `ClusterIP` service
- port-forward access
- no Ingress
- no Kubernetes RBAC for the agent
- a 20 GiB `standard-rwo` PVC
- one bounded conversation before any concurrency increase

## Tested target

- Agent Canvas chart `0.1.0`
- Agent Canvas image `1.5.2`
- Kubernetes `1.35`
- GKE Autopilot

Confirm the live chart and cluster versions before reusing these values.

## Deployment

The chart path defaults to the local Agent Canvas source checkout:

```bash
export AGENT_CANVAS_CHART="$HOME/Code/agent-canvas/helm/agent-canvas"
./experiments/agent-canvas-kubernetes/scripts/preflight.sh
./experiments/agent-canvas-kubernetes/scripts/deploy.sh --live
```

The deployment contains no LLM credential. Start the private port-forward:

```bash
./experiments/agent-canvas-kubernetes/scripts/port-forward.sh
```

Open `http://127.0.0.1:8000`, configure an LLM profile in Agent Canvas, and
then run the bounded pilot from another terminal:

```bash
./experiments/agent-canvas-kubernetes/scripts/run-pilot.sh --live
```

The pilot reads the Canvas API key from the pod without printing it. Research
artifacts remain on the controller under `.lab-canvas-kubernetes`; attempt
workspaces live inside the Canvas PVC under
`/home/openhands/workspace/neurogolf-research-lab`.

## Measurement ladder

Run concurrency progressively and stop when error rate or latency degrades:

1. one worker
2. two workers
3. four workers
4. six workers

Record time to first action, total duration, valid-candidate rate, CPU, memory,
PVC use, and cross-attempt interference. Use separate controller stores for
parallel processes because `FileResearchStore` is single-controller only.

The load harness enforces the 1–6 worker bound, creates a separate store and
remote workspace for every worker, samples the shared pod once per second, and
records immutable phase summaries:

```bash
./experiments/agent-canvas-kubernetes/scripts/run-load-phase.sh --live 1
./experiments/agent-canvas-kubernetes/scripts/run-load-phase.sh --live 2
./experiments/agent-canvas-kubernetes/scripts/run-load-phase.sh --live 4
./experiments/agent-canvas-kubernetes/scripts/run-load-phase.sh --live 6
```

Run each phase only after checking the previous phase for failures, pod
restarts, and unexpected memory growth. See
[`results-2026-07-25.md`](results-2026-07-25.md) for the first GKE results.

Run a sequential matched memory comparison:

```bash
./experiments/agent-canvas-kubernetes/scripts/run-matched-comparison.sh --live
```

Run the concurrent scheduling comparison. The naive arm gives six independent
controllers the same untouched campaign; the managed arm preassigns the six
tasks without overlap:

```bash
./experiments/agent-canvas-kubernetes/scripts/run-scheduled-batch.sh --live naive
./experiments/agent-canvas-kubernetes/scripts/run-scheduled-batch.sh --live managed
```

The task-assignment path uses the repeatable CLI option `--task-id`. This keeps
selection in the external controller and leaves validation inside the same
immutable attempt path used by every other run.

The matched deployment-model comparison holds managed task assignment, the
six-task campaign, concurrency, model family, timeout, contract, and validators
constant across Agent Canvas and a grouped Replicated runtime. See the
[public evidence](../../evidence/2026-07-25-agent-canvas-vs-replicated/README.md)
for the result and its deployment-boundary caveats.

## Cleanup

The namespace is intentionally not deleted automatically. Removing it deletes
the pilot workload and its PVC, so cleanup must be a deliberate operator action
after artifacts are captured.
