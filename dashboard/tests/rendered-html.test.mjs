import assert from "node:assert/strict";
import { stat } from "node:fs/promises";
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
  assert.match(html, />Planner</);
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
