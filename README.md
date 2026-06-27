# Line Guardian — Preventive AI Shift Supervisor

> A video-native AI that watches an industrial zone, predicts what is about to go wrong,
> intervenes through approved tools, verifies the risk dropped, and writes the shift handover.

<img width="1723" height="888" alt="Screenshot 2026-06-27 at 5 05 18 PM" src="https://github.com/user-attachments/assets/af75b719-bb45-4939-be04-20eb90b7f295" />


---

## The Problem

Industrial operations — factories, warehouses, docks, distribution centers — are physical,
fast-moving, and messy. In a single zone you can have forklifts and pedestrians crossing
paths, conveyors backing up, cartons shipping without a required insert, and, occasionally,
a real emergency: a worker collapses, a fire starts, someone forces a restricted door.

Today most "AI for operations" is **detection after the fact**: it tells you a PPE violation
*happened*, or a defect *shipped*, or counts an incident that *already occurred*. That is a
report card, not a supervisor. By the time the alert fires, the near-miss, the line stop, or
the injury has already happened.

The real need is different:

> **Detection is about what already happened. Prevention is about changing the next minute.**

## Why We're Solving It

An operations manager doesn't want more dashboards — they want fewer incidents. The valuable
system is one that:

- **Prevents** safety incidents, quality escapes, and equipment stoppages *before* they complete.
- **Owns a role**, not a task: it watches, reasons, acts, verifies, and reports for one zone,
  like a shift supervisor would — instead of being a single narrow classifier.
- **Escalates emergencies correctly** — fast for genuine P0 events, but without false EMS/police
  calls (a false emergency dispatch is a serious trust and safety failure).
- **Is credible and auditable** — every serious action carries timestamped evidence, the rule it
  was based on, what was done, and whether it worked.

## How It Works (in plain terms)

Think of it as a tireless shift supervisor watching one camera feed:

1. **It watches the video.** Short windows of footage are pulled from the camera continuously.
2. **A fast vision system measures what's literally there** — where people and vehicles are, and
   whether someone is upright or on the ground and *how long they've stayed down*. These are
   measured numbers, not guesses.
3. **A reasoning model decides what it means** — "a person is collapsed and motionless near a
   forklift lane" — using the site's own rulebooks (SOPs, emergency plan, security policy).
4. **It acts through approved tools** — sound a warning beacon, notify the dock lead, create a
   task, place a quality hold, request a safe-stop, open an emergency incident.
5. **It double-checks before doing anything drastic.** A real medical/security emergency must be
   independently confirmed before it "calls EMS" (a mock call, in the demo).
6. **It verifies the risk actually dropped** — it re-checks the scene instead of assuming success.
7. **It writes the shift handover** — what was resolved, what's still open, what the next shift
   should watch.

The guiding idea is a clean division of labor: **the vision system measures, the language model
judges.** A tracker can compute "motionless for 18 seconds" precisely; a language model can't —
but it *can* understand that "collapsed and motionless near moving forklifts, per the emergency
plan" means call for help. Putting each where it's strong is what makes the predictions
trustworthy instead of hallucinated.

---

## Technical Architecture

### High-level pipeline

```
            ┌─────────────┐
 camera ──▶ │ VideoSampler│ frame window (+ base64 frames)
 clip       └──────┬──────┘
                   ▼
            ┌─────────────┐  measured facts (counts, posture,
            │  Perceptor  │  motionless%) ── deterministic
            │ YOLO + pose │
            └──────┬──────┘
                   ▼  facts attached to the frame window
            ┌─────────────┐  scene observation (entities, hazards,
            │   VLM scene │  posture, evidence) ── schema-validated
            │  analysis   │
            └──────┬──────┘
                   ▼
            ┌──────────────────────────┐   ReAct loop (bounded):
            │  Agent planner (plan →   │   plan → execute → observe → repeat
            │  execute → observe)      │   until done or max iterations
            └──────┬───────────────────┘
                   ▼
   ┌───────────────────────────────────────────┐
   │ ToolRegistry  + AuthorityGuard + P0 gate   │  warnings, tasks, holds,
   │ (context retrieval, interventions,         │  safe-stop, emergency calls
   │  emergency escalation, verification)       │
   └──────┬─────────────────────────────────────┘
          ▼
   risk board (ranked by risk_score) · emergency incident · evidence log · shift handover
                   │
                   ▼  persisted to SQLite; scored by the eval harness
```

