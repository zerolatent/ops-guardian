# PRD: Line Guardian - Real-Time Preventive AI Shift Supervisor

**Document owner:** Hackathon team  
**Product:** Line Guardian  
**Document type:** Product Requirements Document  
**Version:** 1.0  
**Date:** 2026-06-27  
**Status:** Draft for hackathon implementation

---

## 1. Executive Summary

Line Guardian is a video-native, real-time preventive AI shift supervisor for industrial operations. The product watches a bounded physical operations zone, reasons over live video and operational context, predicts short-horizon safety and workflow risks, intervenes through approved tools, verifies that risk was reduced, and produces an auditable shift record.

The system is designed for factories, warehouses, logistics sites, and distribution centers where operations managers need help preventing safety incidents, quality escapes, equipment stoppages, dock congestion, and emergency escalation failures.

The core product promise is:

> Detection is about what already happened. Prevention is about changing the next minute.

Line Guardian does not merely detect events and generate tickets after the fact. It manages live risk trajectories: what is happening now, what is likely to happen next, what intervention is appropriate, and whether the intervention worked.

---

## 2. One-Sentence Pitch

Line Guardian is a video-native preventive shift supervisor that watches an industrial zone in real time, predicts safety and operational risks before they become incidents, intervenes through approved workflow tools, escalates emergencies to onsite responders or public safety when required, verifies mitigation, and writes the shift handover.

---

## 3. Problem Statement

Industrial operations are dynamic, physical, and messy. Supervisors, safety officers, maintenance technicians, quality inspectors, and inventory clerks often rely on fragmented information from cameras, radios, WMS/MES logs, SOPs, incident systems, and human observation.

Most AI demos in this space are narrow detection systems: PPE detection, object detection, defect classification, or video summarization. These are useful tasks, but they do not own a role. Operations managers need systems that can monitor a real workflow, understand context, take timely action, and close the loop.

The product problem is:

> How can an AI system act as a preventive area supervisor for a real physical workflow, using live video plus operational tools to prevent safety, quality, flow, and emergency failures before they escalate?

---

## 4. Product Goals

### 4.1 Primary Goals

1. **Prevent incidents before they occur**
   - Predict short-horizon risk from live video and operational context.
   - Intervene before a near miss, quality escape, line stop, or security escalation occurs.

2. **Own a whole operational role**
   - Watch, reason, act, verify, and report for one bounded industrial zone.
   - Operate like a preventive shift supervisor, not a task classifier.

3. **Use agentic tool selection**
   - The agent decides when to read video, query logs, retrieve SOPs, issue warnings, create tasks, call emergency workflows, or generate reports.
   - The pipeline is not hardcoded for each scenario.

4. **Handle unseen operational conditions**
   - Adapt to a new camera angle, new SOP, new site map, new label format, new shift condition, or new emergency policy.

5. **Be credible to an operations manager**
   - Show risk reduction, timestamped evidence, action history, and handoff quality.
   - Use the language of operations: downtime, throughput, congestion, safety, quality holds, shift handover, unresolved actions.

6. **Escalate emergencies appropriately**
   - For P0 events such as worker collapse, severe accident, fire, active violence, forced entry, or visible weapon, initiate the configured emergency protocol.
   - Route medical emergencies, fire emergencies, and security emergencies differently.

### 4.2 Secondary Goals

1. Provide a live risk cockpit for supervisors.
2. Maintain audit trails for all serious recommendations and actions.
3. Support privacy-preserving operation by focusing on zones, equipment, hazards, and workflows rather than worker identity.
4. Provide a modular architecture that can plug into WMS, MES, CMMS, access control, site maps, and alerting systems.

---

## 5. Non-Goals

Line Guardian will not do the following in the hackathon MVP:

1. **Directly control certified safety PLCs or machine safety systems.**
   - It may request a safe stop or notify a human/system, but it will not directly override safety-rated controls.

2. **Replace emergency responders or supervisors.**
   - It escalates, routes, documents, and verifies. Human responders remain responsible for physical intervention.

3. **Perform worker discipline or productivity scoring.**
   - It should not rank, score, or discipline individuals.

4. **Use face recognition by default.**
   - The product should avoid identity-based monitoring unless a customer has a separate, legally reviewed access-control use case.

5. **Claim perfect safety or medical diagnosis.**
   - It observes visible conditions and initiates configured escalation. It does not diagnose medical causes.

6. **Solve all industrial scenarios.**
   - The MVP focuses on one bounded zone and four event classes: preventive safety, preventive operations, preventive quality, and P0 emergency escalation.

---

## 6. Target Users and Personas

### 6.1 Primary User: Operations Manager

**Needs:**
- Keep shift running safely and efficiently.
- Reduce incidents, near misses, downtime, quality escapes, and handoff gaps.
- See what needs attention now.
- Trust that the system has evidence and did not hallucinate.

**Success criteria:**
- The system surfaces the right risks early.
- The system shows why it acted.
- The system reduces follow-up burden by drafting tasks, incident cards, and handovers.

### 6.2 Secondary User: Shift Supervisor / Area Lead

**Needs:**
- Know where to intervene immediately.
- Receive concise, actionable alerts.
- Avoid false alarms and alert fatigue.
- Confirm when a risk has been resolved.

### 6.3 Secondary User: Safety Officer

**Needs:**
- Prevent near misses.
- Document serious events accurately.
- Verify corrective actions.
- Maintain audit trails and evidence.

### 6.4 Secondary User: Security Lead

**Needs:**
- Detect and escalate severe security incidents.
- Avoid unnecessary police calls for ambiguous behavior.
- Receive evidence and location context quickly.

### 6.5 Secondary User: Maintenance Lead

**Needs:**
- Detect early signs of jams, line stops, blocked equipment, leaks, or unsafe machine states.
- Get evidence-backed work requests.

### 6.6 Secondary User: Quality Lead

**Needs:**
- Catch SOP deviations before shipment or downstream escape.
- Place holds when required.
- Verify rework completion.

---

## 7. Core Product Principle

Line Guardian should always answer four questions:

1. **What is happening now?**
2. **What is likely to happen next?**
3. **What is the least disruptive safe intervention?**
4. **Did the intervention reduce risk?**

