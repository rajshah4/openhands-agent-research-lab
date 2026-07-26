# Native TaskToolSet delegation in Agent Canvas

This experiment separates two different ways to delegate work with Agent
Canvas:

1. a controller creates another first-class Canvas conversation through the
   Agent Server API; and
2. one OpenHands parent invokes the native `task` tool, which runs a subagent
   inside the parent's Agent Server process.

The first pattern was already used by the Agent Canvas scheduling experiments.
The result in [`results-2026-07-26.md`](results-2026-07-26.md) validates the
second pattern and includes a matched four-task comparison of sequential
subagents, parallel subagents and first-class conversations. The normalized
measurements are also available in
[`deeper-comparison-2026-07-26.json`](deeper-comparison-2026-07-26.json).
The controlled one-bad-child robustness run is preserved in
[`failure-injection-2026-07-26.json`](failure-injection-2026-07-26.json).

The OpenHands Enterprise/Replicated settings-propagation issue is deliberately
kept separate. A Cloud comparison and an OHE regression ticket are deferred
until the deployment analysis is complete.
