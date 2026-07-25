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

test("renders the research organization dashboard", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /<title>NeuroGolf Lab \| OpenHands Research Organization<\/title>/i);
  assert.match(html, /From a swarm of agents to a learning organization/);
  assert.match(html, /Rajistics capacity/);
  assert.match(html, /Same budget\. Different organization/);
  assert.match(html, /Claims do not become memory\. Evidence does/);
  assert.doesNotMatch(html, /codex-preview|Your site is taking shape/);
});
