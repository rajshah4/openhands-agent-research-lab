"use client";

import { useMemo, useState } from "react";

type AgentRecord = {
  id: string;
  arm: string;
  task: string;
  score: number | null;
  target: number;
  status: string;
  sandbox: string;
  transport: string;
  lessons: number;
  conversationUrl: string;
};

type Snapshot = {
  generatedAt: string;
  environment: {
    name: string;
    version: string;
    mode: string;
  };
  capacity: {
    active: number;
    limit: number;
    launchAtOrAbove: number;
    maxNewConcurrent: number;
    memoryAvailable: string;
    unhealthyPods: number;
    launchAllowed: boolean;
  };
  proof: {
    tests: number;
    liveAttempts: number;
    validAttempts: number;
    invalidLessons: number;
    tasks: number;
    targetTasks: number;
  };
  comparison: Record<
    "naive" | "managed",
    {
      solved: number;
      quality: number;
      qualityAuc: number;
      duplicates: number;
      retrievedLessons: number;
    }
  >;
  comparisonTaskCount: number;
  replicatedPatterns: Record<
    "isolatedFour" | "groupedFour" | "groupedSix",
    {
      valid: number;
      attempts: number;
      runtimesPerBatch: number;
      activeAgents: number;
      simultaneousSandboxes: number;
      queuedAgents: number;
      meanWallSeconds: number;
      meanCost: number;
      totalCost: number;
      controllerRetries: number;
    }
  >;
  scaleStudy: Record<
    "isolatedQueue" | "longLivedShared" | "boundedCells",
    {
      valid: number;
      attempts: number;
      sandboxes: number;
      wallSeconds: number;
      throughput: number;
      controllerRetries: number;
    }
  >;
  robustness: {
    attempts: number;
    elapsedSeconds: number;
    records: number;
    storeMb: number;
    speedup: number;
    liveRecoveryConversations: number;
  };
  portfolioScale: {
    tasks: number;
    attemptsPerArm: number;
    totalAttempts: number;
    elapsedSeconds: number;
    naiveQuality: number;
    managedQuality: number;
    exactAttemptsPerTask: number;
  };
  agents: AgentRecord[];
  lessons: Array<{
    id: string;
    statement: string;
    source: string;
    usedBy: string[];
    evidence: string;
  }>;
  incidents: Array<{
    title: string;
    finding: string;
    resolution: string;
    state: string;
  }>;
};

const views = ["Scale", "Deployment", "Robustness", "Planner"] as const;
type View = (typeof views)[number];

function pct(value: number) {
  return `${Math.round(value * 100)}%`;
}

function shortId(value: string) {
  return value.length > 12 ? `${value.slice(0, 8)}…` : value;
}

function armLabel(value: string) {
  return {
    all: "All runs",
    naive: "No memory",
    managed: "Shared lessons",
    regression: "Fix check",
  }[value.toLowerCase()] ?? value;
}

function transportLabel(value: string) {
  return {
    "exact-json": "Exact JSON",
    "fenced-json-fallback": "JSON in a code block",
    "trailing-json-fallback": "JSON after an explanation",
  }[value] ?? value.replaceAll("-", " ");
}

function formatNumber(value: number) {
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 1,
  }).format(value);
}

