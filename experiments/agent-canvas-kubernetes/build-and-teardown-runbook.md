# Agent Canvas on GKE: build and teardown runbook

This runbook records the disposable GKE environment used for the Agent Canvas
experiments. It is intended to make the deployment reproducible without
retaining the original cloud resources or any credentials.

## What was built

- GCP project: `platform-team-sandbox-62793`
- Region: `us-central1`
- GKE Autopilot cluster: `agent-canvas-pilot`
- Kubernetes namespace and Helm release: `agent-canvas-research`
- One Agent Canvas StatefulSet replica
- Internal-only `ClusterIP` service on port 8000
- One 20 GiB `standard-rwo` persistent volume claim
- No Ingress and no Kubernetes RBAC permissions for the agent

The tested software versions were Agent Canvas chart `0.1.0`, Agent Canvas
`1.5.2`, Kubernetes `1.35`, and Helm `4.2.3`. Confirm current versions before
repeating the deployment.

Agent Canvas is single-tenant in this configuration. Conversations share the
pod, filesystem, shell, and PVC. Use it only for a trusted team and trusted
workloads.

## Prerequisites

The operator needs:

- a GCP identity allowed to create and delete GKE clusters in the project
- the GKE and Compute Engine APIs enabled
- `gcloud`, the GKE authentication plugin, `kubectl`, and Helm
- an Agent Canvas source checkout containing `helm/agent-canvas`
- a supported model-provider credential, entered privately after deployment

Never commit a provider key, pass it as a command-line argument, or source a
broad `.env` file as shell code. The deployment values contain no LLM
credential.

## Create the disposable cluster

The original cluster was created with:

```bash
gcloud container clusters create-auto agent-canvas-pilot \
  --project platform-team-sandbox-62793 \
  --region us-central1 \
  --release-channel regular \
  --network default \
  --labels=environment=ephemeral,purpose=agent-canvas-research,managed-by=codex

gcloud container clusters get-credentials agent-canvas-pilot \
  --project platform-team-sandbox-62793 \
  --region us-central1
```

Confirm that the current Kubernetes context names `agent-canvas-pilot` before
deploying:

```bash
kubectl config current-context
```

## Deploy and verify Agent Canvas

From the repository root:

```bash
export AGENT_CANVAS_CHART="$HOME/Code/agent-canvas/helm/agent-canvas"
./experiments/agent-canvas-kubernetes/scripts/preflight.sh
./experiments/agent-canvas-kubernetes/scripts/deploy.sh --live

kubectl -n agent-canvas-research rollout status \
  statefulset/agent-canvas-research
kubectl -n agent-canvas-research get pod,pvc,service
```

The version-controlled resource settings are in
[`values.yaml`](values.yaml). GKE Autopilot may increase resource requests to
meet its platform minimums; inspect the live pod when estimating cost.

## Access and provider setup

Start the private tunnel:

```bash
./experiments/agent-canvas-kubernetes/scripts/port-forward.sh
```

Open `http://127.0.0.1:8000/canvas/`. The loopback address is the local end of
the Kubernetes tunnel; Agent Canvas still runs in GKE. Create the LLM profile
in the private UI. The successful experiment used the Anthropic provider and
the Claude Haiku 4.5 model family. Do not put the credential in this repository.

## Reproduce the experiment ladder

Run the bounded pilot first, followed by progressively larger phases:

```bash
./experiments/agent-canvas-kubernetes/scripts/run-pilot.sh --live
./experiments/agent-canvas-kubernetes/scripts/run-load-phase.sh --live 1
./experiments/agent-canvas-kubernetes/scripts/run-load-phase.sh --live 2
./experiments/agent-canvas-kubernetes/scripts/run-load-phase.sh --live 4
./experiments/agent-canvas-kubernetes/scripts/run-load-phase.sh --live 6
```

Check errors, latency, memory, and pod restarts after each phase. Then run the
memory and scheduling comparisons:

```bash
./experiments/agent-canvas-kubernetes/scripts/run-matched-comparison.sh --live
./experiments/agent-canvas-kubernetes/scripts/run-scheduled-batch.sh --live naive
./experiments/agent-canvas-kubernetes/scripts/run-scheduled-batch.sh --live managed
```

Controller-side evidence is written beneath `.lab-canvas-kubernetes`.
Conversation workspaces are stored in the PVC beneath
`/home/openhands/workspace/neurogolf-research-lab`. The measured results and
accepted artifact paths are recorded in
[`results-2026-07-25.md`](results-2026-07-25.md).

## Cost and idle handling

At the resources observed during this experiment, the environment was
approximately $3.08 per day at public list prices, including the $0.10/hour
cluster management fee. If the project still has the applicable GKE free-tier
cluster credit, the remaining compute and storage were approximately
$0.66–$0.68 per day. Pricing and free-tier eligibility can change; recalculate
from the live pod requests and current
[GKE pricing](https://cloud.google.com/kubernetes-engine/pricing) and
[persistent disk pricing](https://cloud.google.com/compute/disks-image-pricing).

Agent conversations can be stopped when a batch completes, but an Autopilot
cluster, StatefulSet, and PVC still incur some idle cost. For a completed,
disposable experiment, cluster deletion is the cleanest stop condition.

## Tear down

Before deletion:

1. Ensure no experiment is active.
2. Confirm all required controller-side artifacts are present.
3. Record any results needed from the Canvas UI or PVC.
4. Resolve the exact project, region, and cluster name with a read-only list.

Deleting the cluster removes its namespace, workload, service, and PVC. That
cloud-resident conversation state is not recoverable unless it was separately
backed up. Local repository files and `.lab-canvas-kubernetes` evidence are not
removed.

```bash
gcloud container clusters list \
  --project platform-team-sandbox-62793 \
  --filter='name=agent-canvas-pilot'

gcloud container clusters delete agent-canvas-pilot \
  --project platform-team-sandbox-62793 \
  --region us-central1 \
  --quiet
```

Verify the list is empty:

```bash
gcloud container clusters list \
  --project platform-team-sandbox-62793 \
  --filter='name=agent-canvas-pilot'
```

Also verify that the disk formerly bound to the PVC has disappeared. During
the original teardown, the cluster deletion left the unattached 20 GiB disk
behind instead of garbage-collecting it. The operator resolved its exact name
and zone, confirmed that its `USERS` column was empty, and explicitly deleted
it:

```bash
gcloud compute disks list \
  --project platform-team-sandbox-62793 \
  --filter='name=pvc-300bb33e-8d77-4a97-a475-e032f97dcfbb' \
  --format='table(name,zone,status,sizeGb,users)'

gcloud compute disks delete \
  pvc-300bb33e-8d77-4a97-a475-e032f97dcfbb \
  --project platform-team-sandbox-62793 \
  --zone us-central1-f \
  --quiet
```

Do not reuse that disk name for a new deployment. Resolve and verify the exact
unattached disk created by each new PVC before deleting it.

The old kubeconfig context may remain locally after deletion. It is harmless
and was not treated as part of cloud teardown. Recreate the environment later
by repeating the create, credential, deploy, and private profile setup steps.
