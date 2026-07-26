# 400-task orchestration simulation

This experiment tests whether the research ledger and scheduler remain correct
at the shape of the NeuroGolf competition: 400 task owners and 12 attempts per
task.

It is a deterministic infrastructure test, not a Kaggle or model benchmark.

```bash
python experiments/portfolio-scale/run_400_task_comparison.py \
  --store /tmp/neurogolf-400-task-comparison
```

The matched run executes 4,800 attempts per arm. It verifies task coverage,
balanced ownership, unique attempt IDs and sequences, validated-memory
retrieval, and comparison aggregation.

Measured on 2026-07-26:

- 400/400 tasks received exactly 12 attempts in both arms;
- 9,600 attempts completed in 16.01 seconds;
- the evidence store occupied 192 MB;
- the managed deterministic arm reached normalized quality 1.0000 versus
  0.6675 for naive;
- quality AUC was 0.9582 versus 0.6397.

The quality difference is intentionally encoded in the deterministic worker so
the measurement path has a known signal. It is not evidence that an LLM would
produce the same improvement.
