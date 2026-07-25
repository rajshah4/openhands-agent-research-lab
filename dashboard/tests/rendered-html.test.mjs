import assert from "node:assert/strict";
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
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(
    html,
    /<title>NeuroGolf with OpenHands \| A public multi-agent experiment<\/title>/i,
  );
  assert.match(html, /Can coding agents learn from each other/);
  assert.match(html, /A Kaggle team used many agents/);
  assert.match(html, /I ran the same six problems two ways, three times/);
  assert.match(html, /The six live problems were too easy/);
  assert.match(html, /This reproduces the multi-agent research setup/);
  assert.match(html, /One Enterprise sandbox per agent/);
  assert.match(html, /Many agents on one Agent Canvas/);
  assert.match(html, /Embed the OpenHands SDK/);
  assert.match(html, /Pilot tested: 2 at once/);
  assert.match(html, /These are real OpenHands runs/);
  assert.doesNotMatch(html, /codex-preview|Your site is taking shape/);
});
