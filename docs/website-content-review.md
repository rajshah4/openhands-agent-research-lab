# NeuroGolf website content review

This document turns the website into a linear editorial outline. It is meant
for deciding what belongs on the site and why before polishing individual
sentences.

## How to give feedback

For each section, mark one:

- `[ ] Keep`
- `[ ] Change`
- `[ ] Move`
- `[ ] Remove`

Then write comments under **Feedback**. Short comments are enough:

- “I do not understand why this is here.”
- “Move this to Results.”
- “Keep the data, but remove the explanation.”
- “This repeats the previous section.”
- “Use the detailed table instead.”
- “This needs a concrete example.”

The most useful first pass is structural. Decide which sections belong, their
order, and what question each should answer. Copyediting can happen after that.

---

# Global material

This material currently appears above every page, not only on Overview.

## G1. NeuroGolf introduction

**Current headline:**  
“NeuroGolf required solving and optimizing 400 separate ARC tasks.”

**Intended purpose:**  
Explain immediately that NeuroGolf was a Kaggle competition, what competitors
had to produce, and why 400 separate tasks made parallel work useful.

**Current supporting information:**

- NeuroGolf 2026 was a Kaggle competition.
- Each task required a correct ONNX program.
- The rules did not require agents.
- The project reproduces assignment, validation, history, learning, and runtime
  management.

- [ ] Keep
- [ ] Change
- [ ] Move
- [ ] Remove

**Feedback:**

> 

## G2. Competition summary card

**Intended purpose:**  
Give a compact definition of the workload:

- 400 ARC tasks
- one ONNX program per task
- correctness before optimization
- independent tasks with a shared research process

- [ ] Keep
- [ ] Change
- [ ] Move
- [ ] Remove

**Feedback:**

> 

## G3. Four-number summary

**Current numbers:**

- 400 competition tasks
- 9,600 recorded attempts
- 400/400 tasks receiving work
- 12 attempts per task

**Intended purpose:**  
State the scale of the deterministic orchestration test before discussing its
implementation.

**Question to consider:**  
Should this appear on every page, or only on Overview and Results?

- [ ] Keep
- [ ] Change
- [ ] Move
- [ ] Remove

**Feedback:**

> 

---

# Overview

The Overview is intended to answer:

1. What was NeuroGolf?
2. Why did the workload benefit from multiple agents?
3. What did this project reproduce?
4. How does it compare with actual competition teams?

## O1. What the Kaggle competition required

**Intended purpose:**  
Explain the actual problem before discussing agents or OpenHands.

**Current emphasis:**

- 400 independent implementation problems
- correctness first, then graph efficiency
- many possible candidate implementations per task

- [ ] Keep
- [ ] Change
- [ ] Move
- [ ] Remove

**Feedback:**

> 

## O2. The three parts of a multi-agent system

**Current headline:**  
“Controller, execution, and memory solve different problems.”

**Intended purpose:**  
Introduce the framework used by the rest of the site.

**Definitions:**

- **Controller:** selects, assigns, limits, observes, validates, retries, and
  stops work.
- **Execution:** runs agents using an appropriate conversation, sandbox, and
  isolation boundary.
- **Memory:** retains task state, attempts, candidates, failures, artifacts, and
  validated lessons.

- [ ] Keep
- [ ] Change
- [ ] Move
- [ ] Remove

**Feedback:**

> 

## O3. Why teams used multiple agents

**Intended purpose:**  
Explain that parallel work was useful but did not remove the need for central
coordination.

**Current process shown:**

1. Register tasks
2. Assign attempts
3. Run experiments
4. Validate results
5. Record findings

**Question to consider:**  
Does this repeat the Controller–Execution–Memory framework, or does it make the
framework concrete?

- [ ] Keep
- [ ] Change
- [ ] Move
- [ ] Remove

**Feedback:**

> 

## O4. What this project reproduced

**Intended purpose:**  
Separate the orchestration reproduction from a full ONNX competition solver.

**Current evidence:**

- all 400 tasks received work
- 9,600 attempt records were retained
- the same control path could run licensed NeuroGolf builders later

- [ ] Keep
- [ ] Change
- [ ] Move
- [ ] Remove

**Feedback:**

> 

## O5. Scope of the test

**Intended purpose:**  
State what remains before this becomes a full NeuroGolf reproduction.

**Current remaining areas:**

- licensed ONNX builders and competition validators
- database leases and artifact storage for concurrent controllers
- candidate quarantine, independent audit, and release assembly

