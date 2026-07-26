import assert from "node:assert/strict";
import { readFile, stat } from "node:fs/promises";
import test from "node:test";

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request("http://localhost/", {
      headers: { accept: "text/html" },
    }),
    {
      ASSETS: {
        fetch: async () => new Response("Not found", { status: 404 }),
      },
    },
    {
      waitUntil() {},
      passThroughOnException() {},
    },
  );
}

test("renders the NeuroGolf experiment for a new reader", async () => {
  const illustration = await stat(
    new URL("../public/sandbox-placement.png", import.meta.url),
  );
  assert.ok(illustration.size > 0);

  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(
    html,
    /<title>NeuroGolf with OpenHands \| Reproducing a Kaggle multi-agent workflow<\/title>/i,
  );
  assert.match(html, /NeuroGolf required solving and optimizing 400 separate ARC tasks/i);
  assert.match(html, /NeuroGolf 2026 was a Kaggle competition/);
  assert.match(html, /The rules did not require agents/);
  assert.match(html, />Overview</);
  assert.match(html, />Deployment</);
  assert.match(html, />Robustness</);
  assert.match(html, />Evidence</);
  assert.match(html, />Scaling</);
  assert.match(html, /What the Kaggle competition required/);
  assert.match(html, /400 independent implementation problems/);
  assert.match(html, /Why teams used multiple agents/);
  assert.match(html, /The 400 tasks could be worked on in parallel/);
  assert.match(html, /12 attempts for each of 400 tasks/);
  assert.match(html, /The same control path can run NeuroGolf workers/);
  assert.match(html, /This test focused on multi-agent orchestration/);
  assert.match(html, /OpenHands can orchestrate this campaign as the worker execution layer/);
  assert.match(html, /multi-controller and API load tests/);
  assert.doesNotMatch(html, /Supporting live-systems check|These are real OpenHands runs/);
  assert.doesNotMatch(html, /full competition solver is not/);
  assert.doesNotMatch(html, /codex-preview|Your site is taking shape/);
});

test("includes the Agent Canvas deployment evidence", async () => {
  const source = await readFile(
    new URL("../app/research-dashboard.tsx", import.meta.url),
    "utf8",
  );
  const snapshot = await readFile(
    new URL("../data/snapshot.json", import.meta.url),
    "utf8",
  );

  assert.match(source, /We measured setup time, shared-agent load, model cost, and estimated cluster cost/);
  assert.match(source, /These are resource-based estimates, not a cloud invoice/);
  assert.match(source, /Those waiting jobs\s+did not have sandboxes yet/);
  assert.match(source, /Removing the queue increased contention and did not produce a wall-time win/);
  assert.doesNotMatch(source, /simultaneous sandbox(?:es)? · .* queued/);
  assert.match(source, /Four ways to organize agent execution/);
  assert.match(source, /Enterprise isolated/);
  assert.match(source, /Enterprise grouped/);
  assert.match(source, /Agent Canvas/);
  assert.match(source, /SDK subagents/);
  assert.match(source, /Native TaskToolSet delegation passed in Agent Canvas/);
  assert.match(source, /Native TaskToolSet worked in Agent Canvas; the Replicated profile still omitted it/);
  assert.match(source, /A native code-explorer child performed the delegated work/);
  assert.match(source, /Validate the same contract separately on OpenHands\s+Cloud/);
  assert.match(source, /Choosing an execution pattern/);
  assert.match(source, /NeuroGolf scaling planner/);
  assert.match(source, /One sandbox per active agent/);
  assert.match(source, /Four agents per shared sandbox/);
  assert.match(source, /These estimates scale with the campaign, not sandbox placement/);
  assert.match(source, /CPU and memory still require an ONNX workload benchmark/);
  assert.doesNotMatch(source, /Placement proven|Density option|Worker cluster/);
  assert.match(snapshot, /"clusterProvisionMinutes": 8/);
  assert.match(snapshot, /"wallSeconds": 113/);
  assert.match(snapshot, /"effectiveThroughput": 153\.55/);
  assert.match(snapshot, /"executionSeconds": 204\.294/);
  assert.match(snapshot, /"modelCost": 0\.38482224/);
  assert.match(snapshot, /"taskToolAdvertised": false/);
  assert.match(snapshot, /"agentCanvasTaskTool"/);
  assert.match(snapshot, /"wallSeconds": 26\.272/);
  assert.match(snapshot, /"taskSeconds": 10\.214/);
  assert.match(snapshot, /"totalModelCost": 0\.1321128/);
  assert.match(snapshot, /"childModelCost": 0\.0195816/);
});