The loop the whole system implements is: **watch → understand → predict → retrieve context →
act → verify → report.**

### Component-by-component

**1. Scenarios & demo data — `ops_guardian/data_loader.py`, `data/`**
The world the agent operates in. `data/scenarios.json` defines six bounded scenarios (one per
event class). Alongside them, the "operational systems" live as fixtures: SOPs (`data/sops/*.md`),
`site_map.json`, mock `wms_orders.json` / `mes_events.json` / `cmms_assets.json`,
`emergency_policy.json`, `security_policy.json`, `access_control_log.json`. `DemoData` loads
these and exposes only the sources each scenario declares, so context retrieval differs per
scenario (a quality scenario sees the packout SOP + WMS; a security scenario sees the access log
+ security policy).

**2. Video sampling — `ops_guardian/video.py`**
`VideoSampler` turns a clip + step index into a `FrameWindow` (a few JPEG frames, base64-encoded,
for the time window). If a clip is missing it emits placeholder frame references so the backend
still runs. The base64 frames are what make the vision path *actually multimodal* — real pixels,
not filenames.

**3. Perception layer (the "measure" half) — `ops_guardian/perception.py`**
`Perceptor` runs **YOLO11 detection + pose** (Ultralytics, with ByteTrack tracking available) on
the sampled frames and produces deterministic facts:
- object/person/vehicle counts (COCO classes; note forklifts/cartons aren't COCO, so those lean
  on the VLM + future ROI work);
- **posture** from shoulder/hip keypoints (torso angle → `upright` / `prone`);
- **stillness** via a frame-to-frame pixel-diff over a *stable crop region* (the union of person
  boxes) — robust to keypoint jitter, which otherwise makes a lying-still person read as "moving".

These facts are attached to `FrameWindow.perception`, which already flows into the vision prompt —
so the VLM reasons over *measured numbers*, and deterministic code can use them directly. Optional
and gracefully degrading (off unless `ENABLE_PERCEPTION=1`; no-ops if YOLO/clip absent).

**4. Vision-language reasoning (the "judge" half) — `ops_guardian/model_adapters.py`, `schemas.py`**
`ModelAdapter` has two implementations:
- `OpenAICompatibleAdapter` — calls any OpenAI-compatible vision model (OpenAI or local **Ollama**),
  sending frames as `image_url` content blocks plus the perception facts. Responses are validated
  against Pydantic **schemas** (`SceneAnalysisResponse`, `PlanResponse`); on a parse/validation
  failure the error is fed back and the model is retried — no silent malformed JSON.
- `MockScenarioAdapter` — deterministic, scripted per scenario. Used for tests and credential-free
  demos, and as a reliable planner.
The scene step yields a `SceneObservation` (visible entities, movement, posture, hazards, evidence).

**5. Risk model & scoring — `ops_guardian/scoring.py`, `ops_guardian/models.py`**
Each risk is a structured `Risk` with severity (P0–P3), probability, confidence, time-to-event,
evidence, and a computed `risk_score`:
```
risk_score = severity × probability × exposure × time_urgency × confidence   (0..1)
```
This is the PRD formula made real (exposure derived from perception entity counts; urgency from
time-to-event). The live risk board ranks by it, so a P0 collapse outranks an urgent P2 outranks a
distant P3 — defensible numbers instead of a fixed severity sort.