---

## 8. MVP Scope

### 8.1 Bounded Physical Zone

The MVP should focus on one of the following:

- Outbound dock zone
- Packaging cell
- Warehouse pick/pack aisle
- Receiving bay
- Conveyor transfer area

Recommended hackathon zone:

> Outbound dock and staging zone with one pedestrian crossing, one forklift lane, one dock door, one packing or staging station, and one emergency egress path.

### 8.2 MVP Event Classes

The MVP must demonstrate four event classes:

1. **Preventive safety event**
   - Example: worker and forklift are likely to converge at a blind intersection.

2. **Preventive operations event**
   - Example: dock congestion or conveyor queue buildup is likely to cause loading delay or jam.

3. **Preventive quality event**
   - Example: a carton is about to be sealed before required insert or label verification.

4. **P0 emergency event**
   - Example: worker collapse, severe accident, visible fire/smoke, active violence, visible weapon, or forced entry into a restricted area.

### 8.3 MVP Demo Requirements

The demo must show:

1. Live or simulated live video ingestion.
2. VLM reasoning over the video.
3. Agent tool selection, not a fixed prewired pipeline.
4. Context retrieval from SOP, site map, WMS/MES/CMMS, emergency action plan, or security policy.
5. Preventive intervention before an incident completes.
6. Verification that the risk was reduced.
7. Emergency escalation for a P0 event.
8. End-of-shift handover.
9. Adaptability to an unseen camera angle, SOP, or site rule.

---

## 9. System Overview

### 9.1 High-Level Architecture

```text
Live Video Streams
    -> Video Reasoning Model
    -> Area State Model
    -> Risk Trajectory Engine
    -> Context Retrieval Layer
    -> Agent Planner
    -> Action and Escalation Layer
    -> Verification and Audit Layer
    -> Live Risk Cockpit and Shift Handover
```

### 9.2 Major Components

1. **Video Reasoning Model**
   - Understands scene state, movement, posture, objects, hazards, workflow steps, and visual evidence.

2. **Area State Model**
   - Maintains current state of the zone: people, forklifts, pallets, boxes, machines, paths, blocked areas, queues, doors, emergency exits, and active tasks.

3. **Risk Trajectory Engine**
   - Predicts short-horizon risks over 10 seconds, 30 seconds, 60 seconds, and several minutes.

4. **Context Retrieval Layer**
   - Retrieves SOPs, site maps, emergency action plans, WMS/MES/CMMS logs, dock schedules, access logs, and security policies.

5. **Agent Planner**
   - Chooses what tools to use and in what order.
   - Selects the intervention level based on risk severity, confidence, policy, and urgency.

6. **Action and Escalation Layer**
   - Issues warnings, notifications, tasks, holds, safe-stop requests, onsite responder alerts, EMS calls, fire calls, police calls, and security alerts.

7. **Verification Layer**
   - Confirms whether the intervention reduced risk.
   - Rechecks video and logs after action.

8. **Audit and Reporting Layer**
   - Records evidence, timestamps, reasoning summaries, tool calls, action acknowledgments, outcomes, and handover reports.

---

## 10. Risk and Severity Model

### 10.1 Severity Ladder

| Level | Name | Description | Example | Default Agent Behavior |
|---|---|---|---|---|
| P3 | Operational Risk | Risk to throughput, schedule, inventory, or quality if unaddressed | Dock congestion, queue buildup, wrong staging lane | Notify lead, create task, schedule recheck |
| P2 | Preventive Safety Risk | Unsafe condition that could become incident | Forklift/pedestrian convergence, blocked walkway, spill, unstable pallet | Local warning, notify supervisor, create urgent task, verify |
| P1 | Serious Safety Condition | High-risk event requiring immediate human response | Person down but moving, worker in restricted machine zone, severe near miss | Notify onsite responder/security, request acknowledgment, prepare escalation |
| P0 | Emergency | Immediate threat to life, safety, facility, or public security | Worker collapsed and motionless, severe injury, fire/smoke, active violence, weapon, forced entry into critical area | Trigger emergency protocol immediately |

### 10.2 Risk Score

Each active risk should have a risk score based on:

```text
risk_score = severity * probability * exposure * time_urgency * confidence
```

Definitions:

- **Severity:** Potential harm or business impact.
- **Probability:** Estimated likelihood if no action is taken.
- **Exposure:** Number of people, assets, orders, or operations affected.
- **Time urgency:** How soon intervention is needed.
- **Confidence:** Evidence quality and model certainty.

### 10.3 Risk Card Format

Each risk should be represented as a structured card:

```yaml
risk_id: RISK-2026-0019
risk_type: forklift_pedestrian_conflict
zone: outbound_dock_intersection_a
severity: P2
probability: high
confidence: 0.81
time_to_event_estimate: 12 seconds
evidence:
  - Loaded forklift approaching blind turn
  - Pedestrian walking toward crossing
  - Sightline partially blocked by staged pallet
  - SOP requires clear sightlines and stop-horn behavior
recommended_intervention:
  - Activate local warning beacon
  - Notify dock lead
  - Clear pallet blocking mirror
actions_taken:
  - Warning beacon activated
  - Dock lead notified
  - Clearing task created
verification_status: pending
```

---

## 11. Functional Requirements

### 11.1 Observe and Understand Live Video

| ID | Requirement | Priority | Acceptance Criteria |
|---|---|---|---|
| FR-001 | The system shall ingest live or simulated live video from at least one camera. | P0 | Demo shows video frames being analyzed continuously or in near-real-time chunks. |
| FR-002 | The system shall identify relevant entities in the zone: people, forklifts, pallets, cartons, machines, doors, paths, queues, spills, and blocked areas. | P0 | Agent can describe scene state with timestamped visual evidence. |
| FR-003 | The system shall maintain a current state of the operational zone. | P0 | UI shows active entities, current risks, and unresolved tasks. |
| FR-004 | The system shall support multiple camera angles for the same zone. | P1 | Agent can reason over an unseen angle without hardcoded coordinates. |
| FR-005 | The system shall handle degraded visibility by lowering confidence and escalating to human verification when appropriate. | P0 | Agent states uncertainty and does not fabricate details. |

### 11.2 Predict Preventive Risk

