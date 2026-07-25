# Multi-family live milestone

Date: 2026-07-25  
Environment: Rajistics OpenHands Enterprise 0.24.0

## What ran

- 12-task offline matched comparison across graph coloring, set cover, and bin
  packing
- 12 live OpenHands conversations in a six-task matched comparison
- 2 live OpenHands conversations in the exact-item-ID regression
- one active worker at a time, launch lock at seven, automatic pause after every
  attempt

The public-safe machine-readable ledger is in `evidence.json`. It retains
attempt, scheduler, validation, memory, conversation, and lifecycle identifiers
without raw prompts, final responses, credentials, or candidate content.

## Results

### Offline 12-task comparison

| Metric | Naive | Managed |
| --- | ---: | ---: |
| Problems solved | 12/12 | 12/12 |
| Normalized quality | 0.670 | 0.889 |
| Quality AUC | 0.394 | 0.479 |

The offline worker is deterministic instrumentation. This result verifies that
the scheduler, isolation, validator registry, promotion gate, and retrieval path
can produce a measurable memory effect; it is not a claim about model quality.

### Live six-task comparison

| Metric | Naive | Managed |
| --- | ---: | ---: |
| Problems solved | 6/6 | 4/6 |
| Normalized quality | 1.000 | 0.667 |
| Quality AUC | 0.583 | 0.500 |

The two managed failures were independently rejected because their candidates
used placeholder IDs (`item-a`) instead of task IDs (`a`). No lesson from either
invalid attempt was promoted. This was a prompt example defect, not evidence
that retrieved memory reduced solution quality.

### Live regression after the prompt fix

Both corrected candidates validated at the optimal score and both sandboxes
paused:

- [pack-alpha conversation](https://app.replicated.rajistics.com/conversations/832cdfc8ec1a4eeaa2749499ce38a43b)
- [pack-beta conversation](https://app.replicated.rajistics.com/conversations/2350802c7cd5451e99dd6e2df5d2c212)

The second attempt retrieved the validated lesson promoted by the first.

## Capacity outcome

The run began with zero active user-visible sandboxes. Across 14 new live
conversations, runtime concurrency remained at one. The final preflight reported
zero active, 112 paused, and six historical missing sandboxes. No invalid
candidate entered shared memory.

## Interpretation

This milestone establishes that the organization can preserve structured
conversation metadata, validate three task families, reject bad candidates,
withhold invalid memory, diagnose a prompt defect, verify the fix, and release
runtime capacity repeatedly.

It does not yet establish that managed memory improves live model performance.
The next experiment should use harder instances and three matched seeds while
keeping the same fixed budget and capacity controls.
