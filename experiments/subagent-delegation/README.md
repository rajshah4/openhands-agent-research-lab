# SDK subagent delegation on Replicated

This experiment checks whether the tested OpenHands Enterprise/Replicated
profile exposes SDK TaskToolSet delegation to V1 app conversations.

It is deliberately separate from:

- external orchestration that creates first-class Enterprise conversations;
- Agent Canvas delegation that creates child Canvas conversations through the
  agent-server API; and
- Enterprise sandbox grouping, which changes runtime placement without
  changing conversation identity.

Read [`results-2026-07-26.md`](results-2026-07-26.md) before using SDK
subagents on this installation. The user setting saved successfully, but the
launched profile did not advertise TaskToolSet in the measured run.

The safe inspector in `scripts/inspect-subagent-run.py` pages backward through
the event stream, ignores streaming deltas, and reports only lifecycle,
metrics, and task-event summaries. It does not print prompts, responses, or
credentials.

Run the bounded capability gate before any larger comparison:

```bash
PYTHONPATH=src python3 \
  experiments/subagent-delegation/scripts/run-enterprise-capability.py \
  --live \
  --env-file /path/to/private/enterprise.env \
  --output /tmp/enterprise-tasktool-result.json
```

The gate creates one parent, requires one native task action and observation,
records only sanitized metadata, and pauses the sandbox. Do not run the
two- or four-child load tests unless this gate reports `status: passed`.