| ID | Requirement | Priority | Acceptance Criteria |
|---|---|---|---|
| FR-006 | The system shall predict short-horizon safety risks from entity movement and context. | P0 | Demo shows predicted forklift/pedestrian convergence before contact or near miss. |
| FR-007 | The system shall estimate time-to-event for urgent risks when possible. | P1 | Risk card includes estimated time-to-event such as 12 seconds. |
| FR-008 | The system shall predict operational flow risks such as congestion, queue buildup, dock delay, or conveyor jam. | P0 | Demo shows early warning before a simulated jam or loading delay. |
| FR-009 | The system shall predict quality escape risk before irreversible process completion. | P0 | Demo shows warning before carton is sealed or shipment is released. |
| FR-010 | The system shall rank active risks by severity, time urgency, and confidence. | P0 | Live risk board orders risks appropriately. |

### 11.3 Retrieve Context

| ID | Requirement | Priority | Acceptance Criteria |
|---|---|---|---|
| FR-011 | The system shall retrieve the applicable SOP for a workflow or zone. | P0 | Agent cites the relevant SOP section in reasoning summary. |
| FR-012 | The system shall retrieve site map information including zones, emergency exits, nearest entrances, AEDs, and restricted areas. | P0 | Emergency card includes nearest entrance and relevant zone. |
| FR-013 | The system shall query mock WMS data for pallets, SKUs, orders, dock doors, shipments, and staging lanes. | P1 | Agent verifies whether a pallet or carton is in the correct location. |
| FR-014 | The system shall query mock MES or equipment logs for line state, stoppages, and queue conditions. | P1 | Agent connects video queue buildup with operational log data. |
| FR-015 | The system shall query mock CMMS data for asset history, open work orders, and prior faults. | P2 | Maintenance-related risk card references prior asset issues. |
| FR-016 | The system shall retrieve the site emergency action plan for escalation rules. | P0 | P0 emergency escalation follows configured site policy. |
| FR-017 | The system shall retrieve the site security policy for police/security escalation thresholds. | P0 | Security incident flow distinguishes security review from police escalation. |

### 11.4 Agentic Tool Selection

| ID | Requirement | Priority | Acceptance Criteria |
|---|---|---|---|
| FR-018 | The agent shall choose tools dynamically based on the observed situation. | P0 | Tool trace differs across safety, quality, operations, and emergency scenarios. |
| FR-019 | The agent shall produce a concise reasoning summary that explains why tools were selected. | P0 | UI shows reasoning summary and tool calls without exposing hidden chain-of-thought. |
| FR-020 | The agent shall avoid hardcoded scenario pipelines. | P0 | Demo includes a new SOP or camera angle and agent adapts via retrieval and reasoning. |
| FR-021 | The agent shall ask for human verification when evidence is insufficient for non-emergency high-impact actions. | P0 | Ambiguous security event triggers security review rather than police call. |

### 11.5 Preventive Interventions

| ID | Requirement | Priority | Acceptance Criteria |
|---|---|---|---|
| FR-022 | The system shall activate a local warning for configured P2/P1 safety risks. | P0 | Demo shows warning beacon or simulated alert triggered before near miss. |
| FR-023 | The system shall notify the appropriate area lead with concise, actionable context. | P0 | Alert includes risk type, location, evidence, recommended action, and urgency. |
| FR-024 | The system shall create preventive tasks for hazards or workflow risks. | P0 | Task includes owner role, priority, due time, evidence, and verification requirement. |
| FR-025 | The system shall create a quality hold when a likely quality escape is imminent or detected before release. | P1 | Demo shows QA hold for carton missing required insert before seal/shipment. |
| FR-026 | The system shall request a safe stop or local pause for serious hazards where policy allows. | P1 | Demo shows safe-stop request for worker collapse or severe machine hazard. |
| FR-027 | The system shall avoid unnecessary disruption by choosing the lowest safe intervention level. | P0 | P3 congestion creates task/notification, not emergency escalation. |

### 11.6 Emergency Escalation

| ID | Requirement | Priority | Acceptance Criteria |
|---|---|---|---|
| FR-028 | The system shall classify emergency events into medical, fire, security, environmental, or operational emergency categories. | P0 | Emergency card shows emergency type and escalation path. |
| FR-029 | The system shall initiate medical emergency protocol for configured P0 medical conditions. | P0 | Worker collapse scenario triggers onsite responder alert and mock EMS call. |
| FR-030 | The system shall initiate fire emergency protocol for visible fire, smoke, explosion, or related configured hazard. | P1 | Fire scenario, if included, creates fire escalation card. |
| FR-031 | The system shall initiate security emergency protocol for configured P0 security conditions. | P0 | Forced entry, active assault, visible weapon, or active threat triggers security and police path. |
| FR-032 | The system shall not call police for ambiguous, nonviolent, or low-confidence security observations. | P0 | Ambiguous after-hours presence triggers security review, not police call. |
| FR-033 | Emergency escalation shall include exact location context: site, building, zone, nearest entrance, camera ID, timestamp, hazards nearby, and callback route. | P0 | Mock emergency payload includes all required fields. |
| FR-034 | The system shall stream or attach relevant video evidence to the emergency incident card. | P1 | Emergency card includes key frames and live feed link or placeholder. |
| FR-035 | The system shall track acknowledgment status for emergency notifications. | P1 | UI shows whether onsite responder/security/supervisor acknowledged. |
| FR-036 | The system shall continue monitoring the emergency scene until handoff or resolution. | P1 | Emergency timeline updates after escalation. |

### 11.7 Verification

| ID | Requirement | Priority | Acceptance Criteria |
|---|---|---|---|
| FR-037 | The system shall schedule a recheck after any preventive intervention. | P0 | Risk card shows recheck time and condition. |
| FR-038 | The system shall verify whether risk was reduced after an intervention. | P0 | Demo shows risk downgraded after worker/forklift paths separate. |
| FR-039 | The system shall escalate unresolved risks according to policy. | P1 | Blocked exit task escalates if still unresolved after deadline. |
| FR-040 | The system shall preserve before/after evidence for verified interventions. | P1 | Audit record shows initial risk frame and resolved frame. |

### 11.8 Reporting and Handover

