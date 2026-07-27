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
  const deploymentOptions = await stat(
    new URL("../public/deployment-options.png", import.meta.url),
  );
  assert.ok(illustration.size > 0);
  assert.ok(deploymentOptions.size > 0);

  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(
    html,
    /<title>NeuroGolf with OpenHands \| Reproducing a Kaggle multi-agent workflow<\/title>/i,
  );
  assert.match(html, /Multi-agent orchestration for the NeuroGolf workload/i);
  assert.match(html, /NeuroGolf 2026 was a Kaggle competition/);
  assert.match(html, /The rules did not require agents/);
  assert.match(html, />Overview</);
  assert.match(html, />Controller</);
  assert.match(html, />Execution</);
  assert.match(html, />Memory</);
  assert.match(html, />Results</);
  assert.match(html, />Scaling</);
  assert.doesNotMatch(html, />Deployment|>Robustness|>How we tested/);
  assert.match(html, /What the Kaggle competition required/);
  assert.match(html, /400 independent implementation problems/);
  assert.match(html, /The three parts of a multi-agent system/);
  assert.match(html, /Controller, execution, and memory solve different problems/);
  assert.match(html, /Why teams used multiple agents/);
  assert.match(html, /The 400 tasks could be worked on in parallel/);
  assert.match(html, /several ways to coordinate, execute, and retain state across agent work/);
  assert.match(html, /Four controller approaches/);
  assert.match(html, /Four execution structures/);
  assert.match(html, /The same control path can run NeuroGolf workers/);
  assert.match(html, /This test focused on multi-agent orchestration/);
  assert.match(html, /OpenHands can provide the agent execution\s+layer for this workflow/);
  assert.match(html, /OpenHands ran the agents; our application ran the research organization/);
  assert.match(html, /most of the organizational intelligence was application code outside OpenHands/);
  assert.match(html, /Competition teams built persistent research pipelines around general coding agents/);
  assert.match(html, /A persistent research pipeline/);
  assert.match(html, /Winning-team pipeline/);
  assert.match(html, /A custom resumable Codex scheduler/);
  assert.match(html, /External task ownership prevented agent drift/);
  assert.match(html, /it can replace custom process,\s+sandbox, conversation, event, pause, and operator-visibility glue/);
  assert.match(html, /multi-controller and API load tests/);
  assert.doesNotMatch(html, /Supporting live-systems check|These are real OpenHands runs/);
  assert.doesNotMatch(html, /full competition solver is not/);
  assert.doesNotMatch(html, /codex-preview|Your site is taking shape/);
  assert.doesNotMatch(html, />Evidence</);
});