**6. Agent planner & ReAct tool-use loop — `ops_guardian/runner.py`**
`ScenarioRunner.step_run` orchestrates one window: sample → perceive → accumulate cross-window
motionless → VLM scene analysis → **plan/execute/observe loop**. The planner is called with the
results of prior tool calls (`tool_results`), executes the tools it chose, feeds the outputs back,
and repeats until it signals `done` or hits `max_tool_iterations`. The mock planner returns
`done=True` in one pass, so deterministic runs behave as a single iteration.

**7. Tools, authority guard & the P0 gate — `ops_guardian/tools.py`**
`ToolRegistry` is the agent's hands: ~35 tools spanning context retrieval (`retrieve_sop`,
`query_wms/mes/cmms`, `query_access_control`), interventions (`activate_warning_beacon`,
`create_preventive_task`, `create_quality_hold`, `request_safe_stop`), emergency escalation
(`open_emergency_incident_card`, `call_ems/fire/police` — **mock only**), and verification/reporting.
- `AuthorityGuard` enforces the authority matrix: emergency calls are mock-only; worker discipline,
  face recognition, and direct safety-PLC control are hard-blocked.
- **P0 second-opinion gate:** before any emergency call fires, it requires an *independent
  confirmation* — an open P0 risk above a confidence threshold **and** the hazard corroborated in
  the latest observation. If unconfirmed, the call is blocked and a human-review action is recorded
  instead. This directly guards against false EMS/police dispatch.

**8. Verification — `ops_guardian/tools.py` (`verify_risk_reduced`)**
Instead of rubber-stamping success, verification re-reads the latest observation: a risk is only
downgraded to `mitigated` if its hazard indicators are gone; otherwise it's marked `unresolved`;
with no observation it's left unchanged; P0 is never auto-downgraded. A verification evidence record
is attached.

**9. Reporting — `ops_guardian/tools.py`**
At completion the runner generates a **prevention scorecard** (predicted risks, verified reductions,
open items, incidents) and a **shift handover** (resolved/open risks, emergencies, quality holds,
maintenance watch items, unresolved tasks, recommendations) — the credible end-of-shift artifact.

**10. Persistence — `ops_guardian/storage.py`**
Each `RunState` is saved to SQLite (full JSON plus denormalized tables for risks, tool calls,
actions, incidents, evidence, handovers), so runs are inspectable and replayable.

**11. Evaluation harness — `scripts/eval.py`, `data/eval_labels.json`**
Turns "accuracy" into a number. Every scenario is run through the full pipeline and scored against
ground-truth labels: correct max severity, emergency raised **iff** expected (the false-alarm /
missed-escalation check), and required tools invoked — reported with escalation precision/recall.
This is the regression gate for prompt/model/code changes.

### End-to-end walkthrough (worker collapse, P0 medical)

1. `VideoSampler` pulls a window from the collapse clip (base64 frames).
2. `Perceptor` measures: a person, posture `prone`, and accumulated **motionless seconds** across
   windows (a real number, vs the configured P0 threshold).
3. The **VLM** reads the frame + those facts → `SceneObservation`: "person on the ground near a
   forklift lane," hazards listed, evidence captured.
4. The **planner** raises a P0 `medical_collapse` risk (scored via `risk_score`) and selects the
   emergency protocol tools across the ReAct loop.
5. The **P0 gate** confirms: open P0 risk above threshold + hazard corroborated in the observation →
   `call_ems` is allowed (mock); otherwise it would be blocked and routed to human review.
6. An **emergency incident** is opened with location/evidence; an EMS dispatch action is recorded.
7. **Verification** keeps P0 escalated; the **handover** lists the incident and next-shift actions.

Verified integrated run: real YOLO perception on the demo clip accumulates ~3.3s motionless and the
pipeline fires `medical_collapse → call_ems (gate-confirmed) → medical incident → handover`.

---

## Agents in the System

