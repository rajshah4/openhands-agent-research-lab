# Enterprise fewest-conversations capacity pilot

Date: 2026-07-25

Environment:

- Rajistics OpenHands Enterprise, installed through Replicated
- Enterprise server image:
  `images.r9.all-hands.dev/proxy/openhands/ghcr.io/openhands/enterprise-server:cloud-1.46.2`
- OpenHands SDK reported by the deployed image: `1.36.0`
- User sandbox grouping strategy: `FEWEST_CONVERSATIONS`
- Maximum conversations per sandbox: `4`
- User-visible runtime limit: `10`
- Controller launch lock: `7` active user-visible sandboxes

## Result

The first four first-class Enterprise conversations were assigned to the same
sandbox. A fifth conversation was then started after that sandbox reached the
configured limit. OpenHands automatically created a second sandbox rather than
placing a fifth conversation in the full sandbox.

| Sequence | Task | Conversation | Sandbox | Validation |
| ---: | --- | --- | --- | --- |
| 1 | graph coloring | [b53ba136](https://app.replicated.rajistics.com/conversations/b53ba136576343ecade1a21743106b07) | `7leaYOpahJUNk1y4PK8Gyh` | valid, score 2 |
| 2 | graph coloring | [95bbfd7b](https://app.replicated.rajistics.com/conversations/95bbfd7bf12b4488b6bb2f92174e5f4c) | `7leaYOpahJUNk1y4PK8Gyh` | valid, score 3 |
| 3 | set cover | [531e86a8](https://app.replicated.rajistics.com/conversations/531e86a8e87b406894a04daf1ec97412) | `7leaYOpahJUNk1y4PK8Gyh` | valid, score 2 |
| 4 | set cover | [2249f686](https://app.replicated.rajistics.com/conversations/2249f68632b247ddbd442bb2b9042d5d) | `7leaYOpahJUNk1y4PK8Gyh` | valid, score 2 |
| 5 | graph coloring | [ed2942cf](https://app.replicated.rajistics.com/conversations/ed2942cf27344d5182ea70590b36d843) | `1KiDBcML3xeGFhAtHoIgZg` | valid, score 2 |

Every conversation had a distinct start-task ID, conversation ID, event
history, and workspace path. All five candidates passed independent
deterministic validation. No duplicate candidate was recorded in either run.

## Capacity behavior

| Checkpoint | User-visible active sandboxes | Running physical runtime pods | Unhealthy pods |
| --- | ---: | ---: | ---: |
| Before the pilot | 0 | 1 warm runtime | 0 |
| First grouped sandbox active | 1 | 1, then 2 after warm-spare replenishment | 0 |
| Fifth conversation started | 2 | bounded below the installation limit | 0 |
| Both experiment sandboxes paused | 0 | 1 warm runtime | 0 |

The runtime service replenished a separate warm spare after a runtime was
claimed. Physical runtime pod count can therefore be one greater than the
number of user-visible active experiment sandboxes.

## Lifecycle

Individual attempts used the grouped-pool `keep sandbox` behavior. After all
five conversations reached terminal state, the controller paused both
sandboxes once through the supported V1 sandbox API:

- `7leaYOpahJUNk1y4PK8Gyh`: `PAUSED`
- `1KiDBcML3xeGFhAtHoIgZg`: `PAUSED`

The final cluster check found one healthy warm runtime and zero unhealthy pods.

## Deployment gap

The grouping strategy is a supported personal setting and was saved through
the Enterprise UI.

The per-sandbox conversation limit exists in the deployed OpenHands
configuration model but is not exposed in the Enterprise UI or the current
Replicated application settings. For this pilot it was set on the `openhands`
deployment with:

```text
OH_APP_CONVERSATION_MAX_NUM_CONVERSATIONS_PER_SANDBOX=4
```

The deployment rolled out successfully and the running pod loaded the value.
This direct Kubernetes override is a pilot workaround, not durable Replicated
configuration: an application upgrade or redeploy may replace it. A production
installation should expose the limit in Replicated configuration or apply it
through a version-controlled deployment overlay.

## Conclusion

This test demonstrates the useful production primitive:

- first-class, separately auditable conversations;
- bounded runtime reuse for trusted agents;
- automatic sandbox rollover at a configured conversation count;
- deterministic external validation;
- explicit pool-level cleanup.

It does not make OpenHands resource-aware. The limit counts stored
conversations, not active CPU, memory, or disk pressure. A production pool
controller still needs leases, live-concurrency limits, draining, health
reconciliation, and a one-sandbox-per-conversation fallback for untrusted work.
