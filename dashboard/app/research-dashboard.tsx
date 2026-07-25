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

const views = ["Story", "Operations", "Memory"] as const;
type View = (typeof views)[number];

function pct(value: number) {
  return `${Math.round(value * 100)}%`;
}

function shortId(value: string) {
  return value.length > 12 ? `${value.slice(0, 8)}…` : value;
}

export function ResearchDashboard({ snapshot }: { snapshot: Snapshot }) {
  const [view, setView] = useState<View>("Story");
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
            <strong>NeuroGolf Lab</strong>
            <small>OpenHands research organization</small>
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
          <p className="eyebrow">Evidence, not agent theater</p>
          <h1>From a swarm of agents to a learning organization.</h1>
          <p className="lede">
            Every experiment is scheduled, independently validated, traced to
            its conversation, and converted into memory only when the evidence
            improves.
          </p>
          <div className="hero-actions">
            <a href="#live-agents" className="primary-action">
              Inspect the live proof
            </a>
            <a
              href="https://github.com/rajshah4/openhands-agent-research-lab"
              className="text-action"
            >
              View the public repository <span aria-hidden="true">↗</span>
            </a>
          </div>
        </div>

        <aside className="capacity-card" aria-label="Rajistics capacity">
          <div className="card-heading">
            <span>Rajistics capacity</span>
            <span
              className={`status-badge ${
                snapshot.capacity.launchAllowed ? "healthy" : "blocked"
              }`}
            >
              {snapshot.capacity.launchAllowed ? "Launch safe" : "Launch locked"}
            </span>
          </div>
          <div className="capacity-number">
            <strong>{snapshot.capacity.active}</strong>
            <span>/ {snapshot.capacity.limit} runtimes</span>
          </div>
          <div className="meter" aria-label={`${pct(utilization)} capacity used`}>
            <span style={{ width: pct(utilization) }} />
          </div>
          <dl className="capacity-details">
            <div>
              <dt>Batch guard</dt>
              <dd>Lock at {snapshot.capacity.launchAtOrAbove} active</dd>
            </div>
            <div>
              <dt>New concurrency</dt>
              <dd>≤ {snapshot.capacity.maxNewConcurrent} workers</dd>
            </div>
            <div>
              <dt>Memory available</dt>
              <dd>{snapshot.capacity.memoryAvailable}</dd>
            </div>
            <div>
              <dt>Unhealthy pods</dt>
              <dd>{snapshot.capacity.unhealthyPods}</dd>
            </div>
          </dl>
          <p className="capacity-note">
            Completed sandboxes pause automatically. Conversation history and
            research evidence remain available.
          </p>
        </aside>
      </section>

      <section className="proof-strip" aria-label="Proof summary">
        <div>
          <span>Deterministic tests</span>
          <strong>{snapshot.proof.tests}</strong>
          <small>all passing</small>
        </div>
        <div>
          <span>Recent live attempts</span>
          <strong>
            {snapshot.proof.validAttempts}/{snapshot.proof.liveAttempts}
          </strong>
          <small>independently valid</small>
        </div>
        <div>
          <span>Invalid memory</span>
          <strong>{snapshot.proof.invalidLessons}</strong>
          <small>promotion is gated</small>
        </div>
        <div>
          <span>Scale benchmark</span>
          <strong>
            {snapshot.proof.tasks}/{snapshot.proof.targetTasks}
          </strong>
          <small>tasks prepared</small>
          <div className="mini-meter">
            <span style={{ width: pct(taskProgress) }} />
          </div>
        </div>
      </section>

      {view === "Story" && (
        <>
          <section className="section narrative">
            <div className="section-heading">
              <div>
                <p className="eyebrow">The organizational loop</p>
                <h2>One worker. One contract. One earned lesson.</h2>
              </div>
              <p>
                OpenHands owns isolated execution. The lab owns allocation,
                validation, memory, and the evidence ledger.
              </p>
            </div>
            <div className="workflow">
              {[
                ["01", "Select", "Scheduler chooses the next useful experiment."],
                ["02", "Retrieve", "Only validated, relevant lessons enter context."],
                ["03", "Execute", "One isolated OpenHands conversation does the work."],
                ["04", "Validate", "Deterministic checks, never worker confidence."],
                ["05", "Promote", "Improving evidence becomes reusable memory."],
              ].map(([number, title, copy]) => (
                <article className="workflow-step" key={number}>
                  <span>{number}</span>
                  <h3>{title}</h3>
                  <p>{copy}</p>
                </article>
              ))}
            </div>
          </section>

          <section className="section comparison">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Matched live pilot</p>
                <h2>Same budget. Different organization.</h2>
              </div>
              <p>
                Both arms used the same six tasks and budget. The validator
                exposed two managed prompt-contract failures that a confidence
                score would have missed.
              </p>
            </div>
            <div className="comparison-grid">
              {(["naive", "managed"] as const).map((name) => {
                const result = snapshot.comparison[name];
                return (
                  <article className={`arm-card ${name}`} key={name}>
                    <div className="arm-title">
                      <span>{name === "naive" ? "Baseline" : "Learning system"}</span>
                      <h3>{name[0].toUpperCase() + name.slice(1)}</h3>
                    </div>
                    <dl>
                      <div>
                        <dt>Problems solved</dt>
                        <dd>{result.solved}/{snapshot.comparisonTaskCount}</dd>
                      </div>
                      <div>
                        <dt>Solution quality</dt>
                        <dd>{result.quality.toFixed(3)}</dd>
                      </div>
                      <div>
                        <dt>Quality AUC</dt>
                        <dd>{result.qualityAuc.toFixed(3)}</dd>
                      </div>
                      <div>
                        <dt>Lessons retrieved</dt>
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
                <span className="finding-label">Honest finding</span>
                <strong>Validation found a prompt defect, then proved its fix.</strong>
                <p>
                  Placeholder item IDs invalidated two managed candidates. A
                  corrected two-conversation regression then validated 2/2 at
                  the optimal score.
                </p>
              </article>
            </div>
          </section>
        </>
      )}

      {(view === "Story" || view === "Operations") && (
        <section className="section" id="live-agents">
          <div className="section-heading agents-heading">
            <div>
              <p className="eyebrow">Experiment ledger</p>
              <h2>Every agent leaves a verifiable trail.</h2>
            </div>
            <div className="filter-row" aria-label="Filter experiments">
              {["all", "naive", "managed", "regression"].map((item) => (
                <button
                  className={arm === item ? "active" : ""}
                  key={item}
                  onClick={() => setArm(item)}
                  type="button"
                >
                  {item}
                </button>
              ))}
            </div>
          </div>
          <div className="agent-table-wrap">
            <table className="agent-table">
              <thead>
                <tr>
                  <th>Worker</th>
                  <th>Organization</th>
                  <th>Task</th>
                  <th>Score</th>
                  <th>Memory</th>
                  <th>Contract</th>
                  <th>Sandbox</th>
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
                        {agent.arm}
                      </span>
                    </td>
                    <td>{agent.task}</td>
                    <td>
                      <strong>{agent.score ?? "invalid"}</strong>
                      <small> / target {agent.target}</small>
                    </td>
                    <td>{agent.lessons ? `${agent.lessons} retrieved` : "none"}</td>
                    <td>{agent.transport.replaceAll("-", " ")}</td>
                    <td>
                      <span className="paused-dot" />
                      {agent.sandbox}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {(view === "Story" || view === "Memory") && (
        <section className="section memory-section">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Memory provenance</p>
              <h2>Claims do not become memory. Evidence does.</h2>
            </div>
            <p>
              Every lesson points backward to a valid improvement and forward
              to the workers that received it.
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
              <span>Promotion rule</span>
              <strong>valid ∧ improving ∧ traceable</strong>
              <p>
                Proposed lessons that fail any condition remain in the attempt
                record and never enter retrieval.
              </p>
            </article>
          </div>
        </section>
      )}

      {view === "Operations" && (
        <section className="section">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Reliability learning</p>
              <h2>Failures became controls.</h2>
            </div>
            <p>
              The ledger preserves intermediate failures so compatibility work
              becomes reusable infrastructure.
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
          <p className="eyebrow">Next proof gate</p>
          <h2>Observable scale, without overwhelming the demo cluster.</h2>
        </div>
        <ol>
          <li>
            <span>1</span>
            Repeat the live comparison across three matched seeds.
          </li>
          <li>
            <span>2</span>
            Add harder instances that separate model strategy quality.
          </li>
          <li>
            <span>3</span>
            Add application-owned PostgreSQL only when controllers become
            concurrent.
          </li>
        </ol>
      </section>

      <footer>
        <div>
          <strong>NeuroGolf Lab</strong>
          <span>OpenHands is the execution plane. Evidence is the memory.</span>
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
