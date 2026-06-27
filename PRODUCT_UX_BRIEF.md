# Line Guardian / Ops Guardian Product and UX Brief

This document summarizes what the repository currently builds, the core product
features, why those features exist, and what a clean production-grade UX should
support next.

## 1. Product Summary

Line Guardian is a backend-first hackathon demo for a video-native preventive AI
shift supervisor in industrial operations.

The core idea is not "detect what already happened." The product is meant to
watch a bounded operations zone, understand what is happening now, predict what
is likely to happen next, intervene through approved operational tools, verify
that the intervention reduced risk, and write an auditable shift handover.

The current implementation uses seeded demo scenarios, mock operational data,
policy documents, a FastAPI backend, SQLite run storage, model adapters, a tool
execution layer, and a thin browser console.

## 2. Why This Product Exists

Industrial supervisors work across fragmented signals:

- Camera feeds.
- Radios and area lead alerts.
- WMS order status.
- MES line events.
- CMMS maintenance history.
- Access-control logs.
- SOPs, emergency action plans, and security policies.
- Human observation and shift handover notes.

Most AI systems in this space are narrow detectors: PPE detection, object
detection, video summarization, defect classification, or incident reporting.
Line Guardian is trying to own a broader operational role:

1. Observe the current zone.
2. Predict short-horizon safety, operations, quality, security, or emergency
   risk.
3. Choose the least disruptive safe intervention.
4. Execute or simulate approved tools.
5. Verify whether the risk changed.
6. Preserve evidence and produce a handover.

This is why the repository contains not just video and model code, but SOPs,
mock enterprise systems, policy gates, emergency payloads, evidence records,
action queues, scorecards, and handover generation.

## 3. Current User Promise

For an operations manager, shift lead, safety officer, quality lead, maintenance
lead, or security lead, the app should answer:

- What is happening now?
- What is likely to happen next?
- What risk matters most?
- Why does the system believe this?
- What action did it take or recommend?
- Was that action allowed by policy?
- Did the action reduce the risk?
- What remains unresolved for the next shift?

The UX should therefore feel like an operational command surface, not a model
playground.

## 4. What Is Built Today

### Backend

- FastAPI app in `ops_guardian/app.py`.
- Health, scenario, run, step, complete, handover, and reset endpoints.
- Main local entry point through `main.py` or `ops-guardian`.
- Default console route at `/console`.

### Scenario Runner

- `ScenarioRunner` starts, steps, completes, retrieves, and resets runs.
- Each step samples a video window, optionally runs perception, asks the model
  adapter to analyze the scene, asks the planner for risks and tools, executes
  tools, records state, and completes scorecard/handover when max steps are hit.
- Run state includes observations, risks, evidence, tool calls, actions,
  emergency incidents, handover, and scorecard.

### Video Input

- `VideoSampler` samples 5-second windows by default.
- If an MP4 exists and OpenCV is installed, it extracts three JPEG frames and
  stores base64 image payloads for the live model path.
- If video files are missing, it emits placeholder frame references so the demo
  remains runnable.

### Optional Perception Layer

- `Perceptor` can run YOLO detection and pose models when `ENABLE_PERCEPTION`
  is enabled and optional dependencies/model files are present.
- It produces measured facts such as object counts, person count, vehicle count,
  posture state, torso angle, and motionless duration.
- The rest of the system degrades gracefully when perception is disabled,
  dependencies are missing, or clips are absent.

### Model Adapters

- `MockScenarioAdapter` gives deterministic scenario behavior for demos and
  tests.
- `OpenAICompatibleAdapter` calls an OpenAI-compatible chat completions endpoint.
- The live adapter can attach sampled images as multimodal `image_url` content.
- Scene and planning responses are validated through Pydantic schemas, with a
  retry after parse or schema-validation failure.

### Risk Model

- Risks have severity `P0` through `P3`, probability, confidence, optional
  time-to-event, status, evidence IDs, policy IDs, recommended actions, and
  actions taken.
- `ops_guardian/scoring.py` implements the PRD formula:

```text
risk_score = severity * probability * exposure * time_urgency * confidence
```

- The live risk board ranks by this score when available.

### Tool and Policy Layer

The `ToolRegistry` models what the agent can do:

- Retrieve SOPs, emergency plans, security policy, site map, WMS, MES, CMMS, and
  access-control context.