**Question to consider:**  
Should this stay near the beginning or move entirely to Results?

- [ ] Keep
- [ ] Change
- [ ] Move
- [ ] Remove

**Feedback:**

> 

## O6. Where the orchestration lived

**Intended purpose:**  
Explain which responsibilities belonged to the application, OpenHands, and the
human operator.

**Current division:**

- **Application:** controller policy, registry, ledger, validation, promotion,
  capacity, and cleanup decisions
- **OpenHands:** model/tool loop, conversations, subagents, workspaces,
  sandboxes, events, usage, and pause controls
- **Human:** goals, risk limits, stopping rules, review, and release authority

**Question to consider:**  
Would this be clearer as Controller / Execution / Memory instead of
Application / OpenHands / Human?

- [ ] Keep
- [ ] Change
- [ ] Move
- [ ] Remove

**Feedback:**

> 

## O7. Comparison with public NeuroGolf solutions

**Intended purpose:**  
Show that competition teams built similar persistent research pipelines around
general coding agents.

**Current examples:**

- winning-team campaign pipeline
- third-place file and Codex/ChatGPT handoffs
- ninth-place resumable Codex scheduler
- task-ownership lesson from another team

**Current conclusion:**  
OpenHands can replace some process, conversation, sandbox, event, and operator
glue. It does not replace the domain knowledge, ONNX builders, validators,
scheduling policy, or promotion logic.

- [ ] Keep
- [ ] Change
- [ ] Move
- [ ] Remove

**Feedback:**

> 

---

# Controller

The Controller page is intended to answer:

1. What does the controller do?
2. Where can the controller run?
3. What control patterns were tested?
4. How does it recover and prevent duplicate work?

## C1. Controller introduction

**Current headline:**  
“The controller turns individual agent runs into one managed campaign.”

**Current lifecycle:**

1. Claim
2. Start
3. Observe
4. Validate
5. Commit
6. Release capacity

- [ ] Keep
- [ ] Change
- [ ] Move
- [ ] Remove

**Feedback:**

> 

## C2. One management loop

**Intended purpose:**  
Show the relationship between durable state, one lifecycle owner, and the
available OpenHands execution structures.

**Current boundary:**

- one controller can use files and Git
- concurrent controllers require application-owned database leases

**Current measured summaries:**

- Enterprise endurance campaign
- eight scheduled controller ticks
- Agent Canvas in-cluster controller

- [ ] Keep
- [ ] Change
- [ ] Move
- [ ] Remove

**Feedback:**

> 

## C3. Four controller patterns

**Patterns currently compared:**

1. Bounded polling batch
2. Scheduled controller tick
3. Persistent reconciler
4. Event-triggered tick

**Intended purpose:**  
Explain that the same controller logic can be invoked in different ways.

**Current comparison dimensions:**

- how it works
- when to use it
- evidence available in this project

- [ ] Keep
- [ ] Change
- [ ] Move
- [ ] Remove

**Feedback:**

> 

## C4. Controller test results and limits

**Intended purpose:**  
Distinguish tested behavior from design options.

**Current evidence:**

- four bounded batches covering 20 worker attempts
- 17 Enterprise automation runs, including eight hourly ticks
- six Agent Canvas controller ticks
- restart and overlap protection

**Current unproven areas:**

- continuous 24-hour reconciler
- prolonged API degradation
- multi-controller database failover
- duplicate, delayed, missed, and out-of-order events

- [ ] Keep
- [ ] Change
- [ ] Move
- [ ] Remove

**Feedback:**

> 

## C5. Reusable controller implementations

**Current code links:**

- bounded controller tick
- OpenHands automation package
- persistent polling supervisor
- Agent Canvas Kubernetes CronJob

**Intended purpose:**  
Make the work reusable instead of presenting only results.

- [ ] Keep
- [ ] Change
- [ ] Move
- [ ] Remove

**Feedback:**

> 

## C6. Controls used

**Current controls:**

- single controller owner
- stable identities
- resume instead of duplicate
- independent validation
- validated memory
- backpressure
- explicit cleanup

**Question to consider:**  
Is this useful as a separate section, or should each control be explained where
it appears in the controller lifecycle?

- [ ] Keep
- [ ] Change
- [ ] Move
- [ ] Remove

**Feedback:**

> 

## C7. Restart and overlap tests

**Intended purpose:**  
Show that controllers could resume existing work and reject a second owner.

**Current evidence:**

