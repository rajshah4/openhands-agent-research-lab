# Repository guidance

## Purpose

This repository coordinates bounded OpenHands worker conversations across
repeated, deterministically validated experiments. OpenHands owns execution;
this application owns scheduling, validation, attempt records, and promotion of
evidence-backed lessons.

## Commands

Run tests:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Run the offline campaign:

```bash
PYTHONPATH=src python3 -m research_lab.cli run \
  --campaign examples/graph-coloring-campaign.json \
  --store .lab \
  --worker local
```

Compile-check Python:

```bash
PYTHONPATH=src python3 -m compileall -q src tests
```

## Invariants

- Keep deterministic validation separate from agent claims.
- Keep persistence behind the `ResearchStore` contract.
- Treat `FileResearchStore` as single-controller only.
- Use supported OpenHands V1 app-conversation and event APIs.
- Never write to OpenHands internal database tables.
- Never print or persist API keys, session keys, credentials, or environment
  dumps.
- Live commands must require an explicit `--live` flag and bounded timeouts.
- Record immutable start-task, conversation, sandbox, run, and attempt IDs.
- Preserve failed attempts and lifecycle evidence; do not infer success from a
  commit, candidate, or partial response.
- Promote a lesson only after an independent validator confirms a strictly
  improving candidate.

## Scope

Stage 1 supports graph-coloring tasks and a single controller. Read
`docs/design.md` and `docs/live-validation.md` before expanding the scheduler,
storage backend, or Enterprise integration.
