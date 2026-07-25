# Matched naive-versus-managed comparison

The comparison command runs two isolated arms with the same task set, attempt
budget, worker backend, repository, branch, and model configuration.

- **Naive** uses round-robin scheduling and supplies no cross-attempt memory.
- **Managed** schedules for coverage and weak scores, then supplies only
  independently validated lessons relevant to the selected task.

Each arm has its own store. A lesson from one arm cannot leak into the other.
This is essential for a defensible comparison and is also why the filesystem
backend remains useful: the evidence is inspectable without coupling the demo
to OpenHands internal tables or requiring a separate database.

Run the deterministic offline comparison:

```bash
PYTHONPATH=src python3 -m research_lab.cli compare \
  --campaign examples/graph-coloring-campaign.json \
  --store .lab-comparison \
  --worker local
```

The report includes:

- problems solved and task coverage
- final normalized solution quality
- quality AUC, which rewards reaching good solutions earlier in the budget
- duplicate candidates
- improvement rate per attempt

For tasks with a known target, normalized quality is `target / best`, capped at
one. Unsolved tasks contribute zero. Quality AUC is the mean normalized quality
after each attempt, so it distinguishes two arms that finish at the same score
but learn at different rates.

The bundled offline worker deliberately models one narrow memory effect. Without
a validated lesson it uses input-order greedy coloring. With the promoted
high-degree-first lesson it switches ordering. The adversarially ordered path
task makes that behavior deterministic and testable.

This is control-plane validation, not a claim about language-model performance.
A live result is evidence only when both OpenHands arms use the same model,
timeouts, task definitions, and attempt budget.

## Current offline result

With the bundled three-task campaign and four attempts per arm:

| Metric | Naive | Managed |
| --- | ---: | ---: |
| Problems solved | 3 | 3 |
| Coverage | 1.000 | 1.000 |
| Normalized solution quality | 0.889 | 1.000 |
| Quality AUC | 0.667 | 0.750 |
| Duplicate experiments | 1 | 1 |

The quality gain shows that validated memory is reaching later workers. The
duplicate tie exposes the next gap: the scheduler does not yet describe prior
candidates to workers or explicitly reward experiment diversity.