- Enterprise resumed the original start task
- Agent Canvas resumed the existing conversation after forced termination
- a second Canvas controller was rejected before launching work
- a 4,800-attempt ledger remained parseable

- [ ] Keep
- [ ] Change
- [ ] Move
- [ ] Remove

**Feedback:**

> 

---

# Execution

The Execution page is intended to answer:

1. Where do agents run?
2. Which boundaries does OpenHands provide?
3. What are the isolation, capacity, recovery, and management tradeoffs?

## E1. Four execution structures

**Structures currently introduced:**

1. Enterprise isolated conversations
2. Enterprise grouped conversations
3. Agent Canvas
4. Parent conversation with subagents

**Intended purpose:**  
Introduce the four options before showing their detailed results.

- [ ] Keep
- [ ] Change
- [ ] Move
- [ ] Remove

**Feedback:**

> 

## E2. Comparison table

**Current dimensions:**

- conversation record
- runtime boundary
- isolation
- best fit
- primary tradeoff
- measured cost
- concurrency

**Intended purpose:**  
Provide one compact comparison before the detailed sections.

- [ ] Keep
- [ ] Change
- [ ] Move
- [ ] Remove

**Feedback:**

> 

## E3. Agent Canvas detail

**Intended purpose:**  
Explain how Agent Canvas differs from Enterprise:

- one shared backend and workspace
- lower runtime overhead for trusted work
- application-owned capacity and access boundary
- independent agent records without separate sandboxes

**Current evidence:**

- shared six-agent load
- matched 18-attempt comparison
- cluster setup and operating-cost estimate

- [ ] Keep
- [ ] Change
- [ ] Move
- [ ] Remove

**Feedback:**

> 

## E4. Enterprise isolated and grouped conversations

**Intended purpose:**  
Explain the Enterprise flexibility between one sandbox per conversation and
multiple trusted conversations in a shared sandbox.

**Current measured configurations:**

- four active isolated conversations, two queued
- four active grouped conversations, two queued
- six active grouped conversations

**Current conclusion:**  
Four active grouped conversations were the recommended starting point for one
trusted team on the tested installation.

- [ ] Keep
- [ ] Change
- [ ] Move
- [ ] Remove

**Feedback:**

> 

## E5. Parent and subagents

**Intended purpose:**  
Explain when delegated specialists inside one parent are simpler than separate
first-class conversations.

**Current tradeoff:**  
Lower infrastructure and record overhead, but a shared workspace, lifecycle,
and audit boundary.

- [ ] Keep
- [ ] Change
- [ ] Move
- [ ] Remove

**Feedback:**

> 

## E6. Matched subagent comparison

**Structures compared:**

- sequential delegation
- parallel delegation
- four first-class Canvas conversations

**Additional test:**  
One invalid child did not prevent three siblings from completing.

**Question to consider:**  
Are these numbers useful to the decision, or is the qualitative tradeoff
enough?

- [ ] Keep
- [ ] Change
- [ ] Move
- [ ] Remove

**Feedback:**

> 

## E7. Execution decision guide

**Current decision questions:**

- Can agents share trust, files, and compute?
- Does each agent need its own history?
- How much work may fail together?
- How many sandboxes can the cluster sustain?
- Who owns runtime cleanup and recycling?

**Intended purpose:**  
End the page with a practical selection process rather than another result
table.

- [ ] Keep
- [ ] Change
- [ ] Move
- [ ] Remove

**Feedback:**

> 

---

# Memory

The Memory page is intended to answer:

1. What must survive between agent runs?
2. When are files and Git sufficient?
3. When is an application database required?
4. How does validated learning work?

## M1. Memory introduction

**Current headline:**  
“Durable state lets separate agent runs behave like one research campaign.”

**Current memory model:**

1. Task registry
2. Attempt ledger
3. Candidate and approach history
4. Validated lessons
5. Controller checkpoint

- [ ] Keep
- [ ] Change
- [ ] Move
- [ ] Remove

**Feedback:**

> 

## M2. Storage boundary

**Current recommendation:**

- files and Git for one controller
- application-owned database for concurrent controllers
- do not manipulate OpenHands internal PostgreSQL tables

**Intended purpose:**  
Answer the original question about whether a separate database is always
necessary.

- [ ] Keep
- [ ] Change
- [ ] Move
- [ ] Remove

**Feedback:**

> 

## M3. Memory evidence

**Current evidence:**

- 4,800 stored attempts and 24,013 parseable records
- six lessons promoted after validation
- seven lesson references supplied to later workers
- one duplicate candidate despite receiving lessons

