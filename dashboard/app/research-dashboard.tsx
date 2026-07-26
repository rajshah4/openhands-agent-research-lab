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

const views = ["Overview", "Runs", "Lessons"] as const;
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
              <dd>{snapshot.capacity.maxNewConcurrent} agent</dd>
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
              My default recommendation is the middle option:{" "}
              <strong>FEWEST_CONVERSATIONS with four active agents per sandbox</strong>.
              Keep separate runtimes for untrusted work. Raise the shared limit
              only after a matched load test. Agent Canvas remains a lighter
              single-team backend, and the SDK remains the custom-product path;
              neither replaces the Enterprise identity and lifecycle controls
              measured here. The experiment ledger stays outside the OpenHands
              internal database.
            </p>
          </section>
        </>
      )}

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
          <h2>The next run needs harder problems.</h2>
        </div>
        <ol>
          <li>
            <span>✓</span>
            Keep this version as the working reference: 36/36 valid agent runs.
          </li>
          <li>
            <span>1</span>
            Add problems where an earlier technique can change the final score.
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