- Activate a simulated warning beacon.
- Send radio, shift lead, safety officer, quality lead, security, and onsite
  responder notifications.
- Create preventive tasks.
- Pause work release.
- Create quality holds.
- Request simulated safe stops.
- Schedule rechecks.
- Open emergency incident cards.
- Make mock EMS, fire, or police calls.
- Verify risk reduction.
- Generate live risk board, scorecard, and handover.

The authority guard blocks out-of-scope actions such as worker discipline, face
identification, and direct safety PLC control. Emergency calls are mock-only and
also require independent P0 confirmation from current risk and observation state.

### Persistence

- SQLite storage persists the full run JSON plus denormalized evidence, risk,
  tool call, action, incident, and handover tables.
- The API currently reads the full saved run state for most UI needs.

### Current Console

The existing `ops_guardian/static/console.html` is intentionally thin:

- Scenario selector.
- Start, step, complete, and reset controls.
- Clip/observation status.
- Live risk board.
- Tool trace.
- Evidence drawer.
- Action queue.
- Emergency console.
- Scorecard.
- Shift handover.

Most panels currently show raw JSON, which is useful for proving backend state
but is not yet a polished operator experience.

## 5. Demo Scenarios

### 5.1 Prevent Forklift/Pedestrian Near Miss

- Scenario ID: `safety_forklift_near_miss`.
- Zone: Dock Intersection A.
- Camera: `CAM-DOCK-A`.
- Event class: preventive safety.
- Risk: loaded forklift and pedestrian converge near a blocked mirror.
- Context: Traffic SOP v1 and site map.
- Expected severity: `P2`.
- Tools: retrieve SOP, activate warning beacon, notify shift lead, create task,
  schedule recheck, verify risk reduced.
- Why it exists: demonstrates next-minute safety prevention before a near miss
  completes.

### 5.2 Prevent Conveyor Jam

- Scenario ID: `operations_conveyor_jam`.
- Zone: Conveyor Transfer C7.
- Camera: `CAM-CONV-C7`.
- Event class: preventive operations.
- Risk: boxes accumulate and match a prior stoppage pattern.
- Context: MES line data and CMMS asset history.
- Expected severity: `P3`.
- Tools: query MES, query CMMS, notify shift lead, create maintenance task,
  schedule recheck, generate scorecard.
- Why it exists: shows that the system can connect visible queue buildup to
  operational and maintenance data before downtime occurs.

### 5.3 Prevent Quality Escape

- Scenario ID: `quality_missing_insert`.
- Zone: Pack Station 02.
- Camera: `CAM-PACK-02`.
- Event class: preventive quality.
- Risk: carton is about to be sealed without the required ACME instruction
  insert.
- Context: ACME packout SOP and WMS order `A-1048`.
- Expected severity: `P3`.
- Tools: retrieve SOP, query WMS, pause release, create quality hold, notify
  quality lead, verify hold task.
- Why it exists: proves the product can prevent an irreversible workflow error,
  not just safety incidents.

### 5.4 Worker Collapse Medical Emergency

- Scenario ID: `medical_worker_collapse`.
- Zone: Outbound Dock 3.
- Camera: `CAM-DOCK-03`.
- Event class: P0 medical emergency.
- Risk: worker collapses near active forklift traffic and remains motionless
  beyond the configured threshold.
- Context: emergency action plan and site map.
- Expected severity: `P0`.
- Tools: retrieve emergency plan, retrieve site map, get nearest entrance,
  request safe stop, open incident card, notify onsite first responder, make
  mock EMS call.
- Why it exists: demonstrates emergency escalation with dispatchable location
  context while keeping all external calls simulated.

### 5.5 Forced Entry Security Incident

- Scenario ID: `security_forced_entry`.
- Zone: Restricted Cage Door.
- Camera: `CAM-RESTRICTED-DOOR`.
- Event class: P0 security emergency.
- Risk: after-hours forced entry into a restricted area without a badge match.
- Context: security policy and access-control log.
- Expected severity: `P0`.
- Tools: query access control, retrieve security policy, notify security, open
  emergency incident card, make mock police call.
- Why it exists: tests policy-based emergency escalation and distinguishes
  configured P0 conditions from ambiguous nonviolent presence.

### 5.6 SOP Swap Adaptability