| ID | Requirement | Priority | Acceptance Criteria |
|---|---|---|---|
| FR-041 | The system shall maintain a live risk board for the active zone. | P0 | UI shows ranked live risks and statuses. |
| FR-042 | The system shall produce an end-of-shift handover. | P0 | Report includes resolved risks, open items, emergencies, tasks, and recommendations. |
| FR-043 | The system shall produce a prevention scorecard. | P1 | Scorecard includes predicted risks, interventions, verified reductions, false alarms, and open items. |
| FR-044 | The system shall maintain an audit log of evidence, tool calls, actions, and outcomes. | P0 | Every serious event includes timestamped evidence and action history. |

---

## 12. Emergency Response Requirements

### 12.1 Emergency Response Orchestrator

The Emergency Response Orchestrator handles P0 and selected P1 events. It is separate from normal task creation.

The orchestrator must:

1. Retrieve site-specific emergency action plan.
2. Classify emergency type.
3. Determine required responders.
4. Create emergency incident card.
5. Send immediate notifications.
6. Initiate mock EMS, fire, police, or security call when policy requires.
7. Include dispatchable location context.
8. Track acknowledgment.
9. Keep monitoring the scene.
10. Add emergency summary to shift handover.

### 12.2 P0 Medical Emergency Criteria

The system should initiate P0 medical protocol when one or more configured criteria are met:

- Worker collapses and remains motionless beyond site-configured threshold.
- Worker is visibly injured and unable to move.
- Worker is struck by equipment or trapped.
- Worker falls from height.
- Severe accident occurs with visible impact.
- Human panic/help signal is detected and corroborated by video or audio where available.

Default MVP condition:

```text
Worker was upright, collapsed to the ground, and remained motionless for more than 10-20 seconds while no responder is visible.
```

### 12.3 Medical Emergency Flow

```text
1. Detect collapse or severe accident.
2. Confirm continued risk state over short window.
3. Classify as P0 medical emergency if threshold is met.
4. Request local safe stop if active equipment or vehicles are nearby.
5. Notify onsite first responder and shift supervisor.
6. Initiate mock EMS call through configured emergency endpoint.
7. Include exact location and nearest entrance.
8. Attach video evidence and camera feed.
9. Track acknowledgment.
10. Continue monitoring for responder arrival.
```

### 12.4 Security Emergency Criteria

The system may initiate police escalation only for configured P0 security conditions, such as:

- Visible weapon.
- Active assault or violent incident.
- Forced entry into critical or restricted area.
- Credible active threat.
- Security officer panic alarm.
- Ongoing break-in with access-control corroboration.

The system must not automatically call police for:

- Ambiguous loitering.
- Clothing, appearance, or demographic attributes.
- Nonviolent policy violations.
- Unconfirmed theft-like behavior.
- Low-confidence observations.

### 12.5 Security Incident Flow

```text
1. Detect possible security incident.
2. Query site security policy.
3. Query access-control logs if relevant.
4. Determine severity.
5. If P0, notify security and initiate police escalation according to site policy.
6. If ambiguous or nonviolent, notify security for review and monitor.
7. Attach evidence and location context.
8. Track acknowledgment and updates.
```

### 12.6 Mock Emergency Payload

The hackathon demo should use a mock emergency endpoint, not a real public safety call.

Example payload:

```json
{
  "incident_id": "EMG-2026-0042",
  "emergency_type": "medical_collapse",
  "severity": "P0",
  "site": "Demo Distribution Center",
  "building": "Building B",
  "zone": "Outbound Dock 3",
  "nearest_entry": "South Roll-Up Door",
  "camera_id": "CAM-DOCK-03",
  "timestamp": "2026-06-27T10:42:18-05:00",
  "observed_condition": "Worker collapsed and remains motionless for 18 seconds",
  "hazards_nearby": ["active forklift traffic"],
  "recommended_response": ["EMS", "onsite_first_responder", "area_safe_stop"],
  "callback_route": "demo-command-center",
  "evidence": [
    "frame://CAM-DOCK-03/2026-06-27T10:42:05-05:00",
    "frame://CAM-DOCK-03/2026-06-27T10:42:18-05:00"
  ]
}
```

---

## 13. Authority Matrix

| Action | Autonomy Level | Notes |
|---|---|---|
| Create preventive task | Autonomous | Include owner role, evidence, due time, and recheck. |
| Notify supervisor or area lead | Autonomous | Default for P2/P3 risks. |
| Activate local warning beacon | Autonomous for configured P2/P1 safety risks | Must be site-approved. |
| Create quality hold | Configurable | Autonomous for clear SOP misses; human approval optional. |
| Request safe stop | Human-confirmed unless P0 | For P0, request immediately through configured path. |
| Notify onsite first responder | Autonomous for P0/P1 medical/safety events | Must include location and evidence. |
| Call EMS/fire/police | Autonomous only for configured P0 conditions in demo through mock endpoint | Real deployment requires site legal, emergency, and telecom review. |
| Discipline worker | Never | Out of scope. |
| Identify worker by face | Off by default | Out of scope for MVP. |
| Directly control safety PLC | Never in MVP | Use request/notification path only. |

---

## 14. User Experience Requirements

### 14.1 Live Risk Cockpit

The primary UI should show a live ranked list of risks:

```text
1. High: Forklift/pedestrian convergence at Dock A - 12 sec
2. Medium: Conveyor C7 jam likely - 4 min
3. Medium: Pack station QA miss likely - active carton
4. Low: Dock 3 congestion increasing - 12 min
```

Each risk card must include:

- Risk type
- Severity
- Confidence
- Time-to-event estimate when available
- Zone
- Evidence frames
- Relevant SOP/policy/log excerpts
- Recommended action
- Action taken
- Verification status

### 14.2 Timeline View

The UI must show not only what happened, but what the agent predicted before it happened.

Example:

```text
10:41:55 - Risk forecast created
10:42:01 - Warning issued
10:42:08 - Worker stopped before crossing
10:42:15 - Risk verified as reduced
```

### 14.3 Evidence Drawer

The evidence drawer should show:

- Key frames or clips
- Timestamps
- Camera ID
- SOP snippets
- WMS/MES/CMMS rows
- Site map zone
- Tool calls
- Human acknowledgments

