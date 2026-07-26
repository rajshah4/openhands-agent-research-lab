# Files-first resilience experiment

Date: 2026-07-25  
Environment: local deterministic worker on macOS  
Scope: application-owned research ledger only; no OpenHands conversations

This experiment tests whether `FileResearchStore` can remain the production
ledger for a full 4,800-attempt NeuroGolf campaign. It separates three
questions that are easy to conflate:

1. Can the ledger retain and parse the expected record volume?
2. Can two controllers coordinate work through the ledger?
3. Can a stopped controller automatically resume its existing run?

## Exact commands

### 4,800-attempt ledger stress

```bash
mkdir -p /private/tmp/neurogolf-files-first-4800-20260725
/usr/bin/time -lp .venv/bin/python -m research_lab.cli run \
  --campaign examples/multi-family-campaign.json \
  --store /private/tmp/neurogolf-files-first-4800-20260725 \
  --worker local \
  --attempts 4800
```

All JSON files were then loaded with Python's standard JSON parser and attempt
IDs and sequence numbers were checked for uniqueness.

### Two competing controllers

The same command was launched twice concurrently against one store root:

```bash
.venv/bin/python -m research_lab.cli run \
  --campaign examples/multi-family-campaign.json \
  --store /private/tmp/neurogolf-files-first-dual-20260725 \
  --worker local \
  --attempts 100
```

### Controller termination and restart

```bash
.venv/bin/python experiments/files-first-resilience/run_slow_campaign.py \
  --campaign examples/multi-family-campaign.json \
  --store /private/tmp/neurogolf-files-first-crash-20260725 \
  --attempts 100 \
  --delay-seconds 0.25
```

The process was terminated after completed records were visible. The normal
CLI was then run again against the same store root for 100 attempts.

## Results

| Test | Result |
| --- | --- |
| Ledger volume | 4,800/4,800 completed attempts |
| JSON integrity | 24,013/24,013 JSON files parsed |
| Identifier integrity | 4,800 unique attempt IDs and 4,800 unique sequences |
| Total footprint | 24,014 files, 94 MB |
| Stress wall time | 569.78 seconds |
| Competing controllers | Both completed, but duplicated 100/100 task decisions and 100/100 candidates |
| Terminated run | 34 completed attempts remained intact; one additional selected attempt remained in lifecycle only |
| Restart behavior | Created a new run; 31 of the first 34 candidates were repeated |

The `/usr/bin/time -lp` wrapper exited nonzero because its final macOS
`sysctl kern.clockrate` probe was denied. The campaign itself completed,
produced its report, and passed the subsequent integrity scan.

## Interpretation

The file format is large enough for the planned campaign and atomic writes
preserve completed evidence across controller termination. The current runner,
however, is not yet a production recovery coordinator:

- it reparses the full attempt ledger before every attempt, producing
  quadratic read work;
- it has no cross-controller task claim or lease;
- it always creates a new run on restart instead of reconciling and resuming
  the interrupted run;
- an interrupted in-flight attempt is visible in lifecycle records but is not
  automatically classified or retried.

This does **not** prove that PostgreSQL is required for the current
single-controller campaign. It proves that the files-first implementation
needs an indexed in-memory view plus explicit single-controller resume and
reconciliation before that campaign is production-ready.

Use an application-owned transactional database when more than one controller
must claim work concurrently. Never use OpenHands internal database tables as
the research application's coordination contract.

