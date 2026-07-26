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
    /<title>NeuroGolf with OpenHands \| Multi-agent patterns on Replicated<\/title>/i,
  );
  assert.match(html, /reproduced the organization behind a 400-task agent campaign/i);
  assert.match(html, /NeuroGolf teams used many coding agents/);
  assert.match(html, />Scale</);
  assert.match(html, />Deployment</);
  assert.match(html, />Robustness</);
  assert.match(html, />Planner</);
  assert.match(html, /One campaign coordinated 400 task owners and 9,600 attempts/);
  assert.match(html, /Supporting live-systems check/);
  assert.match(html, /verified the loop with real OpenHands agents/);
  assert.match(html, /not a quality or generalization result/);
  assert.match(html, /The main scale result is a matched campaign/);
  assert.match(html, /Separate runtime for each agent/);
  assert.match(html, /One runtime, four active agents/);
  assert.match(html, /One runtime, six active agents/);
  assert.match(html, /Recommended starting point/);
  assert.match(html, /FEWEST_CONVERSATIONS/);
  assert.match(html, /Total model cost/);
  assert.match(html, /across all 18 accepted attempts/);
  assert.match(html, /4 agents in 4 sandboxes; 2 jobs queued/);
  assert.match(html, /6 agents in 1 sandbox; no jobs queued/);
  assert.match(html, /These are real OpenHands runs/);
  assert.match(html, /Every one of 400 task owners received exactly 12 attempts/);
  assert.match(html, /I killed the controller after OpenHands started the work/);
  assert.match(html, /Four ways to use OpenHands/);
  assert.match(html, /We reproduced the research organization, not a leaderboard score/);
  assert.doesNotMatch(html, /codex-preview|Your site is taking shape/);
});