### 14.4 Intervention Panel

The intervention panel should show:

- Warning beacon activated
- Supervisor notified
- Task created
- Quality hold created
- Safe stop requested
- Onsite responder notified
- EMS/fire/police/security escalation initiated

### 14.5 Emergency Console

For P0 events, show a dedicated emergency console with:

- Emergency type
- Severity
- Location
- Nearest entrance
- Hazards nearby
- Responders notified
- Acknowledgment status
- Live or simulated camera feed
- Incident timeline
- Escalation payload

### 14.6 Shift Handover

The system must generate a handover report with:

- Resolved risks
- Open risks
- Preventive interventions
- Emergency escalations
- Quality holds
- Maintenance watch items
- Safety observations
- Tasks awaiting acknowledgment
- Recommendations for next shift
- Evidence links

---

## 15. Data and Integrations

### 15.1 Required MVP Data Sources

1. **Video clips or streams**
   - Simulated live video is acceptable for hackathon.

2. **SOP documents**
   - Traffic SOP, dock SOP, packout SOP, emergency action plan, security policy.

3. **Site map**
   - Zones, dock doors, forklift lanes, pedestrian crossings, exits, AEDs, nearest entrances.

4. **Mock WMS data**
   - Orders, pallets, SKUs, staging lanes, dock assignments, shipment deadlines.

5. **Mock MES/equipment logs**
   - Conveyor status, line speed, stoppage events, queue counts.

6. **Mock task/incident system**
   - Task creation, incident cards, acknowledgment status, closeout.

7. **Mock emergency dispatch endpoint**
   - EMS, fire, police, security endpoints for demo only.

### 15.2 Optional Data Sources

- Access-control logs.
- CMMS asset history.
- Worker role roster without facial identity.
- Radio or notification channel simulation.
- Environmental sensors.
- Badge-zone presence counts.

---

## 16. Tooling Requirements

The agent must have a toolbox. It must choose tools based on the situation.

### 16.1 Video Tools

```text
read_live_video(camera_id)
read_recent_video(camera_id, lookback_seconds)
extract_keyframes(camera_id, time_range)
track_zone_entities(camera_id, zone_id)
estimate_motion_paths(camera_id, horizon_seconds)
detect_posture_change(camera_id, person_region)
detect_area_congestion(zone_id)
detect_blocked_path(zone_id)
detect_spill_or_debris(zone_id)
detect_unstable_stack(zone_id)
```

### 16.2 Context Tools

```text
query_wms(order_id, pallet_id, dock_door)
query_mes(line_id, time_range)
query_cmms(asset_id)
query_access_control(door_id, time_range)
retrieve_sop(process_name)
retrieve_emergency_action_plan(site_id)
retrieve_security_policy(site_id)
retrieve_site_map(site_id)
get_nearest_emergency_entry(zone_id)
get_nearest_aed(zone_id)
```

### 16.3 Prediction Tools

```text
forecast_collision_risk(zone_id, horizon_seconds)
forecast_congestion_risk(zone_id, horizon_minutes)
forecast_quality_escape_risk(workstation_id)
forecast_line_stop_risk(line_id)
forecast_security_escalation_risk(zone_id)
forecast_medical_emergency_confidence(camera_id, time_range)
rank_risks_by_severity_and_time()
```

### 16.4 Intervention Tools

```text
activate_warning_beacon(zone_id, message)
send_radio_alert(channel, message)
notify_shift_lead(zone_id, message, evidence)
notify_safety_officer(zone_id, message, evidence)
notify_security(zone_id, message, evidence)
create_preventive_task(owner_role, priority, due_time, evidence)
pause_work_release(workstation_id, reason)
create_quality_hold(order_id, reason, evidence)
request_safe_stop(asset_id, reason)
schedule_recheck(camera_id, condition, deadline)
```

### 16.5 Emergency Tools

```text
call_ems(site_id, zone_id, evidence, callback_number)
call_fire(site_id, zone_id, evidence, callback_number)
call_police(site_id, zone_id, evidence, callback_number)
notify_onsite_first_responder(zone_id, evidence)
start_employee_accountability_check(zone_id)
stream_incident_to_command_center(incident_id)
open_emergency_incident_card(type, severity, evidence)
```

### 16.6 Verification and Reporting Tools

```text
verify_risk_reduced(zone_id, original_risk_id)
verify_task_completed(task_id)
generate_live_risk_board(zone_id)
generate_prevention_scorecard(shift_id)
generate_shift_handover(shift_id)
```

---

## 17. Adaptability Requirements

The system must demonstrate adaptability in the hackathon.

### 17.1 New Camera Angle

The agent must handle a camera view not used during initial setup.

Acceptance criteria:

- Agent recognizes the zone layout from site map and visual evidence.
- Agent updates confidence if sightlines are worse.
- Agent avoids relying only on fixed pixel coordinates.

### 17.2 New SOP

The agent must adapt to a changed or newly uploaded SOP.

Acceptance criteria:

- Agent retrieves the new SOP.
- Agent changes its decision based on the new rule.
- Agent explains the difference in the reasoning summary.

Example:

```text
Previous SOP: Pedestrians may cross at Gate A.
New SOP: During cold-chain loading, pedestrians must cross at Gate B only.
```

### 17.3 New Emergency Policy

The agent must adapt to a site-specific emergency action plan.

Acceptance criteria:

- Medical emergency thresholds and escalation recipients come from policy configuration.
- Emergency payload includes configured site location data.

### 17.4 New Label or Layout

The agent must adapt to a different product label position or staging lane layout.

Acceptance criteria:

- Agent uses video reasoning plus WMS/SOP retrieval rather than hardcoded label location.

---

## 18. Example End-to-End Flows

### 18.1 Flow A: Prevent Forklift/Pedestrian Near Miss

**Trigger:** Worker and loaded forklift are on converging paths near blind intersection.

**Agent flow:**