test("organizes the evidence around controller, execution, and memory", async () => {
  const source = await readFile(
    new URL("../app/research-dashboard.tsx", import.meta.url),
    "utf8",
  );
  const snapshot = await readFile(
    new URL("../data/snapshot.json", import.meta.url),
    "utf8",
  );

  assert.match(source, /Agent Canvas: a shared agent service for one trusted team/);
  assert.match(source, /Unlike Enterprise conversations, Canvas does not create a separate\s+sandbox boundary for each agent/);
  assert.match(source, /Lower runtime overhead for trusted work/);
  assert.match(source, /The application owns the shared boundary/);
  assert.match(source, /Those waiting jobs\s+did not have sandboxes yet/);
  assert.match(source, /Removing the queue increased contention and did not produce a wall-time win/);
  assert.doesNotMatch(source, /simultaneous sandbox(?:es)? · .* queued/);
  assert.match(source, /Four ways to organize agent execution/);
  assert.match(source, /Enterprise isolated/);
  assert.match(source, /Enterprise grouped/);
  assert.match(source, /Agent Canvas/);
  assert.match(source, /Parent with subagents/);
  assert.match(source, /src="\/deployment-options\.png"/);
  assert.match(source, /operational tradeoffs among the four structures/);
  assert.ok(
    source.indexOf("operational tradeoffs among the four structures") <
      source.indexOf("Agent Canvas: a shared agent service"),
  );
  assert.ok(
    source.indexOf("<table className=\"agent-table\">") <
      source.indexOf("Agent Canvas: a shared agent service"),
  );
  assert.match(source, /Enterprise: comparing isolated and grouped conversations/);
  assert.match(source, /Replicated was the deployment method, not a\s+separate orchestration pattern/);
  assert.match(source, /Parent and subagents: using TaskToolSet to coordinate specialist children/);
  assert.match(source, /A native code-explorer child performed the delegated work/);
  assert.match(source, /same four research tasks in three execution structures/);
  assert.match(source, /33\.4% faster than sequential delegation/);
  assert.match(source, /Four first-class Canvas conversations/);
  assert.match(source, /Recommended hybrid/);
  assert.match(source, /One invalid child did not prevent its three siblings from completing/);
  assert.match(source, /Orchestration does not require Enterprise/);
  assert.match(source, /Enterprise provides operational boundaries/);
  assert.match(source, /A conversation is a unit of ownership and recovery/);
  assert.match(source, /Need Enterprise\?/);
  assert.match(source, /Failure and retry scope/);
  assert.match(source, /Manageability/);
  assert.match(source, /Enterprise implementation note/);
  assert.match(source, /Decision guide: use trust and operational requirements to choose the boundary/);
  assert.doesNotMatch(source, /Six-agent load phase/);
  assert.doesNotMatch(source, /Peak shared pod/);
  assert.doesNotMatch(source, /Replicated measurements/);
  assert.doesNotMatch(source, /OHE side note/);
  assert.doesNotMatch(source, /Native TaskToolSet worked in Agent Canvas; the Replicated profile still omitted it/);
  assert.match(source, /The controller turns individual agent runs into one managed campaign/);
  assert.match(source, /One management loop/);
  assert.match(source, /One controller can use files and Git/);
  assert.match(source, /Several controllers need database leases/);
  assert.match(source, /Do not use OpenHands internal\s+PostgreSQL tables as the campaign API/);
  assert.match(source, /Four control patterns/);
  assert.match(source, /Bounded polling batch/);
  assert.match(source, /Scheduled controller tick/);
  assert.match(source, /loads durable campaign state/);
  assert.match(source, /runs one bounded unit of work/);
  assert.match(source, /Later triggers continue the same campaign/);
  assert.match(source, /A campaign may contain hundreds of queued tasks/);
  assert.match(source, /Git preserved the campaign queue, task claims/);
  assert.match(source, /Persistent reconciler/);
  assert.match(source, /Event-triggered tick/);
  assert.match(source, /Design option, not yet tested/);
  assert.match(source, /Test results and current limits/);
  assert.match(source, /The completed tests cover bounded batches, an unattended hourly\s+campaign/);
  assert.match(source, /It was not one uninterrupted 20-attempt run/);
  assert.match(source, /hourly campaign ticks/);
  assert.match(source, /artifact outlived its sandbox/);
  assert.match(source, /There is no established endurance limit/);
  assert.match(source, /Duplicate, delayed, missed, and out-of-order events remain\s+untested/);
  assert.match(source, /Reusable implementations/);
  assert.match(source, /View the reusable tick/);
  assert.match(source, /View the automation package/);
  assert.match(source, /View the polling supervisor/);
  assert.match(source, /Controls used/);
  assert.doesNotMatch(source, /What passed, and where we reduced concurrency/);
  assert.doesNotMatch(source, /Controls applied before, during, and after each agent run/);
  assert.doesNotMatch(source, />Control<\/span>/);
  assert.doesNotMatch(source, /Honest boundary/);
  assert.doesNotMatch(source, /Native subagents · inside a cell/);
  assert.match(source, /NeuroGolf scaling planner/);
  assert.match(source, /One sandbox per active agent/);
  assert.match(source, /Four agents per shared sandbox/);
  assert.match(source, /These estimates scale with the campaign, not sandbox placement/);
  assert.match(source, /CPU and memory still require an ONNX workload benchmark/);
  assert.doesNotMatch(source, /Placement proven|Density option|Worker cluster/);
  assert.match(source, /We tested controller, execution, and memory separately and together/);
  assert.match(source, /nine-hour campaign/);
  assert.match(source, /What we tested/);
  assert.match(source, /Managed versus independent agents/);
  assert.match(source, /Limits of the comparison/);
  assert.doesNotMatch(source, /Run records/);
  assert.doesNotMatch(source, /Live OpenHands evidence/);
  assert.doesNotMatch(source, /After the tests, the Replicated instance had/);
  assert.match(source, /Durable state lets separate agent runs behave like one research campaign/);
  assert.match(source, /Files and Git for one controller/);
  assert.match(source, /Application database for concurrent controllers/);
  assert.match(source, /Candidate hashes and approach history/);
  assert.match(source, /Promotion rule/);
  assert.match(source, /Controller approaches evaluated/);
  assert.match(source, /Reliability and recovery tests/);
  assert.match(source, /What must be stored between agent runs/);
  assert.match(source, /How agents reused findings from earlier work/);
  assert.match(source, /Experiments completed and what they established/);
  assert.match(source, /Implications for teams using OpenHands/);
  assert.match(source, /Limitations and remaining tests/);
  assert.match(source, /ControllerTechnicalReport/);
  assert.match(source, /MemoryTechnicalReport/);
  assert.match(source, /ResultsTechnicalReport/);
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
  assert.match(snapshot, /"deeperComparison"/);
  assert.match(snapshot, /"wallSeconds": 501\.362/);
  assert.match(snapshot, /"wallSeconds": 333\.91/);
  assert.match(snapshot, /"wallSeconds": 374\.36/);
  assert.match(snapshot, /"modelCost": 0\.5064957/);
  assert.match(snapshot, /"failureInjection"/);
  assert.match(snapshot, /"wallSeconds": 299\.615/);
  assert.match(snapshot, /"healthyContracts": 3/);
  assert.match(snapshot, /"injectedFailuresDetected": 1/);
  assert.match(snapshot, /"controllerLoad"/);
  assert.match(snapshot, /"throughput": 100\.56/);
  assert.match(snapshot, /"acceptedValid": 2/);
  assert.match(snapshot, /"rejectedValid": 3/);
  assert.match(snapshot, /"documentedBatches": 4/);
  assert.match(snapshot, /"workerAttempts": 20/);
  assert.match(snapshot, /"documentedRuns": 17/);
  assert.match(snapshot, /"recurringRuns": 8/);
  assert.match(snapshot, /"enduranceCampaign"/);
  assert.match(snapshot, /"elapsedHours": 9\.0644/);
  assert.match(snapshot, /"lessonsPromoted": 6/);
  assert.match(snapshot, /"canvasController"/);
  assert.match(snapshot, /"campaignTicks": 6/);
  assert.match(snapshot, /"crashRecoveryPassed": true/);
});