**Short answer: one runtime agent** — the Line Guardian supervisor — by design. The product
premise is to *own a role for one bounded zone* (watch → reason → act → verify → report), so the
system is a single accountable agent grounded by a deterministic perception tool and constrained
by guardrails — not a swarm of narrow bots. That one agent is composed of a single autonomous
decision-maker (the planner) plus supporting model/tool roles:

| Role | What it does | Autonomous? | Built from | Invoked by |
|---|---|---|---|---|
| **Planner agent** *(the agent)* | Raises risks and chooses which tools to call, reacting to tool results | Yes — ReAct loop | `ModelAdapter.plan_next_action` (live: `PLANNER_MODEL`) | the loop in `ScenarioRunner.step_run` |
| Vision / scene role | Turns frames + perception facts into a structured `SceneObservation` | No — single inference | `ModelAdapter.analyze_scene` (live: `VISION_MODEL`) | `ScenarioRunner.step_run`, once per window |
| Perception tool | YOLO detect + pose measurements (counts, posture, stillness) | No — deterministic | `Perceptor` | runner, before the vision call |
| P0 confirmation gate | Independent check before any emergency call | No — deterministic | `AuthorityGuard` / `_p0_confirmed` | `ToolRegistry.execute` |

**How it's built.** The "brain" is the `ModelAdapter` abstraction with two implementations:
`OpenAICompatibleAdapter` (a live LLM over an OpenAI-compatible endpoint such as Ollama) and
`MockScenarioAdapter` (deterministic, scripted). The active one is chosen by
`build_model_adapter(settings)`. The agent's control loop lives in `ScenarioRunner.step_run`, its
hands are the `ToolRegistry`, and its eyes are the `Perceptor`. Vision and planning are separately
configurable models (`VISION_MODEL`, `PLANNER_MODEL`) — they may be the same model or different.

**How it's invoked (call path).**

```
build_model_adapter(settings)               # pick live vs mock brain
        │
ScenarioRunner.step_run(run_id)             # one window of the loop
        ├─ Perceptor.analyze(frame_window)  # deterministic facts
        ├─ adapter.analyze_scene(...)       # vision role → SceneObservation
        └─ for _ in range(max_tool_iterations):     # ReAct loop
              adapter.plan_next_action(..., tool_results)   # planner agent decides
              ToolRegistry.execute(...)                     # act (gate enforced here)
              # feed outputs back; stop on `done`
                  │
        all LLM calls → _request_json (schema-validate + retry)
                      → _chat_completions_request → _post_chat_completions (HTTP)
```

**Why single-agent (and what multi-agent would add).** One supervisor with grounding (perception)
and guardrails (authority matrix + P0 gate) is more accountable and auditable than a crew for a
single zone. Natural multi-agent extensions: replacing the deterministic P0 gate with an
independent LLM "second-opinion" verifier, or running one agent per camera for a multi-zone site.

> Dev-time vs runtime: this repo was partly *built* using a parallel multi-agent Claude workflow
> (several subagents implementing features concurrently). That orchestration is a development tool
> and is **not** part of the running system.

---

## The four event classes

| Class | Example | Typical response |
|---|---|---|
| Preventive safety (P2) | forklift/pedestrian convergence | warning beacon, notify lead, task, recheck |
| Preventive operations (P3) | conveyor queue building toward a jam | notify, maintenance task, recheck |
| Preventive quality (P3) | carton about to seal without insert | quality hold, notify QA |
| P0 emergency | worker collapse / forced entry | confirm → open incident → mock EMS/police, safe-stop |

---

## Running It

Deterministic, no credentials or video required (recommended first run):

```bash
MODEL_PROVIDER=mock python3 -m uvicorn ops_guardian.app:app --reload
```

Open:
- **Operations Cockpit (default UI):** http://127.0.0.1:8000/
- API docs: http://127.0.0.1:8000/docs