```text
1. read_live_video(CAM-DOCK-A)
2. track_zone_entities(CAM-DOCK-A, dock_intersection_a)
3. estimate_motion_paths(CAM-DOCK-A, 15 seconds)
4. retrieve_sop(site_traffic_sop)
5. forecast_collision_risk(dock_intersection_a, 15 seconds)
6. activate_warning_beacon(dock_intersection_a, "Forklift crossing. Stop and check.")
7. notify_shift_lead(dock_intersection_a, concise risk alert)
8. create_preventive_task(material_handler, high, clear blocked mirror)
9. schedule_recheck(CAM-DOCK-A, risk_reduced, 60 seconds)
10. verify_risk_reduced(dock_intersection_a, risk_id)
```

**Expected result:**

- Worker stops or changes path.
- Forklift slows or stops.
- Risk is downgraded from high to low.
- Root cause task remains open until mirror/path is cleared.

### 18.2 Flow B: Prevent Conveyor Jam

**Trigger:** Boxes begin accumulating at transfer point.

**Agent flow:**

```text
1. read_live_video(CAM-CONV-C7)
2. detect_area_congestion(conveyor_transfer_c7)
3. query_mes(line_c7, last_10_minutes)
4. query_cmms(asset_c7)
5. forecast_line_stop_risk(line_c7)
6. notify_shift_lead(line_c7, "Queue buildup likely to cause jam")
7. create_preventive_task(maintenance_tech, medium, inspect transfer point)
8. schedule_recheck(CAM-CONV-C7, queue_reduced, 2 minutes)
```

**Expected result:**

- Agent warns before full jam.
- Maintenance or supervisor receives evidence-backed action.
- Recheck determines whether queue growth stopped.

### 18.3 Flow C: Prevent Quality Escape

**Trigger:** Carton is about to be sealed without required insert.

**Agent flow:**

```text
1. read_live_video(CAM-PACK-02)
2. retrieve_sop(packout_sop)
3. query_wms(order_id)
4. forecast_quality_escape_risk(pack_station_02)
5. pause_work_release(pack_station_02, "Missing required insert before seal")
6. create_quality_hold(order_id, evidence)
7. notify_quality_lead(pack_station_02, evidence)
8. verify_task_completed(quality_hold_id)
```

**Expected result:**

- Carton is corrected before shipment.
- Quality hold includes evidence and SOP reference.

### 18.4 Flow D: Worker Collapse Medical Emergency

**Trigger:** Worker collapses and remains motionless.

**Agent flow:**

```text
1. read_live_video(CAM-DOCK-03)
2. detect_posture_change(CAM-DOCK-03, person_region)
3. forecast_medical_emergency_confidence(CAM-DOCK-03, last_20_seconds)
4. retrieve_emergency_action_plan(site_id)
5. retrieve_site_map(site_id)
6. get_nearest_emergency_entry(outbound_dock_3)
7. request_safe_stop(outbound_dock_zone, "Worker collapsed near active forklift traffic")
8. open_emergency_incident_card(medical_collapse, P0, evidence)
9. notify_onsite_first_responder(outbound_dock_3, evidence)
10. call_ems(site_id, outbound_dock_3, evidence, callback_number)
11. stream_incident_to_command_center(incident_id)
12. track acknowledgment and responder arrival
```

**Expected result:**

- P0 medical emergency card created.
- Onsite responder notified.
- Mock EMS escalation initiated with exact location.
- Area safe-stop requested.
- Incident timeline updates until handoff.

### 18.5 Flow E: Security Incident

**Trigger:** Forced entry into restricted area after hours.

**Agent flow:**

```text
1. read_live_video(CAM-RESTRICTED-DOOR)
2. query_access_control(restricted_door, last_5_minutes)
3. retrieve_security_policy(site_id)
4. classify severity
5. if P0: notify_security(zone_id, evidence)
6. if P0 and policy requires: call_police(site_id, zone_id, evidence, callback_number)
7. open_emergency_incident_card(security_forced_entry, P0, evidence)
8. stream_incident_to_command_center(incident_id)
```

**Expected result:**

- Forced entry with no badge match triggers security and police escalation according to policy.
- Ambiguous nonviolent presence triggers security review only.

---

## 19. Data Model

### 19.1 Risk

```yaml
Risk:
  risk_id: string
  risk_type: string
  severity: P0 | P1 | P2 | P3
  zone_id: string
  camera_ids: list[string]
  status: predicted | active | mitigated | escalated | unresolved | false_alarm
  probability: low | medium | high
  confidence: float
  time_to_event_seconds: integer | null
  detected_at: datetime
  updated_at: datetime
  evidence_ids: list[string]
  applicable_policy_ids: list[string]
  recommended_actions: list[string]
  actions_taken: list[action_id]
  verification_id: string | null
```

### 19.2 Evidence

```yaml
Evidence:
  evidence_id: string
  type: frame | clip | log_row | sop_snippet | map_region | tool_output
  source: string
  timestamp: datetime
  description: string
  uri: string
  confidence: float | null
```

### 19.3 Action

```yaml
Action:
  action_id: string
  action_type: warning | notification | task | hold | safe_stop_request | emergency_call
  risk_id: string
  owner_role: string
  status: created | sent | acknowledged | completed | failed
  created_at: datetime
  due_at: datetime | null
  payload: object
  acknowledgment: object | null
```

### 19.4 Emergency Incident

```yaml
EmergencyIncident:
  incident_id: string
  emergency_type: medical | fire | security | environmental | operational
  severity: P0 | P1
  site_id: string
  building: string
  zone_id: string
  nearest_entry: string
  camera_ids: list[string]
  observed_condition: string
  hazards_nearby: list[string]
  responders_notified: list[string]
  acknowledgment_status: object
  escalation_payload: object
  status: opened | responders_notified | acknowledged | handed_off | closed
```

### 19.5 Shift Handover

```yaml
ShiftHandover:
  shift_id: string
  site_id: string
  zone_id: string
  start_time: datetime
  end_time: datetime
  resolved_risks: list[risk_id]
  open_risks: list[risk_id]
  emergency_incidents: list[incident_id]
  quality_holds: list[action_id]
  maintenance_watch_items: list[action_id]
  unresolved_tasks: list[action_id]
  recommendations: list[string]
```

---

## 20. Success Metrics

### 20.1 Hackathon Demo Metrics

