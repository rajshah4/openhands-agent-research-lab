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
      meanWallSeconds: number;
      meanCost: number;
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

const views = ["Overview", "Planner", "Runs", "Lessons"] as const;
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

export function ResearchDashboard({ snapshot }: { snapshot: Snapshot }) {
  const [view, setView] = useState<View>("Overview");
  const [arm, setArm] = useState("all");

  const visibleAgents = useMemo(
    () =>
      snapshot.agents.filter(
        (agent) => arm === "all" || agent.arm.toLowerCase() === arm,
      ),
    [snapshot.agents, arm],
  );

  const utilization = snapshot.capacity.active / snapshot.capacity.limit;
  const taskProgress = snapshot.proof.tasks / snapshot.proof.targetTasks;

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
          <p className="eyebrow">A question I wanted to test</p>
          <h1>Can coding agents learn from each other&apos;s experiments?</h1>
          <p className="lede">
            A Kaggle team used many agents to search for better solutions. I
            wanted a smaller public example that people could inspect and build
            on. So I used OpenHands to run the same problems with and without
            shared memory, then saved every result.
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
          <span>Bad lessons shared</span>
          <strong>{snapshot.proof.invalidLessons}</strong>
          <small>failed answers stay out</small>
        </div>
        <div>
          <span>Example problems</span>
          <strong>
            {snapshot.proof.tasks}/{snapshot.proof.targetTasks}
          </strong>
          <small>built so far</small>
          <div className="mini-meter">
            <span style={{ width: pct(taskProgress) }} />
          </div>
        </div>
      </section>

      {view === "Overview" && (
        <>
          <section className="section narrative">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Where the idea came from</p>
                <h2>NeuroGolf showed what many agents can try. I wanted to know what they should remember.</h2>
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
              Each of the 36 attempts was a separate OpenHands conversation
              with its own context and workspace. The controller chose the next
              problem, passed in earlier lessons, waited for the answer, ran
              the checker, saved the result, and paused the workspace. The next
              agent received only lessons that survived that loop. This
              reproduces the multi-agent research setup on small public
              problems that anyone can rerun.
            </p>
          </section>

          <section className="section comparison">
            <div className="section-heading">
              <div>
                <p className="eyebrow">What I tested</p>
                <h2>I ran the same six problems two ways, three times.</h2>
              </div>
              <p>
                The first group started fresh on every problem. The second
                group could read lessons from earlier valid answers. Both
                groups used the same model, problems, and number of attempts.
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
                <span className="finding-label">What happened</span>
                <strong>The six live problems were too easy.</strong>
                <p>
                  Both groups solved all 18 problems. The managed agents used
                  nine earlier lessons, but they did not score better. I would
                  not claim a quality win from this benchmark. It does show
                  that the agents, checks, memory, records, and cleanup worked
                  across 36 live conversations.
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
                    <dt>Measured cost</dt>
                    <dd>${snapshot.replicatedPatterns.isolatedFour.meanCost.toFixed(3)} per six-task batch.</dd>
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
                    <dd>One runtime, zero controller retries, ${snapshot.replicatedPatterns.groupedFour.meanCost.toFixed(3)} per batch.</dd>
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
                    <dt>Measured cost</dt>
                    <dd>${snapshot.replicatedPatterns.groupedSix.meanCost.toFixed(3)} per six-task batch.</dd>
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
        </>
      )}

      {view === "Planner" && <CompetitionPlanner snapshot={snapshot} />}

      {(view === "Overview" || view === "Runs") && (
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

      {(view === "Overview" || view === "Lessons") && (
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

      {view === "Runs" && (
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
          <p className="eyebrow">What I would test next</p>
          <h2>The next scale step needs a rollover fix.</h2>
        </div>
        <ol>
          <li>
            <span>✓</span>
            Keep this version as the working reference: 36/36 valid agent runs.
          </li>
          <li>
            <span>1</span>
            Fix and retest shared-sandbox rollover before increasing the queue
            from 12 to 24 jobs.
          </li>
          <li>
            <span>2</span>
            Keep using files until more than one controller needs to claim work
            at the same time. Then add a separate PostgreSQL database.
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