function formatMoney(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function CompetitionPlanner({ snapshot }: { snapshot: Snapshot }) {
  const [attemptsPerTask, setAttemptsPerTask] = useState(12);
  const [parallelCells, setParallelCells] = useState(4);
  const [workloadMultiplier, setWorkloadMultiplier] = useState(3);
  const [costPerAttempt, setCostPerAttempt] = useState(0.025);
  const [artifactMb, setArtifactMb] = useState(5);

  const tasks = 400;
  const agentsPerCell = 4;
  const conversationsPerSandbox = 6;
  const activeAgents = parallelCells * agentsPerCell;
  const totalJobs = tasks * attemptsPerTask;
  const coverageJobs = tasks;
  const explorationJobs = totalJobs - coverageJobs;
  const boundedCells = Math.ceil(totalJobs / conversationsPerSandbox);
  const isolatedThroughput =
    (snapshot.scaleStudy.isolatedQueue.throughput * activeAgents) /
    agentsPerCell /
    workloadMultiplier;
  const boundedThroughput =
    (snapshot.scaleStudy.boundedCells.throughput * parallelCells) /
    workloadMultiplier;
  const isolatedHours = totalJobs / isolatedThroughput;
  const boundedHours = totalJobs / boundedThroughput;
  const modelSpend = totalJobs * costPerAttempt;
  const artifactStorageGb = (totalJobs * artifactMb) / 1024;
  const ledgerEvents = totalJobs * 10;
  const pollingRequestsPerMinute = activeAgents * 15;
  const apiPressure = pollingRequestsPerMinute / 80;
  const workerCpu = parallelCells * 4;
  const workerMemoryGb = parallelCells * 8;
  const capacityHeadroom = 1.3;

  const applyPreset = (name: "coverage" | "campaign" | "intensive") => {
    if (name === "coverage") {
      setAttemptsPerTask(1);
      setParallelCells(2);
      setWorkloadMultiplier(2);
    } else if (name === "campaign") {
      setAttemptsPerTask(12);
      setParallelCells(4);
      setWorkloadMultiplier(3);
    } else {
      setAttemptsPerTask(25);
      setParallelCells(8);
      setWorkloadMultiplier(4);
    }
  };

  return (
    <section className="section planner-section">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Full NeuroGolf capacity planner</p>
          <h1>What would it take to cover all 400 tasks?</h1>
        </div>
        <p>
          The competition required one correct, optimized ONNX graph for each
          ARC task. My postmortem found that 249 tasks never received an
          independent attempt. This model makes coverage, repeated experiments,
          validation, and infrastructure visible before work begins.
        </p>
      </div>

      <div className="planner-presets" aria-label="Planning presets">
        <button type="button" onClick={() => applyPreset("coverage")}>
          Coverage pass
          <small>1 attempt per task</small>
        </button>
        <button type="button" onClick={() => applyPreset("campaign")}>
          Serious campaign
          <small>12 attempts per task</small>
        </button>
        <button type="button" onClick={() => applyPreset("intensive")}>
          Intensive search
          <small>25 attempts per task</small>
        </button>
      </div>

      <div className="planner-controls">
        <label>
          <span>
            Attempts per task <strong>{attemptsPerTask}</strong>
          </span>
          <input
            type="range"
            min="1"
            max="50"
            value={attemptsPerTask}
            onChange={(event) => setAttemptsPerTask(Number(event.target.value))}
          />
        </label>
        <label>
          <span>
            Parallel work cells <strong>{parallelCells}</strong>
          </span>
          <input
            type="range"
            min="1"
            max="25"
            value={parallelCells}
            onChange={(event) => setParallelCells(Number(event.target.value))}
          />
        </label>
        <label>
          <span>
            ONNX workload factor <strong>{workloadMultiplier}×</strong>
          </span>
          <input
            type="range"
            min="1"
            max="8"
            value={workloadMultiplier}
            onChange={(event) => setWorkloadMultiplier(Number(event.target.value))}
          />
        </label>
        <label>
          <span>
            Model cost per attempt <strong>${costPerAttempt.toFixed(3)}</strong>
          </span>
          <input
            type="range"
            min="0.005"
            max="0.25"
            step="0.005"
            value={costPerAttempt}
            onChange={(event) => setCostPerAttempt(Number(event.target.value))}
          />
        </label>
        <label>
          <span>
            Evidence per attempt <strong>{artifactMb} MB</strong>
          </span>
          <input
            type="range"
            min="1"
            max="25"
            value={artifactMb}
            onChange={(event) => setArtifactMb(Number(event.target.value))}
          />
        </label>
      </div>

      <div className="planner-total">
        <span>Planned work</span>
        <strong>{formatNumber(totalJobs)} agent attempts</strong>
        <small>
          {tasks} tasks × {attemptsPerTask} attempts · {activeAgents} agents
          active at once
        </small>
      </div>

      <div className="coverage-bar" aria-label={`${coverageJobs} coverage attempts and ${explorationJobs} optimization attempts`}>
        <span
          className="coverage-first"
          style={{ width: `${(coverageJobs / totalJobs) * 100}%` }}
        />
        {explorationJobs > 0 && (
          <span className="coverage-search" />
        )}
      </div>
      <div className="coverage-labels">
        <span>
          <i className="coverage-first" />
          <b>{formatNumber(coverageJobs)}</b> first-coverage attempts
        </span>
        <span>
          <i className="coverage-search" />
          <b>{formatNumber(explorationJobs)}</b> follow-up experiments
        </span>
      </div>

      <div className="planner-comparison">
        <article>
          <span className="implementation-status tested">Placement proven</span>
          <h2>Isolated queue</h2>
          <strong>{(isolatedHours / 24).toFixed(1)} days</strong>
          <p>
            {formatNumber(isolatedThroughput)} attempts/hour at the selected
            workload factor.
          </p>
          <dl>
            <div>
              <dt>Simultaneous sandboxes</dt>
              <dd>{activeAgents}</dd>
            </div>
            <div>
              <dt>Sandboxes over campaign</dt>
              <dd>{formatNumber(totalJobs)}</dd>
            </div>
            <div>
              <dt>Isolation</dt>
              <dd>One task per runtime</dd>
            </div>
          </dl>
        </article>
        <article className="recommended-plan">
          <span className="implementation-status pilot">Density option</span>
          <h2>Bounded shared cells</h2>
          <strong>{(boundedHours / 24).toFixed(1)} days</strong>
          <p>
            {formatNumber(boundedThroughput)} attempts/hour at the selected
            workload factor.
          </p>
          <dl>
            <div>
              <dt>Simultaneous sandboxes</dt>
              <dd>{parallelCells}</dd>
            </div>
            <div>
              <dt>Cells over campaign</dt>
              <dd>{formatNumber(boundedCells)}</dd>
            </div>
            <div>
              <dt>Isolation</dt>
              <dd>Four trusted agents per runtime</dd>
            </div>
          </dl>
        </article>
      </div>

      <div className="planner-requirements">
        <article>
          <span>Worker cluster</span>
          <strong>
            {Math.ceil(workerCpu * capacityHeadroom)} vCPU ·{" "}
            {Math.ceil(workerMemoryGb * capacityHeadroom)} GB RAM
          </strong>
          <p>
            {parallelCells} four-agent runtimes plus 30% operating headroom.
            This assumes 4 vCPU and 8 GB per ONNX work cell.
          </p>
        </article>
        <article className={apiPressure > 1 ? "requirement-warning" : ""}>
          <span>OpenHands control path</span>
          <strong>{formatNumber(pollingRequestsPerMinute)} requests/minute</strong>
          <p>
            About {apiPressure.toFixed(1)}× the measured safe 80-request/minute
            controller pace. Above that boundary, use event-driven status,
            fewer polls, or a tested higher API limit.
          </p>
        </article>
        <article>
          <span>Experiment ledger</span>
          <strong>{formatNumber(ledgerEvents)} lifecycle records</strong>
          <p>
            Use application-owned PostgreSQL for claims, leases, idempotency,
            task coverage, candidate state, and submission gates.
          </p>
        </article>
        <article>
          <span>Artifact storage</span>
          <strong>{formatNumber(artifactStorageGb)} GB</strong>
          <p>
            Candidate ONNX files, builders, validation logs, counterexamples,
            and immutable evidence belong in object storage with hashes.
          </p>
        </article>
        <article>
          <span>Estimated model spend</span>
          <strong>{formatMoney(modelSpend)}</strong>
          <p>
            Model calls only, using the selected per-attempt assumption.
            Infrastructure, human review, and Kaggle submissions are separate.
          </p>
        </article>
        <article>
          <span>Serial release gate</span>
          <strong>400/400 audit</strong>
          <p>
            Candidate work can run in parallel. ZIP assembly, differential
            audit, full scoring, and submission promotion remain single-writer.
          </p>
        </article>
      </div>

      <div className="planner-warning">
        <strong>What is measured and what is extrapolated</strong>
        <p>
          Four-active placement and 12-job queue behavior were measured on the
          Rajistics Replicated instance. Parallel shared cells, ONNX-heavy
          runtime demand, and the full-campaign duration are planning
          projections. Automatic sandbox rollover is excluded because it
          stalled in the 12-job test.
        </p>
      </div>

      <div className="planner-sources">
        <a href="https://www.kaggle.com/competitions/neurogolf-2026/writeups/155th-place-what-i-learned-about-managing-ai-codi">
          Competition postmortem ↗
        </a>
        <a href="https://2026.ijcai.org/competitions/">
          Official competition description ↗
        </a>
        <a href="https://github.com/rajshah4/openhands-agent-research-lab/tree/main/evidence/2026-07-25-replicated-scale-study">
          Measured scaling evidence ↗
        </a>
      </div>
    </section>
  );
}

function DeploymentDecisionGuide({ snapshot }: { snapshot: Snapshot }) {
  const patterns = [
    {
      name: "Enterprise isolated",
      record: "One conversation per agent",
      runtime: "One sandbox per conversation",
      isolation: "Strongest",
      use: "Untrusted code, mixed tenants, or failures that must stay local",
      tradeoff: "Highest container count and startup churn",
      concurrency: "N active agents require N simultaneous sandboxes",
      cost: `$${snapshot.replicatedPatterns.isolatedFour.totalCost.toFixed(3)} total for 18 measured attempts`,
      status: "Measured",
    },
    {
      name: "Enterprise bounded cell",
      record: "Separate conversations",
      runtime: "Several trusted agents share one sandbox",
      isolation: "Shared within the cell",
      use: "One trusted team that needs audit history with fewer containers",
      tradeoff: "Shared compute and a larger failure boundary",
      concurrency: "4 active conversations shared 1 sandbox; 2 waited",
      cost: `$${snapshot.replicatedPatterns.groupedFour.totalCost.toFixed(3)} total for 18 measured attempts`,
      status: "Measured",
    },
    {
      name: "Agent Canvas",
      record: "Canvas agent records",
      runtime: "Shared backend and workspace",
      isolation: "Shared trust boundary",
      use: "Tightly coupled trusted work and lightweight demonstrations",
      tradeoff: "Less runtime isolation than Enterprise conversations",
      concurrency: "Logical agents share one backend; size the backend for the workload",
      cost: "Not measured in the matched Replicated cost study",
      status: "Compared",
    },
    {
      name: "Subagents",
      record: "One parent conversation",
      runtime: "One parent sandbox",
      isolation: "Shared parent context",
      use: "Low-overhead delegation when separate histories are unnecessary",
      tradeoff: "Least independent audit and failure isolation",
      concurrency: "Delegated work shares one parent sandbox and its budgets",
      cost: "Not measured in the matched Replicated cost study",
      status: "Architecture option",
    },
  ];

  return (
    <>
      <section className="section narrative">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Deployment is a separate design decision</p>
            <h1>Choose the trust boundary before choosing the container count.</h1>
          </div>
          <p>
            Scheduling decides who does the work. Deployment decides what those
            workers share. OpenHands supports several useful boundaries; the
            right one depends on trust, audit needs, failure isolation, and
            infrastructure budget.
          </p>
        </div>
        <div className="workflow">
          {[
            ["01", "Trust", "Can these agents safely share a filesystem and compute?"],
            ["02", "Record", "Does every agent need its own conversation history?"],
            ["03", "Failure", "How much work may fail together?"],
            ["04", "Capacity", "How many sandboxes can the cluster sustain?"],
            ["05", "Lifecycle", "Who drains, pauses, and recycles each runtime?"],
          ].map(([number, title, copy]) => (
            <article className="workflow-step" key={number}>
              <span>{number}</span>
              <h3>{title}</h3>
              <p>{copy}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">OpenHands deployment choices</p>
            <h2>Four patterns, with different isolation and audit boundaries.</h2>
          </div>
          <p>
            These can use the same external task registry, scheduler,
            validators, and experiment ledger. Placement does not have to
            change the research protocol.
          </p>
        </div>
        <div className="agent-table-wrap">
          <table className="agent-table">
            <thead>
              <tr>
                <th>Pattern</th>
                <th>Agent record</th>
                <th>Runtime boundary</th>
                <th>Isolation</th>
                <th>Best fit</th>
                <th>Concurrency requirement</th>
                <th>Measured model cost</th>
                <th>Main tradeoff</th>
                <th>Evidence</th>
              </tr>
            </thead>
            <tbody>
              {patterns.map((pattern) => (
                <tr key={pattern.name}>
                  <td><strong>{pattern.name}</strong></td>
                  <td>{pattern.record}</td>
                  <td>{pattern.runtime}</td>
                  <td>{pattern.isolation}</td>
                  <td>{pattern.use}</td>
                  <td>{pattern.concurrency}</td>
                  <td>{pattern.cost}</td>
                  <td>{pattern.tradeoff}</td>
                  <td><span className="arm-chip managed">{pattern.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="section implementation-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">What Replicated measured</p>
            <h2>Grouping six conversations reduced six runtimes to one.</h2>
          </div>
          <p>
            The same model and six-task batch ran three times in each setup.
            This measured placement overhead and container pressure, not task
            difficulty.
          </p>
        </div>
        <div className="implementation-grid">
          <article className="implementation-card">
            <span className="implementation-status tested">Isolated</span>
            <h3>6 runtimes per batch</h3>
            <p>
              {snapshot.replicatedPatterns.isolatedFour.valid}/
              {snapshot.replicatedPatterns.isolatedFour.attempts} valid,{" "}
              {snapshot.replicatedPatterns.isolatedFour.meanWallSeconds.toFixed(1)}
              {" "}seconds mean wall time.
            </p>
            <dl>
              <div><dt>Concurrency</dt><dd>{snapshot.replicatedPatterns.isolatedFour.activeAgents} agents · {snapshot.replicatedPatterns.isolatedFour.simultaneousSandboxes} simultaneous sandboxes · {snapshot.replicatedPatterns.isolatedFour.queuedAgents} queued</dd></div>
              <div><dt>Total model cost</dt><dd>${snapshot.replicatedPatterns.isolatedFour.totalCost.toFixed(3)} across 18 attempts</dd></div>
              <div><dt>Choose for</dt><dd>Strong isolation and untrusted work.</dd></div>
            </dl>
          </article>
          <article className="implementation-card">
            <span className="implementation-status pilot">Bounded cell</span>
            <h3>1 runtime, 4 active agents</h3>
            <p>
              {snapshot.replicatedPatterns.groupedFour.valid}/
              {snapshot.replicatedPatterns.groupedFour.attempts} valid,{" "}
              {snapshot.replicatedPatterns.groupedFour.meanWallSeconds.toFixed(1)}
              {" "}seconds mean wall time.
            </p>
            <dl>
              <div><dt>Concurrency</dt><dd>{snapshot.replicatedPatterns.groupedFour.activeAgents} agents · {snapshot.replicatedPatterns.groupedFour.simultaneousSandboxes} simultaneous sandbox · {snapshot.replicatedPatterns.groupedFour.queuedAgents} queued</dd></div>
              <div><dt>Total model cost</dt><dd>${snapshot.replicatedPatterns.groupedFour.totalCost.toFixed(3)} across 18 attempts</dd></div>
              <div><dt>Choose for</dt><dd>Trusted production work with separate conversation histories.</dd></div>
            </dl>
          </article>
          <article className="implementation-card">
            <span className="implementation-status next">Higher density</span>
            <h3>1 runtime, 6 active agents</h3>
            <p>
              {snapshot.replicatedPatterns.groupedSix.valid}/
              {snapshot.replicatedPatterns.groupedSix.attempts} valid,{" "}
              {snapshot.replicatedPatterns.groupedSix.meanWallSeconds.toFixed(1)}
              {" "}seconds mean wall time.
            </p>
            <dl>
              <div><dt>Concurrency</dt><dd>{snapshot.replicatedPatterns.groupedSix.activeAgents} agents · {snapshot.replicatedPatterns.groupedSix.simultaneousSandboxes} simultaneous sandbox · {snapshot.replicatedPatterns.groupedSix.queuedAgents} queued</dd></div>
              <div><dt>Total model cost</dt><dd>${snapshot.replicatedPatterns.groupedSix.totalCost.toFixed(3)} across 18 attempts</dd></div>
              <div><dt>Finding</dt><dd>More contention without a wall-time win in this test.</dd></div>
            </dl>
          </article>
        </div>
        <p className="architecture-note">
          <strong>How OpenHands does it:</strong> Enterprise keeps each agent as
          a first-class conversation. The user&apos;s sandbox grouping strategy
          controls placement, but it is a heuristic—not a capacity lease.
          Therefore the application controller still owns admission, bounded
          cell size, drain, pause, and recycle. On this version, the safe
          trusted-work default is four active agents, no more than six
          conversations in a cell, then explicit recycle. Model cost varied
          substantially between otherwise matched batches, so these totals are
          observed spend—not evidence that placement caused the difference.
          Infrastructure cost was not measured.
        </p>
      </section>
    </>
  );
}

function RobustnessGuide({ snapshot }: { snapshot: Snapshot }) {
  const controls = [
    ["Single owner", "A file lock rejects a second controller instead of allowing two schedulers to race."],
    ["Stable identity", "Run, attempt, task, conversation, start-task, and sandbox IDs survive retries and restarts."],
    ["Resume, do not duplicate", "An interrupted attempt reattaches to the persisted OpenHands start task."],
    ["Independent validation", "Agent claims never promote themselves; deterministic code checks the candidate."],
    ["Validated memory", "Only valid, improving, traceable lessons reach later agents."],
    ["Backpressure", "The launch gate queues work before the small cluster reaches its runtime limit."],
    ["Explicit cleanup", "The controller verifies completion, drains the cell, pauses the sandbox, and records the result."],
  ];

  return (
    <>
      <section className="section narrative">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Production robustness</p>
            <h1>The hard part is not starting agents. It is knowing what happened when something stops.</h1>
          </div>
          <p>
            The controller treats OpenHands as the execution plane and keeps
            research state outside it. Every transition is recorded so work
            can be validated, resumed, rejected, or cleaned up without asking
            an agent to remember the system state.
          </p>
        </div>
        <div className="workflow">
          {[
            ["01", "Claim", "Record one owner, task, budget, and attempt ID."],
            ["02", "Start", "Persist the OpenHands start-task ID before waiting."],
            ["03", "Observe", "Track conversation, events, cost, tokens, and sandbox state."],
            ["04", "Validate", "Check the candidate outside the agent."],
            ["05", "Commit", "Save evidence and promote only validated memory."],
            ["06", "Release", "Pause the sandbox and return capacity to the queue."],
          ].map(([number, title, copy]) => (
            <article className="workflow-step" key={number}>
              <span>{number}</span>
              <h3>{title}</h3>
              <p>{copy}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="section implementation-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Seven controls around every agent</p>
            <h2>Reliability comes from the organization, not a longer prompt.</h2>
          </div>
          <p>
            These controls apply whether workers use isolated Enterprise
            sandboxes, bounded shared cells, Agent Canvas, or subagents.
          </p>
        </div>
        <div className="implementation-grid deployment-grid">
          {controls.map(([title, copy]) => (
            <article className="implementation-card" key={title}>
              <span className="implementation-status tested">Control</span>
              <h3>{title}</h3>
              <p>{copy}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="section comparison">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Failure injection and scale evidence</p>
            <h2>We killed the controller after OpenHands started the work.</h2>
          </div>
          <p>
            Restart found the unfinished attempt, attached to the same live
            conversation, validated the answer, recorded one completion, and
            returned the cluster to zero active sandboxes.
          </p>
        </div>
        <div className="comparison-grid">
          <article className="finding-card">
            <span className="finding-label">No duplicate work</span>
            <strong>One start task. One conversation. One completed attempt.</strong>
            <p>The original run and attempt identities were preserved across the controller restart.</p>
          </article>
          <article className="finding-card">
            <span className="finding-label">Large ledger</span>
            <strong>{formatNumber(snapshot.robustness.attempts)} attempts in {snapshot.robustness.elapsedSeconds.toFixed(2)} seconds.</strong>
            <p>{formatNumber(snapshot.robustness.records)} parseable records occupied {snapshot.robustness.storeMb} MB.</p>
          </article>
          <article className="finding-card">
            <span className="finding-label">Honest boundary</span>
            <strong>Restartable single controller, not a distributed queue.</strong>
            <p>Several controllers or tenants require application-owned database leases and idempotent claims.</p>
          </article>
        </div>
      </section>
    </>
  );
}

export function ResearchDashboard({ snapshot }: { snapshot: Snapshot }) {
  const [view, setView] = useState<View>("Scale");
  const [arm, setArm] = useState("all");

  const visibleAgents = useMemo(
    () =>
      snapshot.agents.filter(
        (agent) => arm === "all" || agent.arm.toLowerCase() === arm,
      ),
    [snapshot.agents, arm],
  );

  const utilization = snapshot.capacity.active / snapshot.capacity.limit;
  return (
    <main>
      <header className="topbar">
        <a className="brand" href="#top" aria-label="Research Lab home">
          <span className="brand-mark">N</span>
          <span>
            <strong>NeuroGolf with OpenHands</strong>
            <small>A public multi-agent experiment</small>
          </span>
        </a>
        <nav className="view-switcher" aria-label="Dashboard view">
          {views.map((item) => (
            <button
              className={view === item ? "active" : ""}
              key={item}
              onClick={() => setView(item)}
              type="button"
            >
              {item}
            </button>
          ))}
        </nav>
        <div className="environment-pill">
          <span className="pulse" />
          {snapshot.environment.name}
        </div>
      </header>

      <section className="hero" id="top">
        <div className="hero-copy">
          <p className="eyebrow">A public multi-agent systems test</p>
          <h1>We reproduced the organization behind a 400-task agent campaign.</h1>
          <p className="lede">
            NeuroGolf teams used many coding agents to search for better
            solutions. I rebuilt the coordination layer with OpenHands: who
            owns each task, what gets remembered, how results are checked, how
            work survives a restart, and how many containers it really needs.
          </p>
          <div className="hero-actions">
            <a href="#live-agents" className="primary-action">
              See what happened
            </a>
            <a
              href="https://github.com/rajshah4/openhands-agent-research-lab"
              className="text-action"
            >
              Read the code <span aria-hidden="true">↗</span>
            </a>
            <a
              href="https://github.com/rajshah4/openhands-agent-research-lab/tree/main/evidence/2026-07-25-final-reference"
              className="text-action"
            >
              Download the results <span aria-hidden="true">↗</span>
            </a>
          </div>
        </div>

        <aside className="capacity-card" aria-label="OpenHands server capacity">
          <div className="card-heading">
            <span>OpenHands after the test</span>
            <span
              className={`status-badge ${
                snapshot.capacity.launchAllowed ? "healthy" : "blocked"
              }`}
            >
              {snapshot.capacity.launchAllowed ? "Ready for another run" : "Runs paused"}
            </span>
          </div>
          <div className="capacity-number">
            <strong>{snapshot.capacity.active}</strong>
            <span>/ {snapshot.capacity.limit} agent workspaces running</span>
          </div>
          <div className="meter" aria-label={`${pct(utilization)} capacity used`}>
            <span style={{ width: pct(utilization) }} />
          </div>
          <dl className="capacity-details">
            <div>
              <dt>Stop new runs</dt>
              <dd>At {snapshot.capacity.launchAtOrAbove} running</dd>
            </div>
            <div>
              <dt>Runs at once</dt>
              <dd>{snapshot.capacity.maxNewConcurrent} agents</dd>
            </div>
            <div>
              <dt>Server memory free</dt>
              <dd>{snapshot.capacity.memoryAvailable}</dd>
            </div>
            <div>
              <dt>Unhealthy services</dt>
              <dd>{snapshot.capacity.unhealthyPods}</dd>
            </div>
          </dl>
          <p className="capacity-note">
            The recommended setup lets four trusted agents share one runtime
            while keeping six separate conversation records. The controller
            pauses the runtime only after the batch finishes.
          </p>
        </aside>
      </section>

      <section className="proof-strip" aria-label="Proof summary">
        <div>
          <span>Large orchestration run</span>
          <strong>{formatNumber(snapshot.portfolioScale.totalAttempts)}</strong>
          <small>{snapshot.portfolioScale.tasks} task owners, fully covered</small>
          <div className="mini-meter">
            <span style={{ width: pct(1) }} />
          </div>
        </div>
        <div>
          <span>Automated code checks</span>
          <strong>{snapshot.proof.tests}</strong>
          <small>all passed</small>
        </div>
        <div>
          <span>Valid live agent runs</span>
          <strong>
            {snapshot.proof.validAttempts}/{snapshot.proof.liveAttempts}
          </strong>
          <small>checked by code</small>
        </div>
        <div>
          <span>Attempts per task</span>
          <strong>{snapshot.portfolioScale.exactAttemptsPerTask}</strong>
          <small>for every one of the 400 tasks</small>
        </div>
      </section>

      {view === "Scale" && (
        <>
          <section className="section narrative">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Where the idea came from</p>
                <h2>NeuroGolf showed what many agents can try. This tests what keeps the whole campaign under control.</h2>
              </div>
              <p>
                OpenHands runs each coding agent in a separate workspace. My
                controller picks the problem, checks the answer, and decides
                whether the next agent should see what the first one learned.
              </p>
            </div>
            <div className="workflow">
              {[
                ["01", "Pick", "Choose one small optimization problem."],
                ["02", "Brief", "Give the agent only relevant lessons that already passed."],
                ["03", "Try", "Let one OpenHands agent produce a candidate answer."],
                ["04", "Check", "Run code that can prove whether the answer works."],
                ["05", "Remember", "Share the lesson only when the answer is valid and better."],
              ].map(([number, title, copy]) => (
                <article className="workflow-step" key={number}>
                  <span>{number}</span>
                  <h3>{title}</h3>
                  <p>{copy}</p>
                </article>
              ))}
            </div>
            <p className="architecture-note">
              The main scale result is a matched campaign with 400 task owners
              and 9,600 attempts. Every task received exactly 12 attempts, with
              unique ownership records and no missing work. The live
              Replicated test is smaller because it answers a different
              question: whether the same control loop works with real
              OpenHands conversations, model calls, sandboxes, and cleanup.
            </p>
          </section>

          <section className="section implementation-section scale-lead">
            <div className="section-heading">
              <div>
                <p className="eyebrow">The main orchestration result</p>
                <h2>One campaign coordinated 400 task owners and 9,600 attempts.</h2>
              </div>
              <p>
                This is the workload that tests the organization: coverage,
                repeated experiments, validated memory, immutable evidence,
                reporting, and restart-safe ownership across the shape of the
                full NeuroGolf challenge.
              </p>
            </div>
            <div className="implementation-grid">
              <article className="implementation-card">
                <span className="implementation-status tested">Complete coverage</span>
                <h3>400/400 tasks received work</h3>
                <p>
                  Both matched organizations completed{" "}
                  {formatNumber(snapshot.portfolioScale.attemptsPerArm)} attempts.
                  No task was starved while the scheduler revisited promising work.
                </p>
              </article>
              <article className="implementation-card">
                <span className="implementation-status tested">Balanced ownership</span>
                <h3>Exactly 12 attempts per task</h3>
                <p>
                  All attempt IDs and sequences were unique. The ledger retained
                  enough state to explain who tried what and what each later
                  attempt was allowed to remember.
                </p>
              </article>
              <article className="implementation-card">
                <span className="implementation-status pilot">Claim boundary</span>
                <h3>Complex organization, controlled workers</h3>
                <p>
                  Deterministic workers made the expected result knowable. This
                  proves orchestration scale, not that 400 model agents solved
                  the real ONNX competition.
                </p>
              </article>
            </div>
          </section>

          <section className="section comparison">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Supporting live-systems check</p>
                <h2>Before scaling, I verified the loop with real OpenHands agents.</h2>
              </div>
              <p>
                Six deliberately small, independently checkable problems were
                run with and without shared memory, three times each. They
                tested the live APIs and runtime lifecycle—not difficult
                reasoning or generalization.
              </p>
            </div>
            <div className="comparison-grid">
              {(["naive", "managed"] as const).map((name) => {
                const result = snapshot.comparison[name];
                return (
                  <article className={`arm-card ${name}`} key={name}>
                    <div className="arm-title">
                      <span>{name === "naive" ? "Naive setup" : "Managed setup"}</span>
                      <h3>{name === "naive" ? "No shared memory" : "Validated shared lessons"}</h3>
                    </div>
                    <dl>
                      <div>
                        <dt>Problems solved</dt>
                        <dd>{result.solved}/{snapshot.comparisonTaskCount}</dd>
                      </div>
                      <div>
                        <dt>Average quality</dt>
                        <dd>{result.quality.toFixed(3)}</dd>
                      </div>
                      <div>
                        <dt>Quality during each run</dt>
                        <dd>{result.qualityAuc.toFixed(3)}</dd>
                      </div>
                      <div>
                        <dt>Earlier lessons provided</dt>
                        <dd>{result.retrievedLessons}</dd>
                      </div>
                    </dl>
                    <div className="arm-bar">
                      <span style={{ width: pct(result.quality) }} />
                    </div>
                  </article>
                );
              })}
              <article className="finding-card">
                <span className="finding-label">Why keep this result</span>
                <strong>It proves the large design connects to real OpenHands infrastructure.</strong>
                <p>
                  Both groups solved all 18 problems. The managed agents used
                  nine earlier lessons but did not score better. This is not a
                  quality or generalization result. It verifies conversation
                  creation, model execution, validation, records, shared
                  memory, sandbox placement, and cleanup across 36 live runs.
                </p>
              </article>
            </div>
          </section>

          <section className="section implementation-section">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Three Replicated setups I measured</p>
                <h2>Six conversations do not have to mean six containers.</h2>
              </div>
              <p>
                I ran the same six problems and model three times for each
                setup. Every accepted batch solved all six problems. The main
                difference was where I put the isolation boundary and how much
                pressure I put on the small Enterprise server.
              </p>
            </div>
            <div className="implementation-grid">
              <article className="implementation-card">
                <span className="implementation-status tested">
                  Strongest isolation
                </span>
                <h3>Separate runtime for each agent</h3>
                <p>
                  I kept four agents active and queued two. Each agent owned its
                  runtime and paused it when finished. Across three accepted
                  batches, {snapshot.replicatedPatterns.isolatedFour.valid}/
                  {snapshot.replicatedPatterns.isolatedFour.attempts} answers
                  passed in an average of{" "}
                  {snapshot.replicatedPatterns.isolatedFour.meanWallSeconds.toFixed(1)}
                  {" "}seconds.
                </p>
                <dl>
                  <div>
                    <dt>Use it when</dt>
                    <dd>Code is untrusted, tenants differ, or failures must stay local.</dd>
                  </div>
                  <div>
                    <dt>Tradeoff</dt>
                    <dd>Six runtimes per batch. The controller needed {snapshot.replicatedPatterns.isolatedFour.controllerRetries} API retries.</dd>
                  </div>
                  <div>
                    <dt>Concurrency</dt>
                    <dd>4 agents in 4 sandboxes; 2 jobs queued.</dd>
                  </div>
                  <div>
                    <dt>Total model cost</dt>
                    <dd>${snapshot.replicatedPatterns.isolatedFour.totalCost.toFixed(3)} across all 18 accepted attempts.</dd>
                  </div>
                </dl>
              </article>

              <article className="implementation-card">
                <span className="implementation-status pilot">
                  Recommended starting point
                </span>
                <h3>One runtime, four active agents</h3>
                <p>
                  Six first-class Enterprise conversations shared one runtime.
                  Four ran while two waited. Across three batches,{" "}
                  {snapshot.replicatedPatterns.groupedFour.valid}/
                  {snapshot.replicatedPatterns.groupedFour.attempts} answers
                  passed in an average of{" "}
                  {snapshot.replicatedPatterns.groupedFour.meanWallSeconds.toFixed(1)}
                  {" "}seconds.
                </p>
                <dl>
                  <div>
                    <dt>Use it when</dt>
                    <dd>One trusted team wants production controls without one container per agent.</dd>
                  </div>
                  <div>
                    <dt>Tradeoff</dt>
                    <dd>Agents share compute and a larger failure boundary. Do not mix tenants.</dd>
                  </div>
                  <div>
                    <dt>Measured result</dt>
                    <dd>One runtime and zero controller retries.</dd>
                  </div>
                  <div>
                    <dt>Concurrency</dt>
                    <dd>4 agents in 1 sandbox; 2 jobs queued.</dd>
                  </div>
                  <div>
                    <dt>Total model cost</dt>
                    <dd>${snapshot.replicatedPatterns.groupedFour.totalCost.toFixed(3)} across all 18 accepted attempts.</dd>
                  </div>
                </dl>
              </article>

              <article className="implementation-card">
                <span className="implementation-status next">
                  Higher-pressure mode
                </span>
                <h3>One runtime, six active agents</h3>
                <p>
                  I filled the configured six-conversation sandbox cap. All{" "}
                  {snapshot.replicatedPatterns.groupedSix.valid}/
                  {snapshot.replicatedPatterns.groupedSix.attempts} answers
                  passed, but mean wall time was{" "}
                  {snapshot.replicatedPatterns.groupedSix.meanWallSeconds.toFixed(1)}
                  {" "}seconds—slower than the four-active setup.
                </p>
                <dl>
                  <div>
                    <dt>Use it when</dt>
                    <dd>Trusted, short jobs have already passed load tests on your installation.</dd>
                  </div>
                  <div>
                    <dt>Tradeoff</dt>
                    <dd>Larger contention and blast radius without a measured speed win here.</dd>
                  </div>
                  <div>
                    <dt>Concurrency</dt>
                    <dd>6 agents in 1 sandbox; no jobs queued.</dd>
                  </div>
                  <div>
                    <dt>Total model cost</dt>
                    <dd>${snapshot.replicatedPatterns.groupedSix.totalCost.toFixed(3)} across all 18 accepted attempts.</dd>
                  </div>
                </dl>
              </article>
            </div>
            <p className="architecture-note">
              For one six-task batch, my default is{" "}
              <strong>FEWEST_CONVERSATIONS with four active agents</strong>.
              The larger queue below adds an important boundary: recycle a
              shared sandbox after six conversations instead of asking one
              long-lived pool to roll over automatically. Keep separate
              runtimes for untrusted work. The experiment ledger stays outside
              the OpenHands internal database.
            </p>
          </section>

          <section className="section implementation-section">
            <div className="section-heading">
              <div>
                <p className="eyebrow">What happened when I doubled the queue</p>
                <h2>Twelve jobs exposed the rollover boundary.</h2>
              </div>
              <p>
                I kept the active limit at four and queued 12 jobs. This is a
                small scaling test, not a claim that this server can run 100
                agents at once.
              </p>
            </div>
            <div className="implementation-grid">
              <article className="implementation-card">
                <span className="implementation-status tested">
                  Reliable, more containers
                </span>
                <h3>Isolated queue</h3>
                <p>
                  {snapshot.scaleStudy.isolatedQueue.valid}/
                  {snapshot.scaleStudy.isolatedQueue.attempts} jobs passed in{" "}
                  {snapshot.scaleStudy.isolatedQueue.wallSeconds.toFixed(0)}
                  {" "}seconds. Four sandboxes ran at most, and each was paused
                  as soon as its job finished.
                </p>
                <dl>
                  <div>
                    <dt>Throughput</dt>
                    <dd>{snapshot.scaleStudy.isolatedQueue.throughput.toFixed(1)} jobs/hour.</dd>
                  </div>
                  <div>
                    <dt>Runtime use</dt>
                    <dd>{snapshot.scaleStudy.isolatedQueue.sandboxes} sandboxes over the queue&apos;s lifetime.</dd>
                  </div>
                  <div>
                    <dt>Recovery</dt>
                    <dd>{snapshot.scaleStudy.isolatedQueue.controllerRetries} transient API calls retried.</dd>
                  </div>
                </dl>
              </article>

              <article className="implementation-card">
                <span className="implementation-status next">
                  Do not use for a long queue
                </span>
                <h3>Automatic shared rollover</h3>
                <p>
                  The first sandbox filled with six conversations. Two start
                  tasks stalled after work rolled into the second sandbox, so
                  only {snapshot.scaleStudy.longLivedShared.valid}/
                  {snapshot.scaleStudy.longLivedShared.attempts} jobs passed.
                </p>
                <dl>
                  <div>
                    <dt>Throughput</dt>
                    <dd>{snapshot.scaleStudy.longLivedShared.throughput.toFixed(1)} jobs/hour.</dd>
                  </div>
                  <div>
                    <dt>Runtime use</dt>
                    <dd>{snapshot.scaleStudy.longLivedShared.sandboxes} shared sandboxes.</dd>
                  </div>
                  <div>
                    <dt>Failure</dt>
                    <dd>Two starts stayed non-ready past the 10-minute bound.</dd>
                  </div>
                </dl>
              </article>

              <article className="implementation-card">
                <span className="implementation-status pilot">
                  Trusted-work recommendation
                </span>
                <h3>Bounded shared cells</h3>
                <p>
                  I ran two six-job cells. Each cell drained and paused its
                  sandbox before the next began. All{" "}
                  {snapshot.scaleStudy.boundedCells.valid}/
                  {snapshot.scaleStudy.boundedCells.attempts} jobs passed.
                </p>
                <dl>
                  <div>
                    <dt>Throughput</dt>
                    <dd>{snapshot.scaleStudy.boundedCells.throughput.toFixed(1)} jobs/hour.</dd>
                  </div>
                  <div>
                    <dt>Runtime use</dt>
                    <dd>{snapshot.scaleStudy.boundedCells.sandboxes} sandboxes over the queue&apos;s lifetime.</dd>
                  </div>
                  <div>
                    <dt>Boundary</dt>
                    <dd>One controller owns each cell from admission through pause.</dd>
                  </div>
                </dl>
              </article>
            </div>
            <p className="architecture-note">
              A 100-job system should keep 100 jobs in a durable queue, not
              launch 100 containers. On this installation, the proven choices
              are a four-active isolated queue or sequential bounded shared
              cells. Parallel shared cells still need an explicit, tested way
              to lease or target a sandbox; the global grouping menu does not
              provide that contract.
            </p>
          </section>

          <section className="section implementation-section">
            <div className="section-heading">
              <div>
                <p className="eyebrow">The full-campaign shape</p>
                <h2>Every one of 400 task owners received exactly 12 attempts.</h2>
              </div>
              <p>
                This is a deterministic stress test of the scheduler, memory,
                ledger, and reporting—not a claim about model quality. It gives
                the system a known signal and verifies that no task disappears
                when the queue gets large.
              </p>
            </div>
            <div className="implementation-grid">
              <article className="implementation-card">
                <span className="implementation-status tested">Coverage</span>
                <h3>{formatNumber(snapshot.portfolioScale.totalAttempts)} recorded attempts</h3>
                <p>
                  Naive and managed campaigns each ran{" "}
                  {formatNumber(snapshot.portfolioScale.attemptsPerArm)} times.
                  All {snapshot.portfolioScale.tasks} tasks received exactly{" "}
                  {snapshot.portfolioScale.exactAttemptsPerTask} attempts.
                </p>
              </article>
              <article className="implementation-card">
                <span className="implementation-status tested">Bookkeeping speed</span>
                <h3>{snapshot.portfolioScale.elapsedSeconds.toFixed(2)} seconds</h3>
                <p>
                  The matched 9,600-attempt run completed locally with unique
                  IDs and sequences. This measures the control path, not ONNX
                  build time or model latency.
                </p>
              </article>
              <article className="implementation-card">
                <span className="implementation-status pilot">Known signal</span>
                <h3>
                  {snapshot.portfolioScale.naiveQuality.toFixed(3)} →{" "}
                  {snapshot.portfolioScale.managedQuality.toFixed(3)}
                </h3>
                <p>
                  The deterministic worker intentionally rewards validated
                  memory. The result proves the comparison can detect an
                  effect; it does not predict a Kaggle score.
                </p>
              </article>
            </div>
          </section>

          <section className="section implementation-section">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Failure was part of the test</p>
                <h2>I killed the controller after OpenHands started the work.</h2>
              </div>
              <p>
                Restarting the same campaign reattached to the existing
                Replicated conversation, completed one attempt, and paused the
                sandbox. It did not create duplicate work.
              </p>
            </div>
            <div className="implementation-grid">
              <article className="implementation-card">
                <span className="implementation-status tested">Large ledger</span>
                <h3>{formatNumber(snapshot.robustness.attempts)} attempts</h3>
                <p>
                  {formatNumber(snapshot.robustness.records)} parseable records
                  occupied {snapshot.robustness.storeMb} MB and completed in{" "}
                  {snapshot.robustness.elapsedSeconds.toFixed(2)} seconds.
                </p>
              </article>
              <article className="implementation-card">
                <span className="implementation-status tested">Restart</span>
                <h3>One conversation, not two</h3>
                <p>
                  The attempt kept its run ID and attempt ID, recovered the
                  persisted OpenHands start task, passed validation, and
                  returned the server to zero active sandboxes.
                </p>
              </article>
              <article className="implementation-card">
                <span className="implementation-status next">Production boundary</span>
                <h3>One controller owns the files</h3>
                <p>
                  A lock rejects a second controller. Multiple controllers or
                  tenants need an application-owned database with leases; they
                  should not write to OpenHands&apos; internal database.
                </p>
              </article>
            </div>
          </section>

          <section className="section implementation-section">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Four ways to use OpenHands</p>
                <h2>The right deployment depends on the isolation you need.</h2>
              </div>
              <p>
                Agent orchestration and sandbox placement are separate choices.
                OpenHands gives us several useful boundaries instead of forcing
                every agent into a new container.
              </p>
            </div>
            <div className="implementation-grid deployment-grid">
              {[
                ["Enterprise isolated", "One conversation and sandbox per agent.", "Untrusted code, mixed tenants, strongest failure isolation."],
                ["Enterprise bounded cell", "Several trusted conversations share one sandbox, then drain and recycle.", "Production controls with substantially fewer containers."],
                ["Agent Canvas", "Several agents share a backend and workspace.", "Tightly coupled trusted work and lightweight demonstrations."],
                ["Subagents in one conversation", "Delegated work stays inside one parent runtime.", "Lowest infrastructure overhead when separate histories are unnecessary."],
              ].map(([title, copy, use]) => (
                <article className="implementation-card" key={title}>
                  <span className="implementation-status pilot">OpenHands pattern</span>
                  <h3>{title}</h3>
                  <p>{copy}</p>
                  <dl>
                    <div>
                      <dt>Best fit</dt>
                      <dd>{use}</dd>
                    </div>
                  </dl>
                </article>
              ))}
            </div>
          </section>

          <section className="section comparison">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Compared with public Kaggle work</p>
                <h2>The organization is credible. The ONNX solver is still the next benchmark.</h2>
              </div>
              <p>
                Public NeuroGolf teams used task owners, watchdogs, persistent
                failures, promoted candidates, adversarial validation, and a
                serial submission gate. We now have the first five orchestration
                pieces, but not the competition artifact pipeline.
              </p>
            </div>
            <div className="comparison-grid">
              <article className="finding-card">
                <span className="finding-label">Proven here</span>
                <strong>Ownership, validation, memory, recovery, and capacity control.</strong>
                <p>
                  The live Replicated run and 400-task simulation exercise the
                  control system from selection through cleanup.
                </p>
              </article>
              <article className="finding-card">
                <span className="finding-label">Still required</span>
                <strong>ONNX builders, ARC execution, fuzzing, quarantine, and a 400/400 release audit.</strong>
                <p>
                  The next phase will use a clearly licensed public solution as
                  a workload reference. Unlicensed competition dumps will not
                  become dependencies.
                </p>
              </article>
              <article className="finding-card">
                <span className="finding-label">Honest claim</span>
                <strong>We reproduced the research organization, not a leaderboard score.</strong>
                <p>
                  That is already useful for people building agent research
                  systems, and it gives the domain benchmark a production-ready
                  place to run.
                </p>
              </article>
            </div>
          </section>
        </>
      )}

      {view === "Deployment" && <DeploymentDecisionGuide snapshot={snapshot} />}

      {view === "Robustness" && <RobustnessGuide snapshot={snapshot} />}

      {view === "Planner" && <CompetitionPlanner snapshot={snapshot} />}

      {(view === "Scale" || view === "Robustness") && (
        <section className="section" id="live-agents">
          <div className="section-heading agents-heading">
            <div>
              <p className="eyebrow">The actual conversations</p>
              <h2>These are real OpenHands runs. You can open them.</h2>
              <p>
                Each row links to the agent conversation. The score came from
                the independent checker, not from the agent grading itself.
              </p>
            </div>
            <div className="filter-row" aria-label="Filter experiments">
              {["all", "naive", "managed", "regression"].map((item) => (
                <button
                  className={arm === item ? "active" : ""}
                  key={item}
                  onClick={() => setArm(item)}
                  type="button"
                >
                  {armLabel(item)}
                </button>
              ))}
            </div>
          </div>
          <div className="agent-table-wrap">
            <table className="agent-table">
              <thead>
                <tr>
                  <th>Agent run</th>
                  <th>Test setup</th>
                  <th>Problem</th>
                  <th>Result</th>
                  <th>Lessons provided</th>
                  <th>Reply format</th>
                  <th>Workspace</th>
                </tr>
              </thead>
              <tbody>
                {visibleAgents.map((agent) => (
                  <tr key={agent.id}>
                    <td>
                      <a href={agent.conversationUrl}>
                        {shortId(agent.id)} <span aria-hidden="true">↗</span>
                      </a>
                    </td>
                    <td>
                      <span className={`arm-chip ${agent.arm.toLowerCase()}`}>
                        {armLabel(agent.arm)}
                      </span>
                    </td>
                    <td>{agent.task}</td>
                    <td>
                      <strong>{agent.score ?? "invalid"}</strong>
                      <small> / target {agent.target}</small>
                    </td>
                    <td>{agent.lessons ? `${agent.lessons} retrieved` : "none"}</td>
                    <td>{transportLabel(agent.transport)}</td>
                    <td>
                      <span className="paused-dot" />
                      {agent.sandbox.toLowerCase()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {view === "Robustness" && (
        <section className="section memory-section">
          <div className="section-heading">
            <div>
              <p className="eyebrow">What agents passed forward</p>
              <h2>An agent shared a lesson only after its answer passed the test.</h2>
            </div>
            <p>
              I kept the source problem, the checker result, and the later
              agents that received each lesson. A plausible sentence by itself
              was never enough.
            </p>
          </div>
          <div className="memory-grid">
            {snapshot.lessons.map((lesson) => (
              <article className="lesson-card" key={lesson.id}>
                <div className="lesson-id">{lesson.id}</div>
                <blockquote>“{lesson.statement}”</blockquote>
                <div className="provenance">
                  <div>
                    <span>Earned by</span>
                    <strong>{lesson.source}</strong>
                  </div>
                  <div>
                    <span>Used by</span>
                    <strong>{lesson.usedBy.join(", ")}</strong>
                  </div>
                </div>
                <p>{lesson.evidence}</p>
              </article>
            ))}
            <article className="memory-rule">
              <span>When a lesson gets shared</span>
              <strong>valid ∧ improving ∧ traceable</strong>
              <p>
                The answer must work, improve the best score, and point back to
                the run that produced it. Failed lessons stay in the record but
                never reach another agent.
              </p>
            </article>
          </div>
        </section>
      )}

      {view === "Robustness" && (
        <section className="section">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Bugs I found while building it</p>
              <h2>The first version broke in four useful ways.</h2>
            </div>
            <p>
              I kept the failed runs. They exposed problems that a polished
              architecture diagram would have missed.
            </p>
          </div>
          <div className="incident-list">
            {snapshot.incidents.map((incident, index) => (
              <article key={incident.title}>
                <span className="incident-number">0{index + 1}</span>
                <div>
                  <h3>{incident.title}</h3>
                  <p>{incident.finding}</p>
                </div>
                <div className="incident-resolution">
                  <span>{incident.state}</span>
                  <p>{incident.resolution}</p>
                </div>
              </article>
            ))}
          </div>
        </section>
      )}

      <section className="section next-gate">
        <div>
          <p className="eyebrow">What comes next</p>
          <h2>Put the real NeuroGolf workload on the proven control path.</h2>
        </div>
        <ol>
          <li>
            <span>✓</span>
            Keep this version as the working reference: 37/37 valid live runs,
            restart recovery, and 400/400 task-owner coverage.
          </li>
          <li>
            <span>1</span>
            Add a licensed ONNX workload adapter with official, fresh,
            adversarial, and metamorphic validation.
          </li>
          <li>
            <span>2</span>
            Fix shared-sandbox rollover, then run two explicitly owned cells in
            parallel before increasing the queue from 12 to 24 live jobs.
          </li>
          <li>
            <span>3</span>
            Keep files for one controller. Add application-owned PostgreSQL
            leases only when several controllers must claim work concurrently.
          </li>
        </ol>
      </section>

      <footer>
        <div>
          <strong>NeuroGolf with OpenHands</strong>
          <span>Built by Rajiv Shah as a public multi-agent experiment.</span>
        </div>
        <div>
          <span>
            OpenHands Enterprise {snapshot.environment.version} ·{" "}
            {snapshot.environment.mode}
          </span>
          <span>
            Snapshot {new Date(snapshot.generatedAt).toLocaleDateString()}
          </span>
        </div>
      </footer>
    </main>
  );
}