| Metric | Target |
|---|---|
| Preventive event shown before incident completion | At least 1 |
| Event classes demonstrated | At least 4 |
| Agent-selected tool calls visible | Yes |
| Evidence attached to each serious action | 100% of demo events |
| P0 emergency escalation demo | At least 1 |
| Adaptability test | At least 1 new SOP or camera angle |
| Shift handover generated | Yes |

### 20.2 Product Metrics for Future Pilot

| Metric | Description |
|---|---|
| Verified risk reductions | Number of risks downgraded after intervention. |
| Prevented near misses | Estimated number of high-risk trajectories interrupted. |
| Mean time to supervisor notification | Time from risk prediction to alert. |
| Mean time to acknowledgment | Time from alert to human acknowledgment. |
| False alarm rate | Share of alerts marked invalid by reviewer. |
| Missed critical event rate | Critical events not flagged in time. |
| Open risk aging | Time risks remain unresolved. |
| Quality escapes prevented | Holds/corrections before shipment or downstream release. |
| Downtime avoided | Estimated line stoppage or congestion avoided. |
| Emergency escalation completeness | Percent of emergency cards with required location/evidence fields. |

---

## 21. Privacy, Safety, and Trust Requirements

### 21.1 Privacy Requirements

1. The product should focus on zones, hazards, equipment, and workflows.
2. Face recognition should be disabled by default.
3. Worker identity should not be used for productivity scoring or discipline.
4. Visual evidence should be access-controlled.
5. Emergency and safety evidence retention should follow customer policy.
6. Demo should avoid unnecessary personal identification.

### 21.2 Safety Requirements

1. Emergency escalation must follow a site-configured policy.
2. The system must distinguish medical, fire, security, and operational emergencies.
3. The system must show confidence and uncertainty.
4. The system must not hallucinate emergency details.
5. For P0 events, the system should bias toward rapid escalation or rapid human verification.
6. For ambiguous security events, the system should notify security rather than directly call police.

### 21.3 Auditability Requirements

Every P0/P1 event must include:

- Timestamp
- Camera ID
- Zone
- Observed facts
- Confidence
- Applicable SOP or policy reference
- Actions taken
- Notifications sent
- Acknowledgment status
- Outcome
- Evidence links

---

## 22. Demo Script

### 22.1 Opening

Presenter says:

> This is Line Guardian, a preventive AI shift supervisor for an outbound dock zone. It does not just detect incidents after the fact. It predicts what is about to go wrong, intervenes through approved tools, verifies that risk dropped, and writes the shift handover.

### 22.2 Scene 1: Preventive Safety

Video shows a forklift and pedestrian approaching a blind intersection.

Expected agent output:

```text
High-risk trajectory detected. Pedestrian and loaded forklift are likely to converge at Dock Intersection A in approximately 12 seconds. Sightline is partially blocked by a staged pallet. I am activating the local warning beacon, notifying the dock lead, and creating a task to clear the obstruction.
```

Then video shows paths separate.

Expected agent output:

```text
Risk reduced. Pedestrian stopped before crossing and forklift slowed at intersection. Collision risk downgraded from high to low. Mirror obstruction remains open and will be rechecked in 3 minutes.
```

### 22.3 Scene 2: Preventive Operations

Video shows boxes accumulating at a conveyor transfer point or dock congestion increasing.

Expected agent output:

```text
Transfer Point C7 is trending toward a jam. Queue growth matches earlier stoppage pattern. I recommend reducing upstream release for 3 minutes and sending maintenance to inspect the roller bed. Preventive task created and recheck scheduled.
```

### 22.4 Scene 3: Preventive Quality

Video shows a carton about to be sealed without an insert.

Expected agent output:

```text
Quality escape risk. The ACME packout SOP requires an instruction insert before seal. I do not see the insert placed in the carton, and the carton is not sealed yet. I am creating a QA hold and notifying the quality lead before shipment release.
```

### 22.5 Scene 4: P0 Emergency

Video shows worker collapse near active forklift lane.

Expected agent output:

```text
P0 medical emergency. Worker collapsed at Outbound Dock 3 and has remained motionless for 18 seconds. Active forklift traffic is nearby. I requested local safe stop, alerted onsite first responder, opened the emergency incident card, and initiated mock EMS escalation with site, building, zone, nearest entrance, timestamp, camera ID, and hazard context.
```

### 22.6 Scene 5: Adaptability

Presenter uploads new SOP or switches to new camera angle.

Expected agent output:

```text
I found an updated traffic SOP. During cold-chain loading, pedestrians must cross at Gate B only. Under the previous SOP this route was acceptable; under the new SOP it creates a preventive safety risk. I am updating the risk policy for this zone and notifying the area lead.
```

### 22.7 Closing: Shift Handover

Expected handover:

```text
Shift Handover - Outbound Dock Zone

Resolved:
- Forklift/pedestrian convergence prevented at Dock Intersection A.
- Conveyor C7 queue risk reduced after upstream release was slowed.

Open:
- Mirror obstruction at Dock Intersection A remains unresolved.
- QA hold for Order A-1048 awaiting quality lead acknowledgment.

Emergency:
- P0 medical emergency at Outbound Dock 3. Onsite responder and mock EMS escalation initiated. Incident card EMG-2026-0042 remains open.

Next shift actions:
1. Verify Dock Intersection A sightline is cleared.
2. Confirm QA disposition for Order A-1048.
3. Inspect Conveyor C7 transfer point if queue growth repeats.
```

---

## 23. Acceptance Criteria for Hackathon Submission

The submission is successful if it demonstrates all of the following:

1. **Whole-role ownership**
   - The agent acts as a preventive shift supervisor for a bounded zone.

2. **Reasoning model usage**
   - A VLM or frontier model reasons over messy operational video and context.

3. **Workflow tool use**
   - The agent selects tools such as video reading, SOP retrieval, WMS/MES query, task creation, warnings, and emergency escalation.

4. **Preventive behavior**
   - The agent acts before at least one incident completes.

5. **Emergency handling**
   - The agent escalates a P0 medical or security emergency using a site-configured mock protocol.

6. **Adaptability**
   - The agent handles a new SOP, camera angle, or policy without hardcoded rules.

7. **Verification**
   - The agent checks whether its intervention reduced risk.

8. **Auditability**
   - Each serious conclusion has timestamped evidence and action history.

