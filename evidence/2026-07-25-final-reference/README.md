# Final reference evidence

Date: 2026-07-25

This directory is the public-safe result of three matched live comparisons on
the Rajistics Replicated OpenHands Enterprise 0.24.0 installation.

## Result

| Metric | Naive | Managed |
| --- | ---: | ---: |
| Replicates | 3 | 3 |
| Attempts | 18 | 18 |
| Independently valid | 18/18 | 18/18 |
| Problems solved | 18/18 | 18/18 |
| Mean normalized quality | 1.000 | 1.000 |
| Mean quality AUC | 0.583 | 0.583 |
| Retrieved validated lessons | 0 | 9 |
| Duplicate experiments | 0 | 0 |

All 36 OpenHands conversations completed, all 36 candidates passed the
family-specific deterministic validator, no invalid lesson was promoted, and
all 36 sandboxes were verified `PAUSED`. The final preflight observed zero
active sandboxes and an open capacity gate.

Contract transport remained an observable compatibility issue: 2 responses
were exact JSON, 21 used the bounded fenced-JSON fallback, and 13 used the
bounded trailing-JSON fallback. Every accepted fallback still had to match the
five-field contract and pass independent validation.

## What this proves

- A single external controller can safely coordinate repeated OpenHands
  conversations while preserving conversation, run, attempt, sandbox,
  validation, and lesson lineage.
- Validated lessons can cross conversation boundaries through the file ledger;
  neither an external database nor OpenHands internal database access is
  required for this single-controller topology.
- Capacity protection works: launches are gated, execution is sequential on
  the small installation, and completed sandboxes release capacity
  automatically.
- Failures remain useful evidence. An earlier live run exposed placeholder ID
  aliasing in the managed prompt, and a two-conversation regression plus these
  36 attempts verified the fix.

## What this does not prove

These six live tasks were intentionally small. Both organizations reached every
known target, so this result does not demonstrate a live quality advantage for
managed scheduling. The controlled 12-task offline mechanism benchmark did
separate the policies (`0.670` naive versus `0.889` managed normalized
quality), but the next live gate must use harder tasks where retrieved
techniques can affect the candidate.

This run was deliberately single-controller and one-conversation-at-a-time. It
does not test concurrent ownership. Add an application-owned PostgreSQL store
only when multiple controllers or tenants make atomic claims, leases, and
authorization necessary.

## Files

- `results.json` is the aggregate, machine-readable conclusion and capacity
  snapshot.
- `seed-1.json`, `seed-2.json`, and `seed-3.json` contain sanitized attempts,
  validator results, transport status, lesson provenance, conversation links,
  and verified pause state.

The raw local ledgers are intentionally not published. The evidence exporter
removes secret-bearing metadata and omits raw worker responses while retaining
the identifiers and outcomes required for audit.