**Current conclusion:**  
Validated lessons are useful but insufficient. Candidate hashes and approach
history are also needed to prevent duplicate experimentation.

- [ ] Keep
- [ ] Change
- [ ] Move
- [ ] Remove

**Feedback:**

> 

## M4. Example validated lessons

**Intended purpose:**  
Show concrete examples of provenance:

- what the lesson said
- which attempt earned it
- which later attempt received it
- why it was eligible for promotion

**Question to consider:**  
Do the examples help explain the mechanism, or are they too specific to the
small deterministic benchmark?

- [ ] Keep
- [ ] Change
- [ ] Move
- [ ] Remove

**Feedback:**

> 

---

# Results

The Results page is intended to answer:

1. What exactly was tested?
2. What did each test establish?
3. What broke?
4. What remains before a full NeuroGolf campaign?

## R1. Combined test summary

**Current test groups:**

- OpenHands execution path
- managed versus independent agents
- limits of the small-problem comparison
- nine-hour Enterprise endurance campaign
- Agent Canvas controller recovery and overlap test

**Intended purpose:**  
Provide one place where readers can distinguish measurements from
extrapolations and untested claims.

- [ ] Keep
- [ ] Change
- [ ] Move
- [ ] Remove

**Feedback:**

> 

## R2. Implementation issues

**Resolved issues currently shown:**

- agents wrapped answers in prose
- final answers arrived after the first completion signal
- finished workspaces remained active
- agents copied an example ID

**Open issues currently shown:**

- a terminal Git artifact outlived its sandbox
- validated lessons did not prevent a duplicate candidate

**Question to consider:**  
Should resolved implementation bugs remain on the main report, move to a
technical appendix, or be removed?

- [ ] Keep
- [ ] Change
- [ ] Move
- [ ] Remove

**Feedback:**

> 

## R3. Remaining work

**Current list:**

1. Validate terminal Git artifacts before requiring the original sandbox.
2. Pass candidate hashes and approach history to the scheduler.
3. Add licensed ONNX builders and adversarial validation.
4. Add database leases only when concurrent controllers are required.

- [ ] Keep
- [ ] Change
- [ ] Move
- [ ] Remove

**Feedback:**

> 

---

# Scaling

The Scaling page is intended to answer:

“What infrastructure and time would a full 400-task campaign require?”

## S1. Adjustable campaign assumptions

**Current controls:**

- attempts per task
- number of parallel cells
- workload multiplier
- estimated model cost per attempt
- artifact size per attempt

- [ ] Keep
- [ ] Change
- [ ] Move
- [ ] Remove

**Feedback:**

> 

## S2. Isolated execution estimate

**Intended purpose:**  
Estimate time and sandbox capacity when each active agent receives its own
sandbox.

- [ ] Keep
- [ ] Change
- [ ] Move
- [ ] Remove

**Feedback:**

> 

## S3. Grouped execution estimate

**Intended purpose:**  
Estimate time and sandbox capacity when four trusted agents share each bounded
sandbox cell.

- [ ] Keep
- [ ] Change
- [ ] Move
- [ ] Remove

**Feedback:**

> 

## S4. Shared production requirements

**Current estimates:**

- total jobs
- model spend
- artifact storage
- ledger events
- worker slots with headroom
- API polling pressure

**Question to consider:**  
Which of these numbers help a reader make a decision, and which create
precision without enough evidence?

- [ ] Keep
- [ ] Change
- [ ] Move
- [ ] Remove

**Feedback:**

> 

---

# Whole-site questions

These decisions will have more impact than editing individual sentences.

## 1. Intended reader

Who should understand the report without other context?

> 

## 2. Primary question

What is the single question the website should answer?

> 

## 3. Required conclusion

What should a reader believe or know after reviewing the site?

> 

## 4. Evidence threshold

Which claims need measured numbers, and which are better presented as
qualitative architecture guidance?

> 

## 5. Technical depth

Should detailed test histories and implementation issues appear in the main
report, a collapsible appendix, or only in the repository?

> 

## 6. Global material

Should the NeuroGolf introduction and four-number summary appear on every page
or only on Overview?

> 

## 7. Final page order

Current order:

1. Overview
2. Controller
3. Execution
4. Memory
5. Results
6. Scaling

Preferred order:

> 

## 8. Sections to remove immediately

> 

## 9. Missing sections

> 

## 10. Phrases or presentation patterns to avoid

> 