9. **Handover**
   - The agent produces a credible end-of-shift report.

---

## 24. Implementation Plan for Hackathon

### 24.1 Minimum Build

1. Build a simple web UI with:
   - Video player
   - Live risk board
   - Tool trace
   - Evidence drawer
   - Action queue
   - Emergency console
   - Shift handover panel

2. Create mock data:
   - 3-5 short video clips or staged clips
   - SOP markdown files
   - Site map JSON
   - WMS/MES CSV or JSON
   - Mock task database
   - Mock emergency endpoint

3. Implement agent tools as local functions.

4. Use VLM for scene interpretation and reasoning summaries.

5. Use a frontier model as the planner that chooses tools.

6. Store all actions and events in a local SQLite or JSON event log.

### 24.2 Suggested Stack

- Frontend: React, Next.js, or Streamlit
- Backend: FastAPI or Node.js
- Agent planner: Claude, GPT, or other frontier model
- Vision reasoning: VLM API
- Data store: SQLite or JSON files
- Video: Local MP4 clips treated as simulated live feed
- Notifications: Mock Slack/Teams/radio console
- Emergency: Mock dispatch endpoint

### 24.3 Demo Data Files

Recommended files:

```text
/data/videos/forklift_pedestrian_convergence.mp4
/data/videos/conveyor_queue_buildup.mp4
/data/videos/packout_missing_insert.mp4
/data/videos/worker_collapse.mp4
/data/videos/new_angle_dock_intersection.mp4
/data/sops/traffic_sop_v1.md
/data/sops/traffic_sop_v2_cold_chain.md
/data/sops/packout_sop_acme.md
/data/sops/emergency_action_plan.md
/data/sops/security_policy.md
/data/site_map.json
/data/wms_orders.json
/data/mes_events.json
/data/cmms_assets.json
/data/access_control_log.json
```

---

## 25. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| False emergency escalation | High trust/safety risk | Use mock endpoint in demo; require site-configured P0 policy; include confidence and evidence; use human review for ambiguous events. |
| Alert fatigue | Users ignore alerts | Rank risks, use severity ladder, choose lowest safe intervention, suppress duplicates. |
| Privacy concerns | Deployment blocker | Avoid face recognition, focus on zones/equipment/hazards, redact faces in evidence where possible. |
| Overclaiming medical capability | Legal and trust risk | Do not diagnose; describe observed condition and escalate through policy. |
| Hardcoded demo | Fails challenge criteria | Include live SOP swap or unseen camera angle. |
| VLM uncertainty | Incorrect assessment | Expose confidence, cite evidence, escalate to human verification when ambiguous. |
| Direct control of unsafe equipment | Safety certification issue | Do not directly control safety systems; issue requests and alerts only. |
| Poor location context in emergency | Response delay | Use site map, zone IDs, nearest entrance, camera ID, and callback route in emergency payload. |

---

## 26. Open Questions

1. What exact physical zone should the hackathon demo use?
2. Will video be live, staged, synthetic, or public-domain?
3. Which VLM will be used for frame/video interpretation?
4. Which model will act as planner?
5. Should the MVP show one camera or multiple cameras?
6. What is the emergency escalation threshold for the demo collapse scenario?
7. Should quality hold be autonomous or supervisor-approved?
8. Should warning beacon and safe-stop actions be simulated in UI only?
9. What is the desired latency target for simulated real-time operation?
10. What output format is required for final hackathon judging?

---

## 27. Appendix: Sample Agent Response Format

```text
Risk Update - Outbound Dock Zone

Risk:
A loaded forklift and pedestrian are likely to converge at Dock Intersection A in approximately 12 seconds.

Severity:
P2 preventive safety risk.

Why:
- Forklift is approaching blind turn with a pallet load.
- Pedestrian is walking toward crossing.
- Sightline is partially blocked by staged pallet.
- Site traffic SOP requires clear crossing and stop-horn behavior.

Action taken:
- Activated local warning beacon.
- Notified dock lead.
- Created task to clear blocked sightline.
- Scheduled recheck in 60 seconds.

Verification:
Pending.

Confidence:
0.81. Visibility is adequate, but forklift operator view is partly inferred from camera angle.
```

---

## 28. Appendix: Sample Shift Handover Format

```text
Shift Handover - Outbound Dock Zone
Shift: 2026-06-27 AM

Summary:
Line Guardian monitored the outbound dock zone for safety, operational flow, quality, and emergency risk. Three preventive interventions were issued and one P0 emergency was escalated through the configured mock protocol.

Resolved:
1. Forklift/pedestrian convergence prevented at Dock Intersection A.
   - Warning beacon activated.
   - Dock lead notified.
   - Risk reduced after pedestrian stopped and forklift slowed.

2. Conveyor C7 queue buildup reduced.
   - Upstream release reduction recommended.
   - Maintenance watch task created.

Open:
1. Mirror obstruction at Dock Intersection A.
   - Owner: Material handler.
   - Due: Immediate.
   - Status: Open.

2. QA hold for Order A-1048.
   - Reason: Missing ACME instruction insert before seal.
   - Owner: Quality lead.
   - Status: Awaiting acknowledgment.

Emergency:
1. P0 medical emergency at Outbound Dock 3.
   - Worker collapsed and remained motionless.
   - Onsite responder notified.
   - Mock EMS escalation initiated.
   - Local safe stop requested.
   - Incident card: EMG-2026-0042.

Recommendations for next shift:
1. Clear Dock Intersection A sightline before forklift traffic resumes at full volume.
2. Review C7 transfer point if queue growth repeats.
3. Confirm QA disposition for Order A-1048.
4. Review emergency response timeline for acknowledgment delays.
```

---

## 29. Final MVP Definition

For the hackathon, Line Guardian is considered complete when it can demonstrate this loop:

```text
Watch live/simulated video
-> Understand current operational state
-> Predict near-term risk
-> Retrieve relevant context
-> Choose a tool-driven intervention
-> Act through warning/task/hold/escalation
-> Verify whether risk dropped
-> Record evidence and outcome
-> Produce shift handover
```

The winning demo should make an operations manager believe:

> This is not a camera alert system. This is an AI shift supervisor that prevents the next bad thing from happening.