- Scenario ID: `adaptability_sop_swap`.
- Zone: Dock Intersection A.
- Camera: `CAM-DOCK-B`.
- Event class: adaptability.
- Risk: cold-chain loading changes the pedestrian crossing rule from Gate A to
  Gate B.
- Context: Traffic SOP v1 and Traffic SOP v2 - Cold Chain Loading.
- Expected severity: `P2`.
- Tools: retrieve updated SOP, notify shift lead, create preventive task.
- Why it exists: shows the product should adapt to updated rules and camera
  context instead of hardcoding one traffic pattern.

## 6. Severity and Intervention Ladder

- `P3`: Operational or quality risk. Notify lead, create task, schedule recheck.
- `P2`: Preventive safety risk. Activate local warning, notify supervisor,
  create urgent task, verify.
- `P1`: Serious safety condition. Notify onsite responder or security and
  prepare escalation.
- `P0`: Emergency. Trigger configured emergency protocol through mock endpoint
  after P0 confirmation.

The UX should make this ladder visible through hierarchy, color, urgency, and
action controls. A `P0` emergency should not look like just another card in the
same list.

## 7. Important Safety and Authority Boundaries

The current product is deliberately constrained:

- Emergency calls are mock endpoint calls only.
- Direct safety PLC control is never allowed.
- Worker discipline is never allowed.
- Face recognition is off by default and outside MVP scope.
- Safe stop is a simulated request, not direct machine control.
- Quality holds are configurable and simulated.
- P0 emergency calls require corroborated current observation and confidence.
- Ambiguous security situations should route to human security review instead of
  police escalation.

The future UX should surface these boundaries clearly but calmly, especially
around emergency and high-impact actions.

## 8. Current Data Sources

- `data/scenarios.json`: seeded scenario definitions.
- `data/site_map.json`: zones, camera IDs, hazards, nearest entrances, AEDs.
- `data/wms_orders.json`: order, SKU, carton, dock, lane, release, and insert
  requirements.
- `data/mes_events.json`: line status, queue counts, prior stoppage pattern.
- `data/cmms_assets.json`: asset maintenance history and prior faults.
- `data/access_control_log.json`: restricted door badge result.
- `data/emergency_policy.json`: medical threshold, responders, callback route.
- `data/security_policy.json`: P0 security conditions and ambiguous conditions.
- `data/sops/*.md`: traffic, cold-chain, packout, emergency, and security rules.
- `data/eval_labels.json`: ground-truth checks for severity, escalation, and
  required tools.

## 9. API Surface Useful for UX

- `GET /health`: app status.
- `GET /console`: current static console.
- `GET /api/scenarios`: list available demo scenarios.
- `GET /api/runs`: list saved runs.
- `POST /api/runs`: start a scenario run.
- `POST /api/runs/{run_id}/step`: advance one window.
- `POST /api/runs/{run_id}/complete`: run until scenario completion.
- `GET /api/runs/{run_id}`: retrieve full run state.
- `GET /api/runs/{run_id}/handover`: retrieve or generate handover.
- `POST /api/reset`: clear stored demo runs.

## 10. Current UX Inventory

The current console already names the right product surfaces:

- Scenario launcher.
- Video/clip status.
- Live risk board.
- Tool trace.
- Evidence drawer.
- Action queue.
- Emergency console.
- Prevention scorecard.
- Shift handover.

The main UX gap is presentation. The data is available, but much of it is raw
JSON and not organized around operator decisions.

## 11. UX Principles for the Next Build

### Design for Supervisory Work

This should feel like an operations cockpit:

- Dense, scannable, and calm.
- Prioritized by risk and urgency.
- Evidence-backed.
- Built for repeated shift use.
- Fast to answer "what needs attention now?"

Avoid a marketing-style hero page. The first screen should be the working
console.

### Make Risk the Primary Navigation Model

Operators should move from:

1. Current highest-risk item.
2. Why the system believes it.
3. What was done.
4. What remains unresolved.
5. What evidence and policy support the decision.

### Separate Normal Operations from Emergencies

A P0 event needs a dedicated emergency presentation:

- Emergency type.
- Severity.
- Exact zone and nearest entrance.
- Hazards nearby.
- Responders notified.
- Acknowledgment status.
- Mock escalation payload.
- Timeline of escalation steps.

### Turn Raw Logs into Actionable Artifacts

