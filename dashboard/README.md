# NeuroGolf Lab dashboard

The dashboard turns the research ledger into an operator-facing story:

- live capacity and launch policy for the Rajistics OpenHands instance
- matched naive-versus-managed results
- conversation-level provenance and sandbox lifecycle
- promoted lessons with their evidence chain
- resolved incidents and the next proof gates
- an adjustable full-competition planner for all 400 NeuroGolf tasks

The initial release renders a checked-in snapshot from `data/snapshot.json`. This
keeps the public dashboard read-only and deployable without granting it access to
the OpenHands control plane. A later milestone can replace the snapshot during a
release build or expose a narrowly scoped read API.

## Run locally

Requires Node.js `>=22.13.0`.

```bash
npm install
npm run dev
```

## Verify

```bash
npm run lint
npm test
```

`npm test` performs a production Sites build and checks the rendered dashboard
contract. The app is hosted with OpenAI Sites using the project ID in
`.openai/hosting.json`.