The cockpit is a live control-room view: pick a scenario, **Start Shift**, then **Step** or
**Auto** to watch the agent observe → predict → act → verify. Click any risk for its evidence
drawer; P0 events open a dedicated emergency console; completing a run shows the shift handover.

Live model via local Ollama (copy `.env.example` to `.env`):

```bash
MODEL_PROVIDER=openai
OPENAI_BASE_URL=http://127.0.0.1:11434/v1
OPENAI_API_KEY=ollama            # placeholder for Ollama's OpenAI-compatible API
VISION_MODEL=qwen3-vl:8b
PLANNER_MODEL=qwen3-vl:8b
CHAT_MAX_TOKENS=1500             # thinking VLMs need headroom or they return empty content
CHAT_THINK=false
```

Real perception (YOLO) — install the extras and enable it:

```bash
pip install -e ".[perception]"   # ultralytics (YOLO11 + torch); ".[video]" adds OpenCV only
ENABLE_PERCEPTION=1
```

Drop demo MP4s into `data/videos/` using the filenames in `data/scenarios.json`. If clips are
missing, the sampler emits placeholders so the backend stays runnable.

## Configuration (env / `.env`)

| Variable | Purpose | Default |
|---|---|---|
| `MODEL_PROVIDER` | `mock` or `openai` (OpenAI-compatible) | `openai` |
| `OPENAI_BASE_URL` / `OPENAI_API_KEY` | live endpoint (e.g. Ollama) | OpenAI |
| `VISION_MODEL` / `PLANNER_MODEL` | model ids for scene/plan | — |
| `CHAT_MAX_TOKENS` / `CHAT_THINK` | budget / disable hidden reasoning | 512 / auto |
| `REQUEST_TIMEOUT_SECONDS` | per-call HTTP timeout (raise for slow local VLMs) | 60 |
| `ENABLE_PERCEPTION` | run YOLO detect+pose | off |
| `DETECTOR_MODEL` / `POSE_MODEL` | YOLO weight paths | `models/yolo11n*.pt` |
| `P0_MOTIONLESS_THRESHOLD_SECONDS` | motionless seconds → P0 medical | 15 |
| `P0_CONFIRMATION_CONFIDENCE` | P0 gate confidence floor | 0.75 |
| `MAX_TOOL_ITERATIONS` | ReAct loop cap | 4 |
| `FRAME_WINDOW_SECONDS` | window length per step | 5 |

## API

- `GET  /api/scenarios`
- `POST /api/runs` · `POST /api/runs/{id}/step` · `POST /api/runs/{id}/complete`
- `GET  /api/runs/{id}` · `GET /api/runs/{id}/handover`
- `POST /api/reset`

## Demo scenarios & assets

Seeded fixtures under `data/`: forklift/pedestrian near miss, conveyor jam, missing-insert quality
escape, worker-collapse medical emergency, forced-entry security incident, and an SOP-swap
adaptability test. Demo clips and YOLO weights are gitignored (`data/videos/*.mp4`, `*.pt`).

## Tests & evaluation

```bash
python3 -m unittest discover -s tests          # unit + API tests (mock adapter, no creds/video)
python3 scripts/eval.py                         # scenario scorecard: severity / escalation / tools
```

## Design notes & honest limitations

- **Mock vs live.** All demo accuracy is real and deterministic via the mock path; the live path
  adds genuine perception and VLM reasoning.
- **Perception coverage.** YOLO/COCO reliably finds people (and powers pose). Forklifts, cartons,
  and parcels are not COCO classes — those currently rely on the VLM, with ROI/motion handling a
  planned follow-up.
- **Local-model reliability.** A small local thinking-VLM (qwen3-vl:8b) is verified for vision and
  grounded decisions, but the *fully-live multi-step* run is flaky on the 8B model (empty/non-JSON
  under thinking + large prompts). A stronger/cloud planner removes this; the surrounding pipeline
  is model-agnostic.
- See `improvements.md` for the full accuracy roadmap, what landed, and open follow-ups.
```
