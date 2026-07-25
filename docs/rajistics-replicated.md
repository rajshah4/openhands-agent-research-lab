# Rajistics Replicated compatibility target

The first live compatibility target is the Rajistics OpenHands Enterprise
deployment installed through Replicated.

## Recorded environment

The local installation worklog dated 2026-07-20 records:

- OpenHands Enterprise version: `0.24.0`
- Active application host after blue/green cutover:
  `https://app.replicated.rajistics.com`
- Replicated Embedded Cluster installer:
  `v2.19.2+k8s-1.36`
- Kubernetes: `v1.36.1+k0s.0`

The temporary `replicated-next.rajistics.com` hostname was replaced during
cutover and is not the default target.

## Configuration

Do not commit credentials. Configure the supported V1 app-server API:

```bash
export OPENHANDS_BASE_URL="https://app.replicated.rajistics.com"
export OPENHANDS_API_KEY="..."
```

The implementation accepts `OPENHANDS_API_KEY_ORG` and `OH_API_KEY` as
compatibility aliases, but documentation uses `OPENHANDS_API_KEY`.

The CLI can also read a `KEY=value` file with `--env-file`. It parses the file
as data and does not execute it as a shell script. This is the preferred route
for the existing Rajistics install environment.

## Safe staged validation

1. Run all offline tests.
2. Call `preflight --worker openhands` to test `/api/v1/users/me`.
3. Confirm the repository exists and the configured branch is visible through
   the Enterprise integration.
4. Override the campaign to one attempt.
5. Run with `--worker openhands --live`.
6. Confirm the child appears in the Enterprise UI.
7. Confirm start-task, sandbox, conversation, terminal state, final contract,
   event counts, candidate score, and UI link appear in the attempt artifact.
8. Run a second attempt only after the first lifecycle is correct.
9. Confirm the `sandbox_pause_requested` and `sandbox_paused` lifecycle events.

Until this repository is published, the smoke test can use the existing public
demo repository without modifying it:

```bash
PYTHONPATH=src python3 -m research_lab.cli run \
  --campaign examples/graph-coloring-campaign.json \
  --worker openhands \
  --repository rajshah4/openhands-multi-agent-demo \
  --branch main \
  --attempts 1 \
  --base-url https://app.replicated.rajistics.com \
  --env-file /path/to/install_replicate/.env \
  --live
```

## Known 0.24.0 behavior to preserve

- App-conversation creation is asynchronous and returns a start-task ID.
- The conversation ID arrives when the start task reaches `READY`.
- Conversation list state and durable event state can converge at different
  times.
- A paused sandbox with an empty execution status may still have a durable
  terminal event.
- Final-response indexing can lag terminal state and needs a bounded grace
  period.

## Explicit non-actions

- Do not query or write the OpenHands PostgreSQL database during Stage 2.
- Do not print session keys, API keys, environment dumps, or full event
  payloads.
- Do not create more than two concurrent workers.
- Do not start a live batch when seven or more runtime sandboxes are active on
  the approximately ten-runtime Rajistics demo instance.
- Pause every completed lab sandbox by default. Retain one only for an explicit,
  bounded debugging session.
- Do not install dependencies inside timed worker runs.