Tool calls, evidence, and actions should be rendered as operator-readable
timeline events and compact detail panels rather than raw JSON.

### Preserve Auditability

The system's credibility depends on visible evidence:

- Frame or clip references.
- SOP snippets.
- WMS/MES/CMMS/access-control rows.
- Tool call status and policy check.
- Before/after verification evidence.
- Handover-ready summaries.

### Show Confidence Without Overclaiming

The UX should show confidence, uncertainty, policy checks, and verification
status. Especially in degraded visibility or high-impact scenarios, the UI
should make it obvious whether the system acted, blocked an action, or requested
human review.

## 12. Suggested Information Architecture

### Primary Layout

- Left rail: scenario/run controls, zone selector, run status, current step.
- Center: video/evidence region plus timeline.
- Right rail: ranked risk board and active action queue.
- Bottom or drawer: tool trace, policy evidence, raw audit details.
- Modal or full-height panel: P0 emergency console.

### Key Views

- Live Operations View: active video/evidence, risk board, action queue.
- Risk Detail View: one risk, evidence, policy, actions, verification.
- Emergency Console: P0 incident lifecycle and escalation payload.
- Evidence Drawer: frames, SOP snippets, logs, tool outputs.
- Handover View: resolved risks, open risks, incidents, holds, tasks,
  recommendations.
- Eval/Confidence View: scenario pass/fail, expected tools, escalation precision
  and recall for demos.

## 13. UX Components to Build

- Scenario cards with event class, severity expectation, zone, camera, and data
  sources.
- Run timeline with observation, risk forecast, action, recheck, verification,
  escalation, and handover events.
- Risk cards with severity, score, probability, confidence, time-to-event,
  status, zone, evidence count, and next required action.
- Risk detail drawer with recommended actions, actions taken, policy IDs,
  evidence references, and verification status.
- Tool trace table with tool name, policy check, status, output summary, and
  timestamp.
- Action queue grouped by owner role and status.
- Emergency incident panel with responder state and mock dispatch payload.
- Scorecard tiles for predicted risks, verified reductions, open items, and
  emergency incidents.
- Handover report renderer that reads like a shift-ready summary.
- Raw JSON inspector hidden behind an audit/developer toggle.

## 14. Implementation Realities and Gaps

Important limitations to keep in mind while designing:

- Mock mode is deterministic and scenario-specific.
- Live model mode depends on configured model credentials and model behavior.
- Real video perception requires MP4 clips, OpenCV, optional ultralytics
  dependencies, and model files.
- Missing clips fall back to placeholder frame references.
- The agent loop is currently step-based: observe, plan once, execute listed
  tools, save state.
- Some tool outputs are recorded but not yet transformed into polished summaries.
- Verification is rule-based over the latest observation text and does not yet
  perform a full visual before/after comparison.
- The current console has no real video player, no image rendering, no polished
  hierarchy, and minimal interaction design.

These gaps do not block a strong UX. They define where the UX should clearly
label simulated behavior, live evidence, policy state, and uncertainty.

## 15. What "Good" Should Look Like

A clean UX should make Line Guardian feel like a trustworthy shift supervisor:

- It sees the zone.
- It names the active operational risk.
- It explains the operational rule or data behind the risk.
- It chooses an allowed intervention.
- It shows whether the action happened, was blocked, or needs human review.
- It verifies the outcome.
- It leaves a shift handover that a real supervisor could use.

The best next UX should turn the current backend state into a focused command
surface: prioritized, evidence-rich, calm under emergency conditions, and clear
about what is simulated versus live.

## 16. Source Map

- Product intent: `PRD.md`, `README.md`.
- App/API: `ops_guardian/app.py`, `main.py`.
- Scenario orchestration: `ops_guardian/runner.py`.
- Domain models: `ops_guardian/models.py`.
- Model adapters: `ops_guardian/model_adapters.py`, `ops_guardian/schemas.py`.
- Video and perception: `ops_guardian/video.py`, `ops_guardian/perception.py`.
- Risk scoring: `ops_guardian/scoring.py`.
- Tool execution and authority gates: `ops_guardian/tools.py`.
- Storage: `ops_guardian/storage.py`.
- Current UI: `ops_guardian/static/console.html`.
- Demo data and policies: `data/`.
- Eval harness and tests: `scripts/eval.py`, `tests/`.
