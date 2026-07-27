"use client";

import { useState } from "react";

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
  canvasPilot: {
    clusterProvisionMinutes: number;
    coldStartSeconds: {
      first: number;
      recreated: number;
    };
    sharedLoadSix: {
      attempts: number;
      valid: number;
      wallSeconds: number;
      peakCpuMillis: number;
      peakMemoryMib: number;
      modelCost: number;
      restarts: number;
    };
    matchedDeployment: {
      attempts: number;
      valid: number;
      meanBatchWallSeconds: number;
      replicatedMeanBatchWallSeconds: number;
      effectiveThroughput: number;
      replicatedEffectiveThroughput: number;
      totalModelCost: number;
      replicatedTotalModelCost: number;
    };
    estimatedDailyInfrastructure: {
      publicListPrice: number;
      afterApplicableFreeTierLow: number;
      afterApplicableFreeTierHigh: number;
    };
  };
  subagentPilot: {
    settingEnabled: boolean;
    parallelToolCalls: number;
    sandboxCount: number;
    executionSeconds: number;
    endToEndSeconds: number;
    modelCost: number;
    taskToolAdvertised: boolean;
    taskActions: number;
    taskObservations: number;
    fallbackRun: {
      endToEndSeconds: number;
      modelCost: number;
      createdAdditionalConversation: boolean;
    };
  };
  agentCanvasTaskTool: {
    passed: boolean;
    agentCanvasVersion: string;
    agentServerVersion: string;
    parallelToolCalls: number;
    wallSeconds: number;
    taskSeconds: number;
    modelCalls: number;
    totalModelCost: number;
    childModelCost: number;
    taskActions: number;
    taskObservations: number;
    childType: string;
    taskId: string;
    deeperComparison: {
      sequential: {
        wallSeconds: number;
        modelCost: number;
        modelCalls: number;
        deterministicValid: number;
        strictContracts: number;
      };
      parallel: {
        wallSeconds: number;
        modelCost: number;
        modelCalls: number;
        deterministicValid: number;
        strictContracts: number;
        taskSpanSeconds: number;
      };
      firstClass: {
        wallSeconds: number;
        modelCost: number;
        modelCalls: number;
        deterministicValid: number;
        strictContracts: number;
        conversationRecords: number;
      };
      failureInjection: {
        wallSeconds: number;
        modelCost: number;
        modelCalls: number;
        taskActions: number;
        taskObservations: number;
        healthyContracts: number;
        injectedFailuresDetected: number;
        parentFinished: boolean;
      };
    };
  };
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
  controllerLoad: {
    enterpriseExternal: {
      valid: number;
      attempts: number;
      activeWorkers: number;
      queuedWorkers: number;
      sandboxes: number;
      wallSeconds: number;
      throughput: number;
      modelCost: number;
      retries: number;
    };
    enterpriseAutomation: {
      acceptedWorkers: number;
      acceptedValid: number;
      acceptedAttempts: number;
      acceptedWallSeconds: number;
      acceptedSandboxes: number;
      rejectedWorkers: number;
      rejectedValid: number;
      rejectedAttempts: number;
      rejectedWallSeconds: number;
    };
    canvasResume: {
      controllerProcesses: number;
      valid: number;
      attempts: number;
      firstSeconds: number;
      resumedSeconds: number;
    };
    externalValidation: {
      documentedBatches: number;
      workerAttempts: number;
      initialFullBatches: number;
      initialValidPerBatch: number;
      targetedValid: number;
      targetedAttempts: number;
      finalValid: number;
      finalAttempts: number;
    };
    automationValidation: {
      documentedRuns: number;
      pilotRuns: number;
      concurrencyRuns: number;
      cleanPilotTicks: number;
      recurringRuns: number;
    };
  };
  enduranceCampaign: {
    attempts: number;
    valid: number;
    tasksCovered: number;
    taskCount: number;
    elapsedHours: number;
    modelCost: number;
    promptTokens: number;
    completionTokens: number;
    lessonsPromoted: number;
    lessonRetrievals: number;
    duplicates: number;
    recoveryFailures: number;
    automationEnabled: boolean;
  };
  canvasController: {
    campaignTicks: number;
    valid: number;
    taskCount: number;
    elapsedSeconds: number;
    modelCost: number;
    promptTokens: number;
    completionTokens: number;
    crashRecoveryPassed: boolean;
    overlapLockPassed: boolean;
    restarts: number;
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

const views = ["Overview", "Deployment", "Robustness", "How we tested", "Scaling"] as const;
type View = (typeof views)[number];

function pct(value: number) {
  return `${Math.round(value * 100)}%`;
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
  const workerSlotsWithHeadroom = Math.ceil(activeAgents * 1.3);

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
          <p className="eyebrow">NeuroGolf scaling planner</p>
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
          <span className="implementation-status tested">Higher isolation</span>
          <h2>One sandbox per active agent</h2>
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
          <span className="implementation-status pilot">Fewer sandboxes</span>
          <h2>Four agents per shared sandbox</h2>
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

      <div className="section-heading">
        <div>
          <p className="eyebrow">Shared production services</p>
          <h2>These estimates scale with the campaign, not sandbox placement.</h2>
        </div>
        <p>
          Both execution options run the same number of agent attempts and keep
          the same evidence. The cards above change sandbox count and isolation;
          the requirements below change when the work volume, concurrency, or
          retention assumptions change.
        </p>
      </div>
      <div className="planner-requirements">
        <article>
          <span>Concurrent worker capacity</span>
          <strong>{workerSlotsWithHeadroom} worker slots</strong>
          <p>
            {activeAgents} agents active at once plus 30% operating headroom.
            The placement cards above show whether those agents use{" "}
            {activeAgents} isolated sandboxes or {parallelCells} shared
            sandboxes. CPU and memory still require an ONNX workload benchmark.
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
            A planning allowance of 10 records per attempt for claims, leases,
            status changes, validation, candidate state, and submission gates.
            This is independent of sandbox placement.
          </p>
        </article>
        <article>
          <span>Durable evidence storage</span>
          <strong>{formatNumber(artifactStorageGb)} GB</strong>
          <p>
            {formatNumber(totalJobs)} attempts × {artifactMb} MB retained per
            attempt. Candidate ONNX files, validation logs, and counterexamples
            are kept whether agents use isolated or shared sandboxes.
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

function OverviewGuide({ snapshot }: { snapshot: Snapshot }) {
  return (
    <>
      <section className="section narrative" id="overview">
        <div className="section-heading">
          <div>
            <p className="eyebrow">What the Kaggle competition required</p>
            <h1>NeuroGolf had 400 separate ARC tasks, each requiring a correct and efficient ONNX program.</h1>
          </div>
          <p>
            Each task described an input-to-output transformation. A submission
            needed an ONNX graph that reproduced that transformation correctly.
            Once a graph worked, the competition rewarded reducing its memory
            use and parameter count.
          </p>
        </div>
        <div className="implementation-grid">
          <article className="implementation-card">
            <span className="implementation-status tested">The workload</span>
            <h3>400 independent implementation problems</h3>
            <p>
              Every ARC task could require a different algorithm, builder, test
              process, and optimization strategy.
            </p>
          </article>
          <article className="implementation-card">
            <span className="implementation-status tested">The scoring problem</span>
            <h3>Correctness first, then program efficiency</h3>
            <p>
              A smaller graph was useful only after it passed the task&apos;s
              examples and independent validation.
            </p>
          </article>
          <article className="implementation-card">
            <span className="implementation-status pilot">The research problem</span>
            <h3>Many candidate implementations per task</h3>
            <p>
              Teams needed to preserve failed approaches, compare candidates,
              and keep the best validated result for each task.
            </p>
          </article>
        </div>
      </section>

      <section className="section narrative">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Why teams used multiple agents</p>
            <h2>The 400 tasks could be worked on in parallel, but the work still needed central coordination.</h2>
          </div>
          <p>
            Kaggle did not require agents. The workload made them useful:
            different workers could try different tasks and approaches at the
            same time. Without a shared task registry and validation process,
            however, agents could repeat the same work while other tasks were
            never attempted.
          </p>
        </div>
        <div className="workflow">
          {[
            ["01", "Register", "Keep one record for each of the 400 competition tasks."],
            ["02", "Assign", "Give every attempt a task, owner, budget, and stable ID."],
            ["03", "Experiment", "Run candidate implementations in bounded agent workspaces."],
            ["04", "Validate", "Check results outside the agent before accepting them."],
            ["05", "Record", "Save failures, improvements, artifacts, and reusable lessons."],
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
            <p className="eyebrow">What this project reproduced</p>
            <h2>We exercised the coordination system with 12 attempts for each of 400 tasks.</h2>
          </div>
          <p>
            The scale run used controlled deterministic workers so that missing
            work, duplicate ownership, incorrect retrieval, and measurement
            errors could be detected reliably.
          </p>
        </div>
        <div className="implementation-grid">
          <article className="implementation-card">
            <span className="implementation-status tested">Task assignment</span>
            <h3>All 400 tasks received work</h3>
            <p>
              The scheduler recorded exactly{" "}
              {snapshot.portfolioScale.exactAttemptsPerTask} attempts for every
              task instead of concentrating work on only a subset.
            </p>
          </article>
          <article className="implementation-card">
            <span className="implementation-status tested">Experiment history</span>
            <h3>{formatNumber(snapshot.portfolioScale.totalAttempts)} attempts were retained</h3>
            <p>
              Each attempt kept its task, sequence, result, validation state,
              and the lessons it was allowed to use.
            </p>
          </article>
          <article className="implementation-card">
            <span className="implementation-status next">Production path</span>
            <h3>The same control path can run NeuroGolf workers</h3>
            <p>
              A production run would replace the controlled workers with
              licensed ONNX builders and validators while keeping the
              scheduler, attempt history, shared memory, and recovery path.
            </p>
          </article>
        </div>
      </section>

      <section className="section comparison">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Scope of this test</p>
            <h2>This test focused on multi-agent orchestration.</h2>
          </div>
          <p>
            The results give us enough evidence to proceed with OpenHands as
            the execution layer for a full campaign. OpenHands would manage
            agent conversations and sandboxes; the application would continue
            to own scheduling, experiment history, validation, and promotion.
          </p>
        </div>
        <div className="comparison-grid">
          <article className="finding-card">
            <span className="finding-label">Domain worker</span>
            <strong>Connect licensed NeuroGolf builders, ONNX execution, and competition-specific validators.</strong>
          </article>
          <article className="finding-card">
            <span className="finding-label">Production state</span>
            <strong>Add database leases and artifact storage when more than one controller runs the campaign.</strong>
          </article>
          <article className="finding-card">
            <span className="finding-label">Release process</span>
            <strong>Quarantine candidates, run an independent 400-task audit, and assemble the submission through one release writer.</strong>
          </article>
        </div>
        <div className="architecture-note">
          <strong>Our conclusion:</strong> OpenHands can orchestrate this
          campaign as the worker execution layer. The remaining work is domain
          and production integration, not a different orchestration
          architecture. A 100-agent deployment should still pass
          multi-controller and API load tests before it is treated as proven at
          that concurrency.
        </div>
      </section>

      <section className="section implementation-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Where the orchestration lived</p>
            <h2>OpenHands ran the agents; our application ran the research organization.</h2>
          </div>
          <p>
            The experiments were not an all-in-one OpenHands feature. I used
            controller code outside the agent runtime to decide what should
            run, verify the result, and preserve campaign state. OpenHands
            supplied the execution and lifecycle layer.
          </p>
        </div>
        <div className="implementation-grid">
          <article className="implementation-card">
            <span className="implementation-status tested">Application-owned</span>
            <h3>Campaign policy and evidence</h3>
            <p>
              Task registry, scheduling, coverage, attempt ledger, retrieved
              lessons, output contracts, deterministic validation, promotion,
              admission control, retry policy, and cleanup decisions.
            </p>
          </article>
          <article className="implementation-card">
            <span className="implementation-status tested">OpenHands-owned</span>
            <h3>Agent execution and runtime lifecycle</h3>
            <p>
              Model and tool loop, conversations, native subagents, workspaces,
              sandbox creation or grouping, event history, usage metadata, and
              pause controls.
            </p>
          </article>
          <article className="implementation-card">
            <span className="implementation-status pilot">Human-owned</span>
            <h3>Objectives and final authority</h3>
            <p>
              Benchmark design, risk boundaries, stopping rules, review of
              unusual failures, release approval, and the final Kaggle
              submission remain human decisions.
            </p>
          </article>
        </div>
        <p className="architecture-note">
          <strong>Practical interpretation:</strong> most of the organizational
          intelligence was application code outside OpenHands; most of the
          agent-execution mechanics were inside OpenHands. The controller could
          itself run as an OpenHands parent or automation, but its durable
          ledger and independent validators should remain application-owned.
        </p>
      </section>

      <section className="section comparison">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Comparison with public NeuroGolf solutions</p>
            <h2>Competition teams built persistent research pipelines around general coding agents.</h2>
          </div>
          <p>
            The reviewed writeups describe custom schedulers, task files,
            checkpoint state, validators, and promotion gates around Codex,
            ChatGPT, or Claude Code. Their competitive advantage came mainly
            from domain context and validation—not from a packaged multi-agent
            runtime.
          </p>
        </div>
        <div className="implementation-grid">
          <article className="implementation-card">
            <span className="implementation-status tested">Winning-team reference</span>
            <h3>A campaign pipeline, not a one-time swarm</h3>
            <p>
              The published pipeline treated task state, candidate history,
              validation, and promotion as durable parts of the competition
              system. Repeated agent work improved a retained portfolio instead
              of starting from an empty prompt each time.
            </p>
          </article>
          <article className="implementation-card">
            <span className="implementation-status tested">Third place</span>
            <h3>Custom files and Codex/ChatGPT handoffs</h3>
            <p>
              The team maintained promoted history, rejected attempts, retry
              state, negative knowledge, task ZIPs, and local checks, then
              merged the UI and local histories after each attempt.
            </p>
          </article>
          <article className="implementation-card">
            <span className="implementation-status tested">Ninth place</span>
            <h3>A custom resumable Codex scheduler</h3>
            <p>
              A bounded worker pool used one persistent session per task,
              backup and restore, strict validation, checkpoint files, and a
              serialized step for consolidating proven techniques.
            </p>
          </article>
          <article className="implementation-card">
            <span className="implementation-status tested">Agent-management lesson</span>
            <h3>External task ownership prevented agent drift</h3>
            <p>
              One public postmortem found that agents changed tasks based on
              local ROI. Restricting each worker to one task workspace restored
              global coverage control.
            </p>
          </article>
        </div>
        <p className="architecture-note">
          <strong>Where OpenHands helps:</strong> it can replace custom process,
          sandbox, conversation, event, pause, and operator-visibility glue.
          It does not replace the NeuroGolf task context, ONNX builders,
          adversarial validators, scheduling policy, or promotion logic that
          separated the strongest teams.
        </p>
        <div className="planner-sources">
          <a href="https://www.kaggle.com/competitions/neurogolf-2026/discussion/726799">
            Winning-team pipeline ↗
          </a>
          <a href="https://www.kaggle.com/competitions/neurogolf-2026/writeups/3rd-place-solution-writeup">
            Third-place writeup ↗
          </a>
          <a href="https://www.kaggle.com/competitions/neurogolf-2026/writeups/9th-place-solution">
            Ninth-place writeup ↗
          </a>
          <a href="https://www.kaggle.com/competitions/neurogolf-2026/writeups/155th-place-what-i-learned-about-managing-ai-codi">
            Agent-management postmortem ↗
          </a>
        </div>
      </section>
    </>
  );
}

function TestMethodGuide({ snapshot }: { snapshot: Snapshot }) {
  return (
    <>
      <section className="section narrative">
        <div className="section-heading">
          <div>
            <p className="eyebrow">How we tested</p>
            <h1>We tested the orchestration separately from the competition solver.</h1>
          </div>
          <p>
            Small deterministic problems made orchestration failures easy to
            detect. A separate nine-hour campaign tested scheduled control,
            multi-step tool use, Git handoff, shared lessons, and recovery.
            Neither test substitutes for the real ONNX workload.
          </p>
        </div>
        <div className="agent-table-wrap method-table">
          <table className="agent-table">
            <thead>
              <tr>
                <th>What we tested</th>
                <th>Method</th>
                <th>What the result tells us</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>OpenHands execution path</strong></td>
                <td>
                  {snapshot.proof.validAttempts}/
                  {snapshot.proof.liveAttempts} accepted runs; every answer
                  checked by deterministic code
                </td>
                <td>
                  Conversations could be created, completed, independently
                  validated, and cleaned up.
                </td>
              </tr>
              <tr>
                <td><strong>Managed versus independent agents</strong></td>
                <td>
                  The same six problems ran under both organizations three
                  times, using the same model, timeouts, and attempt budgets.
                </td>
                <td>
                  Differences in coverage, time, and cost came from the
                  orchestration setup rather than different test inputs.
                </td>
              </tr>
              <tr>
                <td><strong>Limits of the comparison</strong></td>
                <td>
                  The problems were small and both organizations could solve
                  them.
                </td>
                <td>
                  The test measures orchestration behavior. It does not
                  establish a reasoning-quality or Kaggle-score advantage.
                </td>
              </tr>
              <tr>
                <td><strong>Enterprise endurance campaign</strong></td>
                <td>
                  {snapshot.enduranceCampaign.attempts} hourly attempts over{" "}
                  {snapshot.enduranceCampaign.elapsedHours.toFixed(1)} hours.
                  Each worker compared three approaches, ran at least 12
                  trials, and wrote a Git artifact.
                </td>
                <td>
                  Scheduled OpenHands automations resumed one campaign from
                  Git, passed validated lessons between conversations, and
                  retained both a failed recovery and a duplicate experiment.
                </td>
              </tr>
              <tr>
                <td><strong>Agent Canvas controller</strong></td>
                <td>
                  {snapshot.canvasController.campaignTicks} separate Kubernetes
                  controller ticks, followed by forced termination and an
                  overlapping-controller test.
                </td>
                <td>
                  A controller running beside Agent Canvas recovered an existing
                  conversation after restart, while the file lock rejected a
                  second controller before it launched duplicate work.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p className="architecture-note">
          The run records below link the method to the individual OpenHands
          conversations. Finished experiment sandboxes were paused after their
          results were recorded.
        </p>
      </section>
    </>
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
      concurrency: "Six jobs total: four run in four sandboxes; two wait for an agent slot",
      cost: `$${snapshot.replicatedPatterns.isolatedFour.totalCost.toFixed(3)} total for 18 measured attempts`,
      enterprise: "Yes for the tested self-hosted boundary",
      recovery: "Retry one conversation; sandbox failure stays local",
      management: "Clearest ownership and audit trail; most runtimes to operate",
      status: "Measured",
    },
    {
      name: "Enterprise bounded cell",
      record: "Separate conversations",
      runtime: "Several trusted agents share one sandbox",
      isolation: "Shared within the cell",
      use: "One trusted team that needs audit history with fewer containers",
      tradeoff: "Shared compute and a larger failure boundary",
      concurrency: "Six jobs total: four run in one sandbox; two wait for an agent slot",
      cost: `$${snapshot.replicatedPatterns.groupedFour.totalCost.toFixed(3)} total for 18 measured attempts`,
      enterprise: "Yes for built-in grouped placement",
      recovery: "Retry one conversation; recycle the cell after shared-runtime trouble",
      management: "Separate histories with bounded infrastructure",
      status: "Measured",
    },
    {
      name: "Agent Canvas",
      record: "Canvas agent records",
      runtime: "Shared backend and workspace",
      isolation: "Shared trust boundary",
      use: "One trusted team that wants lower runtime overhead and can own the surrounding controls",
      tradeoff: "The application owns capacity, access, and shared-workspace safety",
      concurrency: "Logical agents share one backend; size the backend for the workload",
      cost: `$${snapshot.canvasPilot.matchedDeployment.totalModelCost.toFixed(3)} total for 18 matched attempts`,
      enterprise: "No",
      recovery: "Retry one record; backend or workspace failure can affect the group",
      management: "Independent records, but the application owns trust and capacity controls",
      status: "Compared",
    },
    {
      name: "Subagents",
      record: "One parent conversation",
      runtime: "One parent sandbox",
      isolation: "Shared parent context",
      use: "Two to four independent specialists inside one trusted work cell",
      tradeoff: "Children share the parent lifecycle, workspace, and audit record",
      concurrency: "Four read-only delegates ran concurrently; shared writes can race",
      cost: `$${snapshot.agentCanvasTaskTool.deeperComparison.parallel.modelCost.toFixed(3)} for four matched Canvas tasks`,
      enterprise: "No",
      recovery: "Parent or controller identifies and reissues the failed child",
      management: "One compact record; weakest child-level audit and handoff",
      status: "Canvas validated",
    },
  ];

  return (
    <>
      <section className="section narrative">
        <div className="section-heading">
          <div>
            <p className="eyebrow">OpenHands multi-agent deployment options</p>
            <h1>Four ways to organize agent execution.</h1>
          </div>
          <p>
            The scheduler can assign the same work through four different
            execution structures. The choice determines whether agents receive
            separate records, separate sandboxes, or a shared working
            environment.
          </p>
        </div>
        <div className="pattern-grid">
          {[
            ["01", "Enterprise isolated", "Each agent has its own OpenHands conversation and sandbox.", "isolated", "Measured"],
            ["02", "Enterprise grouped", "Agents keep separate conversations while trusted work shares a sandbox.", "grouped", "Measured"],
            ["03", "Agent Canvas", "Several agents share one lighter agent backend, workspace, and trust boundary.", "canvas", "Measured"],
            ["04", "Parent with subagents", "One parent delegates through TaskToolSet inside its conversation and sandbox.", "subagents", "Validated in Canvas"],
          ].map(([number, title, copy, visual, status]) => (
            <article className="pattern-card" key={number}>
              <div className={`pattern-miniature ${visual}`} aria-hidden="true">
                <span className="mini-parent" />
                <span className="mini-connector" />
                <span className="mini-workers">
                  <i />
                  <i />
                  <i />
                </span>
              </div>
              <span className="pattern-number">{number}</span>
              <h3>{title}</h3>
              <p>{copy}</p>
              <small>{status}</small>
            </article>
          ))}
        </div>
        <figure className="deployment-illustration">
          <img
            src="/deployment-options.png"
            alt="Four OpenHands execution structures: separate Enterprise sandboxes, grouped Enterprise conversations in one sandbox, Agent Canvas records in one shared backend and workspace, and parent-managed subagents in one sandbox."
          />
          <figcaption>
            The four structures differ in runtime isolation and record
            ownership. The controller, validators, and experiment ledger can
            remain the same.
          </figcaption>
        </figure>
        <p className="architecture-note">
          The same campaign controller, task registry, validators, and
          experiment ledger can be used with all four structures. The
          execution choice changes isolation, runtime count, agent history,
          failure scope, and how much operational control the application must
          provide.
        </p>
        <div className="section-heading comparison-table-heading report-heading">
          <div>
            <p className="eyebrow">Comparison at a glance: operational tradeoffs among the four structures</p>
          </div>
          <p>
            Use this table for the initial decision. The sections below provide
            the implementation details and measured evidence for each
            approach.
          </p>
        </div>
        <div className="agent-table-wrap">
          <table className="agent-table">
            <thead>
              <tr>
                <th>Pattern</th>
                <th>Need Enterprise?</th>
                <th>Agent record</th>
                <th>Runtime boundary</th>
                <th>Failure and retry scope</th>
                <th>Manageability</th>
                <th>Best fit</th>
                <th>Main tradeoff</th>
                <th>Evidence</th>
              </tr>
            </thead>
            <tbody>
              {patterns.map((pattern) => (
                <tr key={pattern.name}>
                  <td><strong>{pattern.name}</strong></td>
                  <td>{pattern.enterprise}</td>
                  <td>{pattern.record}</td>
                  <td>{pattern.runtime}</td>
                  <td>{pattern.recovery}</td>
                  <td>{pattern.management}</td>
                  <td>{pattern.use}</td>
                  <td>{pattern.tradeoff}</td>
                  <td><span className="arm-chip managed">{pattern.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="section implementation-section">
        <div className="section-heading report-heading">
          <div>
            <p className="eyebrow">Agent Canvas: a shared agent service for one trusted team</p>
          </div>
          <p>
            Unlike Enterprise conversations, Canvas does not create a separate
            sandbox boundary for each agent. Agents keep separate records but
            share the backend, workspace, credentials, and infrastructure
            failure boundary.
          </p>
        </div>
        <div className="implementation-grid">
          <article className="implementation-card">
            <span className="implementation-status tested">Organization</span>
            <h3>Independent agent records on one shared service</h3>
            <p>
              The controller can assign and retry individual Canvas
              conversations while the agents use the same Agent Server and
              persistent workspace.
            </p>
          </article>
          <article className="implementation-card">
            <span className="implementation-status tested">Advantage</span>
            <h3>Lower runtime overhead for trusted work</h3>
            <p>
              A team can coordinate many logical agents without operating one
              sandbox for every conversation. Enterprise is not required for
              this execution model.
            </p>
          </article>
          <article className="implementation-card">
            <span className="implementation-status pilot">Tradeoff</span>
            <h3>The application owns the shared boundary</h3>
            <p>
              Capacity limits, access control, workspace safety, credentials,
              and recovery from a backend failure remain the
              application&apos;s responsibility.
            </p>
          </article>
        </div>
        <details className="compact-details">
          <summary>Implementation and measured evidence</summary>
          <div className="compact-details-grid">
            <div>
              <h3>Setup</h3>
              <p>
                GKE Autopilot in us-central1, one StatefulSet pod, one internal
                ClusterIP service, and one 20 GiB persistent volume. The pod
                requested 500m CPU and 1 GiB memory, with limits of 2 CPU and
                4 GiB.
              </p>
            </div>
            <div>
              <h3>Why Kubernetes</h3>
              <p>
                Kubernetes supplied restart, storage, and service lifecycle for
                the shared Canvas backend. It did not add per-agent isolation;
                all agents remained inside the same trusted service boundary.
              </p>
            </div>
            <div>
              <h3>Load check</h3>
              <p>
                {snapshot.canvasPilot.sharedLoadSix.valid}/
                {snapshot.canvasPilot.sharedLoadSix.attempts} attempts
                validated with {snapshot.canvasPilot.sharedLoadSix.restarts}
                {" "}backend restarts. This established that several logical
                agents could share one service for the tested workload.
              </p>
            </div>
            <div>
              <h3>Matched comparison</h3>
              <p>
                All {snapshot.canvasPilot.matchedDeployment.valid} matched
                attempts validated. Canvas and Enterprise had effectively tied
                reported model cost; the important difference was the runtime
                and trust boundary, not answer quality.
              </p>
            </div>
          </div>
          <p>
            Choose Canvas when one trusted team values a shared service and is
            prepared to own the surrounding operational controls. Choose
            Enterprise when agents require stronger isolation, separate
            credentials, platform-managed sandbox lifecycle, or tenant
            boundaries.
          </p>
        </details>
      </section>

      <section className="section implementation-section">
        <div className="section-heading report-heading">
          <div>
            <p className="eyebrow">Enterprise: comparing isolated and grouped conversations</p>
          </div>
          <p>
            The same model and six-task batch ran three times in each setup.
            All three approaches produced 18/18 valid results. The useful
            differences were sandbox count, queueing, failure scope, and the
            type of work each approach can safely run.
          </p>
        </div>
        <p className="architecture-note">
          <strong>What “waiting” means:</strong> every batch contained six
          agent jobs. A four-agent admission limit started four and kept two in
          the controller queue until an agent slot opened. Those waiting jobs
          did not have sandboxes yet. This backpressure kept the small
          installation within its safe operating range.
        </p>
        <div className="implementation-grid">
          <article className="implementation-card">
            <span className="implementation-status tested">Isolated</span>
            <h3>One sandbox per conversation</h3>
            <p>
              Four agents ran in four sandboxes while two jobs waited for an
              agent slot. This creates the clearest security and failure
              boundary.
            </p>
            <dl>
              <div><dt>Placement</dt><dd>{snapshot.replicatedPatterns.isolatedFour.activeAgents} active agents · {snapshot.replicatedPatterns.isolatedFour.simultaneousSandboxes} simultaneous sandboxes</dd></div>
              <div><dt>Backpressure</dt><dd>{snapshot.replicatedPatterns.isolatedFour.queuedAgents} jobs waiting for an agent slot; each starts in its own sandbox when admitted</dd></div>
              <div><dt>Measured batch time</dt><dd>{snapshot.replicatedPatterns.isolatedFour.meanWallSeconds.toFixed(1)} seconds on average</dd></div>
              <div><dt>Choose for</dt><dd>Strong isolation and untrusted work.</dd></div>
            </dl>
          </article>
          <article className="implementation-card">
            <span className="implementation-status pilot">Bounded cell</span>
            <h3>Several conversations share one sandbox</h3>
            <p>
              Four trusted agents kept separate conversation histories while
              sharing one runtime. Two additional jobs remained in the
              controller queue.
            </p>
            <dl>
              <div><dt>Placement</dt><dd>{snapshot.replicatedPatterns.groupedFour.activeAgents} active agents share {snapshot.replicatedPatterns.groupedFour.simultaneousSandboxes} sandbox</dd></div>
              <div><dt>Backpressure</dt><dd>{snapshot.replicatedPatterns.groupedFour.queuedAgents} jobs waiting for an agent slot in the same bounded cell</dd></div>
              <div><dt>Measured batch time</dt><dd>{snapshot.replicatedPatterns.groupedFour.meanWallSeconds.toFixed(1)} seconds on average</dd></div>
              <div><dt>Choose for</dt><dd>Trusted production work with separate conversation histories.</dd></div>
            </dl>
          </article>
          <article className="implementation-card">
            <span className="implementation-status next">Higher density</span>
            <h3>Six conversations share one sandbox</h3>
            <p>
              The full batch started together. Removing the queue increased
              shared-runtime contention and did not improve average completion
              time.
            </p>
            <dl>
              <div><dt>Placement</dt><dd>{snapshot.replicatedPatterns.groupedSix.activeAgents} active agents share {snapshot.replicatedPatterns.groupedSix.simultaneousSandboxes} sandbox</dd></div>
              <div><dt>Backpressure</dt><dd>{snapshot.replicatedPatterns.groupedSix.queuedAgents} jobs waiting; the full batch starts together</dd></div>
              <div><dt>Measured batch time</dt><dd>{snapshot.replicatedPatterns.groupedSix.meanWallSeconds.toFixed(1)} seconds on average</dd></div>
              <div><dt>Finding</dt><dd>Removing the queue increased contention and did not produce a wall-time win.</dd></div>
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
          The two-job queue is intentional admission control, not unused
          sandbox capacity. These tests ran on OpenHands Enterprise installed
          through Replicated; Replicated was the deployment method, not a
          separate orchestration pattern.
        </p>
      </section>

      <section className="section subagent-section">
        <div className="section-heading report-heading">
          <div>
            <p className="eyebrow">Parent and subagents: using TaskToolSet to coordinate specialist children</p>
          </div>
          <p>
            This structure keeps one parent conversation and one shared
            lifecycle. It is useful when specialists can share a workspace and
            do not need independent histories, permissions, or service levels.
          </p>
        </div>
        <div className="section-heading report-heading">
          <div>
            <p className="eyebrow">Matched comparison: the same four research tasks in three execution structures</p>
          </div>
          <p>
            Each run inspected the same four source files and had to return the
            same structured evidence. This separates delegation overhead from
            task difficulty.
          </p>
        </div>
        <div className="implementation-grid">
          <article className="implementation-card">
            <span className="implementation-status tested">Native · sequential</span>
            <h3>{snapshot.agentCanvasTaskTool.deeperComparison.sequential.wallSeconds.toFixed(1)} seconds</h3>
            <p>
              Four children ran one at a time for $
              {snapshot.agentCanvasTaskTool.deeperComparison.sequential.modelCost.toFixed(3)}.
              All four analyses were correct; three followed the strict output contract.
            </p>
          </article>
          <article className="implementation-card">
            <span className="implementation-status tested">Native · four parallel</span>
            <h3>{snapshot.agentCanvasTaskTool.deeperComparison.parallel.wallSeconds.toFixed(1)} seconds</h3>
            <p>
              Four concurrent children returned 4/4 strict contracts for $
              {snapshot.agentCanvasTaskTool.deeperComparison.parallel.modelCost.toFixed(3)}.
              This was 33.4% faster than sequential delegation.
            </p>
          </article>
          <article className="implementation-card">
            <span className="implementation-status tested">Four first-class records</span>
            <h3>{snapshot.agentCanvasTaskTool.deeperComparison.firstClass.wallSeconds.toFixed(1)} seconds</h3>
            <p>
              Four first-class Canvas conversations cost $
              {snapshot.agentCanvasTaskTool.deeperComparison.firstClass.modelCost.toFixed(3)}.
              Three followed the strict contract; each retained an independent visible record.
            </p>
          </article>
        </div>
        <div className="subagent-findings">
          <article>
            <span className="implementation-status tested">Canvas passed</span>
            <h3>A native code-explorer child performed the delegated work</h3>
            <p>
              The parent emitted {snapshot.agentCanvasTaskTool.taskActions}
              {" "}TaskAction and received{" "}
              {snapshot.agentCanvasTaskTool.taskObservations} TaskObservation
              from {snapshot.agentCanvasTaskTool.childType}. The child returned
              task ID {snapshot.agentCanvasTaskTool.taskId} and the exact
              independently known file values.
            </p>
          </article>
          <article>
            <span className="implementation-status pilot">Execution boundary</span>
            <h3>Parallel children still share the parent process and workspace</h3>
            <p>
              The four task calls were issued together and completed out of
              order, proving overlap. They shared one backend, workspace, and
              model path, so the speedup was about 1.5× rather than 4×.
            </p>
          </article>
          <article>
            <span className="implementation-status tested">Failure injection</span>
            <h3>One invalid child did not prevent its three siblings from completing</h3>
            <p>
              The parent finished after{" "}
              {snapshot.agentCanvasTaskTool.deeperComparison.failureInjection.wallSeconds.toFixed(1)}
              {" "}seconds with all{" "}
              {snapshot.agentCanvasTaskTool.deeperComparison.failureInjection.taskObservations}
              {" "}observations. The controller accepted{" "}
              {snapshot.agentCanvasTaskTool.deeperComparison.failureInjection.healthyContracts}
              {" "}healthy contracts and isolated the one injected failure for retry.
            </p>
          </article>
        </div>
        <p className="architecture-note">
          <strong>Recommended hybrid:</strong> let an external scheduler and
          experiment ledger own the campaign. Give independently retryable
          work to first-class conversations or bounded Enterprise cells, then
          use two to four native subagents inside each trusted cell for
          independent read-only exploration, testing, or synthesis. Use
          isolated sandboxes for untrusted code, conflicting writes, separate
          credentials, or failures that must remain local.
        </p>
        <details className="compact-details">
          <summary>Enterprise implementation note</summary>
          <p>
            In the tested Enterprise installation, the saved subagent setting
            did not appear in the launched agent profile. This is tracked as a
            profile integration issue; it does not change the TaskToolSet
            results measured in Agent Canvas.
          </p>
        </details>
      </section>

      <section className="section">
        <div className="section-heading report-heading">
          <div>
            <p className="eyebrow">Decision guide: use trust and operational requirements to choose the boundary</p>
          </div>
          <p>
            All four patterns can use the same external task registry,
            scheduler, validators, and experiment ledger. The execution choice
            changes isolation, agent records, failure boundaries, and
            infrastructure overhead.
          </p>
        </div>
        <div className="implementation-grid">
          <article className="implementation-card">
            <span className="implementation-status tested">Enterprise is optional</span>
            <h3>Orchestration does not require Enterprise</h3>
            <p>
              An external scheduler, durable ledger, contract validator, and
              Canvas or SDK workers can coordinate the campaign. This is the
              simplest choice for one trusted team willing to own those
              controls.
            </p>
          </article>
          <article className="implementation-card">
            <span className="implementation-status tested">Enterprise boundary</span>
            <h3>Enterprise provides operational boundaries</h3>
            <p>
              Choose it when self-hosting, separate conversation records,
              sandbox lifecycle, access controls, grouped placement, and
              operator visibility are requirements you do not want to rebuild.
            </p>
          </article>
          <article className="implementation-card">
            <span className="implementation-status tested">Conversation boundary</span>
            <h3>A conversation is a unit of ownership and recovery</h3>
            <p>
              Use fewer conversations when specialists are short-lived and
              trusted. Use first-class conversations when work needs its own
              retry, history, permissions, human handoff, or service-level
              objective.
            </p>
          </article>
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
            <p className="eyebrow">Managing and controlling OpenHands conversations</p>
          </div>
          <p>
            The Deployment section explains how OpenHands provides conversation
            and runtime infrastructure. This section covers the management
            layer around it: assignment, admission, observation, validation,
            recovery, durable records, and cleanup.
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

      <section className="section controller-section">
        <div className="section-heading report-heading">
          <div>
            <p className="eyebrow">One management loop</p>
          </div>
          <p>
            OpenHands executed the agent work. The controller selected tasks,
            limited concurrent work, validated outputs, recorded evidence,
            resumed interrupted attempts, and paused completed sandboxes.
          </p>
        </div>

        <div className="controller-map" role="img" aria-label="A single controller uses a file ledger and Git checkpoints, then assigns bounded work cells to OpenHands Enterprise, Agent Canvas, or native subagents. Multiple controllers require database leases.">
          <div className="controller-source">
            <span className="controller-kicker">Durable campaign memory</span>
            <strong>Files + Git checkpoints</strong>
            <small>4,800 attempts · 24,013 records · restartable</small>
          </div>
          <span className="controller-arrow" aria-hidden="true">→</span>
          <div className="controller-owner">
            <span className="controller-kicker">One lifecycle owner</span>
            <strong>Controller</strong>
            <small>claim · admit · validate · resume · pause</small>
          </div>
          <span className="controller-arrow" aria-hidden="true">→</span>
          <div className="controller-workers">
            <span>Enterprise conversations</span>
            <span>Agent Canvas cells</span>
            <span>Native subagents</span>
          </div>
        </div>

        <div className="controller-boundary">
          <article>
            <span className="implementation-status tested">Tested boundary</span>
            <h3>One controller can use files and Git</h3>
            <p>
              A file lock prevents a second writer. Immutable lifecycle records
              preserve the audit trail, and Git checkpoints make a scheduled
              controller tick restartable without depending on agent memory.
            </p>
          </article>
          <article>
            <span className="implementation-status next">Scale-out boundary</span>
            <h3>Several controllers need database leases</h3>
            <p>
              When controller replicas or tenants can claim work at the same
              time, use an application-owned transactional database for leases,
              idempotent claims, and heartbeats. Do not use OpenHands internal
              PostgreSQL tables as the campaign API.
            </p>
          </article>
        </div>

        <div className="comparison-grid">
          <article className="finding-card">
            <span className="finding-label">Enterprise endurance</span>
            <strong>
              {snapshot.enduranceCampaign.attempts} hourly attempts over{" "}
              {snapshot.enduranceCampaign.elapsedHours.toFixed(1)} hours.
            </strong>
            <p>
              {snapshot.enduranceCampaign.valid} valid results covered all{" "}
              {snapshot.enduranceCampaign.taskCount} tasks at a recorded model
              cost of ${snapshot.enduranceCampaign.modelCost.toFixed(2)}.
            </p>
          </article>
          <article className="finding-card">
            <span className="finding-label">Shared learning</span>
            <strong>
              {snapshot.enduranceCampaign.lessonsPromoted} validated lessons
              were promoted.
            </strong>
            <p>
              Later agents received{" "}
              {snapshot.enduranceCampaign.lessonRetrievals} lesson references.
              One final result still duplicated a known candidate.
            </p>
          </article>
          <article className="finding-card">
            <span className="finding-label">In-cluster controller</span>
            <strong>
              {snapshot.canvasController.campaignTicks} Canvas ticks completed
              with zero service restarts.
            </strong>
            <p>
              Forced controller recovery and overlapping-controller rejection
              both passed.
            </p>
          </article>
        </div>
      </section>

      <section className="section implementation-section">
        <div className="section-heading report-heading">
          <div>
            <p className="eyebrow">Four control patterns</p>
          </div>
          <p>
            These patterns use the same scheduler, validators, ledger, and
            OpenHands conversation API. The difference is what starts the
            management loop and how long it remains active.
          </p>
        </div>
        <div className="agent-table-wrap controller-model-table">
          <table className="agent-table">
            <thead>
              <tr>
                <th>Pattern</th>
                <th>How it works</th>
                <th>Use it when</th>
                <th>Evidence in this project</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>Bounded polling batch</strong></td>
                <td>
                  An external process starts a limited set of conversations,
                  polls them to terminal state, validates the results, updates
                  the ledger, cleans up, and exits.
                </td>
                <td>
                  A pipeline or operator owns a finite batch and needs an
                  inspectable end state.
                </td>
                <td>
                  <strong>Live-tested.</strong> Four documented batches covered
                  20 worker attempts; the accepted load used four active
                  conversations and queued two.
                </td>
              </tr>
              <tr>
                <td><strong>Scheduled controller tick</strong></td>
                <td>
                  On each trigger, an OpenHands automation or Kubernetes
                  CronJob loads durable campaign state, reconciles existing
                  conversations, runs one bounded unit of work, saves the
                  result, and exits. Later triggers continue the same campaign.
                </td>
                <td>
                  A campaign may contain hundreds of queued tasks, but only a
                  small bounded group needs to run during each controller tick.
                  Work can wait until the next scheduled interval.
                </td>
                <td>
                  <strong>Live-tested on both deployments.</strong> Enterprise
                  completed eight hourly campaign ticks over nine hours. The
                  in-cluster Agent Canvas controller completed six campaign
                  ticks, recovered after forced termination, and rejected an
                  overlapping controller.
                </td>
              </tr>
              <tr>
                <td><strong>Persistent reconciler</strong></td>
                <td>
                  A long-running service repeatedly checks the queue and active
                  conversations, then admits new work as capacity opens.
                </td>
                <td>
                  A sustained campaign needs faster reaction than a schedule
                  provides.
                </td>
                <td>
                  <strong>Implementation available; endurance unproven.</strong>
                  The reconciliation and restart paths were tested in bounded
                  runs, but the service was not kept running for 24 hours.
                </td>
              </tr>
              <tr>
                <td><strong>Event-triggered tick</strong></td>
                <td>
                  A queue, webhook, or completion event invokes the same
                  idempotent reconciliation instead of waiting for a timer.
                </td>
                <td>
                  Start latency matters, workload is irregular, and the
                  surrounding platform already has reliable event delivery.
                </td>
                <td>
                  <strong>Design option, not yet tested.</strong> It still needs
                  duplicate-event, missed-event, and out-of-order-event tests.
                  Periodic reconciliation remains necessary as a backstop.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p className="architecture-note">
          All four patterns must reconcile durable state before claiming work.
          A successful schedule or event trigger only shows that the controller
          started; validation and recorded terminal state determine whether the
          agent work completed.
        </p>
      </section>

      <section className="section implementation-section">
        <div className="section-heading report-heading">
          <div>
            <p className="eyebrow">Test results and current limits</p>
          </div>
          <p>
            The completed tests cover bounded batches, an unattended hourly
            campaign, and an in-cluster scheduled controller. They still use
            simplified optimization tasks rather than the full ONNX workload.
          </p>
        </div>
        <div className="agent-table-wrap controller-evidence-table">
          <table className="agent-table">
            <thead>
              <tr>
                <th>Approach</th>
                <th>Test history</th>
                <th>What it established</th>
                <th>What it did not establish</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>Bounded polling batch</strong></td>
                <td>
                  {snapshot.controllerLoad.externalValidation.documentedBatches}
                  {" "}documented controller batches covering{" "}
                  {snapshot.controllerLoad.externalValidation.workerAttempts}
                  {" "}worker attempts: two initial 6-task batches at 5/6, a{" "}
                  {snapshot.controllerLoad.externalValidation.targetedValid}/
                  {snapshot.controllerLoad.externalValidation.targetedAttempts}
                  {" "}targeted recovery test, and a final{" "}
                  {snapshot.controllerLoad.externalValidation.finalValid}/
                  {snapshot.controllerLoad.externalValidation.finalAttempts}
                  {" "}batch.
                </td>
                <td>
                  Bounded admission, queueing, grouped placement, terminal
                  response recovery, independent validation, and sandbox
                  cleanup worked together.
                </td>
                <td>
                  It was not one uninterrupted 20-attempt run, a long-running
                  service test, or a multi-controller failover test.
                </td>
              </tr>
              <tr>
                <td><strong>Scheduled controller tick</strong></td>
                <td>
                  {snapshot.controllerLoad.automationValidation.documentedRuns}
                  {" "}documented Enterprise automation runs:{" "}
                  {snapshot.controllerLoad.automationValidation.pilotRuns}
                  {" "}setup, failure, recovery, and campaign-pilot runs plus{" "}
                  {snapshot.controllerLoad.automationValidation.concurrencyRuns}
                  {" "}concurrency runs and{" "}
                  {snapshot.controllerLoad.automationValidation.recurringRuns}
                  {" "}hourly campaign ticks. Agent Canvas added{" "}
                  {snapshot.canvasController.campaignTicks}
                  {" "}in-cluster campaign ticks.
                </td>
                <td>
                  Git preserved the campaign queue, task claims, run and
                  attempt IDs, OpenHands conversation and start-task IDs,
                  validation results, and checkpoints between temporary
                  controller conversations. Enterprise completed{" "}
                  {snapshot.enduranceCampaign.valid}/
                  {snapshot.enduranceCampaign.attempts}
                  {" "}valid attempts and promoted{" "}
                  {snapshot.enduranceCampaign.lessonsPromoted}
                  {" "}lessons over{" "}
                  {snapshot.enduranceCampaign.elapsedHours.toFixed(1)}
                  {" "}hours. The Canvas controller recovered without creating
                  another conversation.
                </td>
                <td>
                  One Enterprise result artifact outlived its sandbox, but
                  recovery checked the missing sandbox before validating that
                  artifact. The final attempt also repeated a known candidate.
                  The full 400-task ONNX workload was not run.
                </td>
              </tr>
              <tr>
                <td><strong>Persistent reconciler</strong></td>
                <td>
                  The reusable supervisor and reconciliation code passed unit
                  tests. Separate bounded tests exercised restart
                  reattachment, file locking, validation, and cleanup.
                </td>
                <td>
                  The components needed by a long-running controller behave
                  correctly when invoked in bounded runs.
                </td>
                <td>
                  No continuous 24-hour run, rolling process restart, memory
                  growth test, prolonged API degradation, or queue-drain test
                  has been completed. There is no established endurance limit.
                </td>
              </tr>
              <tr>
                <td><strong>Event-triggered tick</strong></td>
                <td>
                  No live event-delivery test has been run. This pattern would
                  invoke the same tested reconciliation command.
                </td>
                <td>
                  Nothing beyond reuse of the controller contract.
                </td>
                <td>
                  Duplicate, delayed, missed, and out-of-order events remain
                  untested. Do not recommend this pattern without a periodic
                  reconciliation backstop and an event failure-injection run.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p className="architecture-note">
          The large qualification runs are complete. Before customer use, fix
          artifact-first recovery when a sandbox is missing and pass prior
          candidate hashes and approach history to the scheduler. A persistent
          24-hour service and event-delivery failures remain separate future
          tests.
        </p>
      </section>

      <section className="section implementation-section">
        <div className="section-heading report-heading">
          <div>
            <p className="eyebrow">Reusable implementations</p>
          </div>
          <p>
            The examples share the production controller code rather than
            embedding orchestration decisions in prompts.
          </p>
        </div>
        <div className="control-list">
          <article>
            <h3>Controller tick</h3>
            <p>
              One command reconciles saved state, handles one bounded unit of
              work, checkpoints the result, and exits.
            </p>
            <a href="https://github.com/rajshah4/openhands-agent-research-lab/blob/main/experiments/in-platform-controller/run_tick.py">
              View the reusable tick
            </a>
          </article>
          <article>
            <h3>OpenHands automation</h3>
            <p>
              The automation wrapper prepares the checkout and credentials,
              invokes the same controller tick, and leaves lifecycle cleanup
              to OpenHands.
            </p>
            <a href="https://github.com/rajshah4/openhands-agent-research-lab/tree/main/experiments/in-platform-controller/automation">
              View the automation package
            </a>
          </article>
          <article>
            <h3>Persistent polling</h3>
            <p>
              The supervisor repeats bounded ticks at a configured interval.
              It is intentionally small so production process management can
              be supplied by Kubernetes or another service manager.
            </p>
            <a href="https://github.com/rajshah4/openhands-agent-research-lab/blob/main/experiments/in-platform-controller/persistent_supervisor.py">
              View the polling supervisor
            </a>
          </article>
          <article>
            <h3>Agent Canvas CronJob</h3>
            <p>
              A suspended-by-default Kubernetes CronJob runs the same bounded
              controller beside Agent Canvas and stores its ledger on a
              dedicated persistent volume.
            </p>
            <a href="https://github.com/rajshah4/openhands-agent-research-lab/tree/main/experiments/agent-canvas-kubernetes/controller">
              View the in-cluster controller
            </a>
          </article>
        </div>
      </section>

      <section className="section implementation-section">
        <div className="section-heading report-heading">
          <div>
            <p className="eyebrow">Controls used</p>
          </div>
          <p>
            These safeguards are part of the controller and apply to every
            execution pattern.
          </p>
        </div>
        <div className="control-list">
          {controls.map(([title, copy]) => (
            <article key={title}>
              <h3>{title}</h3>
              <p>{copy}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="section comparison">
        <div className="section-heading report-heading">
          <div>
            <p className="eyebrow">Restart recovery after the controller stopped during an active run</p>
          </div>
          <p>
            Enterprise recovery reattached to the original start task. The
            Agent Canvas test then force-deleted its controller after the child
            ID was durable; the replacement attached to that same conversation
            and did not launch another one.
          </p>
        </div>
        <div className="comparison-grid">
          <article className="finding-card">
            <span className="finding-label">Recovery result</span>
            <strong>Both controller placements resumed existing work.</strong>
            <p>
              Enterprise preserved its start task. Agent Canvas recorded an
              explicit recovery marker after zero-grace controller termination.
            </p>
          </article>
          <article className="finding-card">
            <span className="finding-label">Large ledger</span>
            <strong>{formatNumber(snapshot.robustness.attempts)} attempts in {snapshot.robustness.elapsedSeconds.toFixed(2)} seconds.</strong>
            <p>{formatNumber(snapshot.robustness.records)} parseable records occupied {snapshot.robustness.storeMb} MB.</p>
          </article>
          <article className="finding-card">
            <span className="finding-label">Overlap result</span>
            <strong>The second Canvas controller was rejected before launching work.</strong>
            <p>
              Files support one active owner. Several active controllers still
              require application-owned database leases.
            </p>
          </article>
        </div>
      </section>
    </>
  );
}

export function ResearchDashboard({ snapshot }: { snapshot: Snapshot }) {
  const [view, setView] = useState<View>("Overview");

  return (
    <main>
      <header className="topbar">
        <a className="brand" href="#top" aria-label="Research Lab home">
          <span className="brand-mark">N</span>
          <span>
            <strong>NeuroGolf with OpenHands</strong>
            <small>Reproducing a Kaggle multi-agent workflow</small>
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
          <p className="eyebrow">A Kaggle competition workload reproduced with OpenHands</p>
          <h1>NeuroGolf required solving and optimizing 400 separate ARC tasks.</h1>
          <p className="lede">
            NeuroGolf 2026 was a Kaggle competition in which each task needed a
            correct ONNX program. The rules did not require agents, but the 400
            independent problems made parallel agent work useful. This project
            reproduces the system needed to assign that work, check results,
            retain experiment history, share validated lessons, and manage the
            OpenHands runtimes.
          </p>
          <div className="hero-actions">
            <a href="#overview" className="primary-action">
              How the work was structured
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

        <aside className="capacity-card" aria-label="NeuroGolf competition summary">
          <div className="card-heading">
            <span>NeuroGolf workload</span>
            <span className="status-badge healthy">Kaggle 2026</span>
          </div>
          <div className="capacity-number">
            <strong>400</strong>
            <span>separate ARC tasks</span>
          </div>
          <dl className="capacity-details">
            <div>
              <dt>Required output</dt>
              <dd>One ONNX program per task</dd>
            </div>
            <div>
              <dt>Correctness</dt>
              <dd>Match the ARC transformation</dd>
            </div>
            <div>
              <dt>Optimization</dt>
              <dd>Reduce memory and parameters</dd>
            </div>
            <div>
              <dt>Work structure</dt>
              <dd>Independent tasks, shared research process</dd>
            </div>
          </dl>
          <p className="capacity-note">
            Different tasks could be attempted in parallel. The coordination
            problem was making sure every task received work, candidates were
            checked consistently, and useful results were retained.
          </p>
        </aside>
      </section>

      <section className="proof-strip" aria-label="Proof summary">
        <div>
          <span>Competition tasks</span>
          <strong>{snapshot.portfolioScale.tasks}</strong>
          <small>separate ARC problems</small>
          <div className="mini-meter">
            <span style={{ width: pct(1) }} />
          </div>
        </div>
        <div>
          <span>Attempts recorded</span>
          <strong>{formatNumber(snapshot.portfolioScale.totalAttempts)}</strong>
          <small>across two matched organizations</small>
        </div>
        <div>
          <span>Tasks receiving work</span>
          <strong>400/400</strong>
          <small>in the orchestration test</small>
        </div>
        <div>
          <span>Attempts per task</span>
          <strong>{snapshot.portfolioScale.exactAttemptsPerTask}</strong>
          <small>for every one of the 400 tasks</small>
        </div>
      </section>

      {view === "Overview" && <OverviewGuide snapshot={snapshot} />}

      {false && (
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

      {view === "How we tested" && <TestMethodGuide snapshot={snapshot} />}

      {view === "Scaling" && <CompetitionPlanner snapshot={snapshot} />}

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
              <p className="eyebrow">Implementation issues</p>
              <h2>The tests exposed six issues in the controller workflow.</h2>
            </div>
            <p>
              Four are resolved in the current implementation. Two remain open
              after the endurance campaign and are described with their
              required fixes.
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
          <p className="eyebrow">Remaining work</p>
          <h2>Steps required for a full NeuroGolf reproduction.</h2>
        </div>
        <ol>
          <li>
            <span>✓</span>
            Keep the orchestration, capacity, restart, and endurance results as
            the working reference.
          </li>
          <li>
            <span>1</span>
            Validate a terminal Git artifact before checking whether its
            original sandbox still exists.
          </li>
          <li>
            <span>2</span>
            Pass prior candidate hashes and approach history to the scheduler
            so a later agent does not repeat an experiment.
          </li>
          <li>
            <span>3</span>
            Add a licensed ONNX workload adapter with official, fresh,
            adversarial, and metamorphic validation.
          </li>
          <li>
            <span>4</span>
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
