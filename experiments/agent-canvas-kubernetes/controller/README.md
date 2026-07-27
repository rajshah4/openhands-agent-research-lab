# Agent Canvas Kubernetes controller

This package moves the single research controller into the same Kubernetes
cluster as Agent Canvas. A CronJob wakes every 15 minutes, runs at most one
new validated attempt, writes the campaign ledger to a dedicated PVC, and
exits. Later jobs resume the same run from that ledger.

The controller is not an agent. It owns task selection, lifecycle recovery,
validation, and durable state. Agent Canvas owns the worker conversations.

## Safety and recovery properties

- `concurrencyPolicy: Forbid` and the file-store lock prevent two controller
  ticks from owning the ledger.
- Each tick runs at most one new attempt.
- An interrupted tick resumes the persisted run and conversation identifiers.
- The controller state uses a separate PVC; it does not mount the shared Agent
  Canvas workspace volume.
- The Canvas API key is supplied through a Kubernetes Secret.
- The controller pod has no Kubernetes API credential.

This is a single-controller design. Use a transactional lease store before
running multiple controller replicas.

## Build and deploy

Build the image from the repository root and push it to an accessible registry:

```bash
docker build \
  -f experiments/agent-canvas-kubernetes/controller/Dockerfile \
  -t REGION-docker.pkg.dev/PROJECT/REPOSITORY/research-controller:COMMIT .
docker push REGION-docker.pkg.dev/PROJECT/REPOSITORY/research-controller:COMMIT
```

Create the secret without placing its values in shell history:

```bash
kubectl -n agent-canvas-research create secret generic \
  agent-canvas-controller \
  --from-file=canvas-api-key=/path/to/private/api-key.txt \
  --from-literal=canvas-profile=PROFILE_NAME
```

Replace the `replace-me` image tag in a temporary copy of `kubernetes.yaml`,
apply it, and inspect the first job before allowing later ticks. The checked-in
CronJob is suspended so applying the example cannot launch work automatically:

```bash
kubectl apply -f /path/to/rendered-kubernetes.yaml
kubectl -n agent-canvas-research create job \
  --from=cronjob/agent-canvas-research-controller \
  agent-canvas-controller-canary
kubectl -n agent-canvas-research wait \
  --for=condition=complete job/agent-canvas-controller-canary \
  --timeout=25m
kubectl -n agent-canvas-research logs \
  job/agent-canvas-controller-canary
```

Verify one attempt, one worker conversation, deterministic validation, the
controller status file, and zero unexpected pod restarts. Enable the schedule
only after those checks:

```bash
kubectl -n agent-canvas-research patch cronjob \
  agent-canvas-research-controller \
  --type=merge \
  -p '{"spec":{"suspend":false}}'
```

## Live-test gates

1. One canary tick starts one run and records one attempt.
2. A separate tick resumes the same run ID and records the next sequence.
3. Delete a running controller pod after worker creation; the replacement tick
   must reattach rather than launch a duplicate.
4. Start two manual jobs simultaneously; one must be rejected by the store
   ownership lock or Kubernetes scheduling, with no duplicate attempt.
5. Confirm the CronJob stops launching workers when the attempt budget is
   complete.

The original GKE cluster was deleted after the earlier experiments. Recreating
it and running these gates requires an authenticated GCP session.
