# Ops Guardian — Improvements

A critique of the current implementation and a prioritized plan to make the
system's **accuracy** real rather than simulated. Today almost all demo accuracy
comes from `MockScenarioAdapter`'s hardcoded per-scenario facts; the "live" path
cannot actually perceive video.

## Headline problem: the VLM never sees the video

- `video.py` reads frames with OpenCV but **discards the pixels**, keeping only
  string references like `clip://...#frame=123`.
- `model_adapters.py` `OpenAICompatibleAdapter` sends a **text-only** chat
  message; the "frame window" is metadata/URIs, never image bytes.

Result: in live mode the vision model infers the scene from the scenario
description and filenames. For a "video-native" product this is the core gap and
must be fixed before any other accuracy work matters.

## Critique by pipeline stage

- **Perception does too much in one model.** One VLM is asked to both perceive
  (positions, speeds, posture) and reason (severity, time-to-event). This is the
  least accurate possible design.
- **Prediction is hallucinated, not computed.** `estimate_motion_paths`,
  `forecast_collision_risk`, `forecast_medical_emergency_confidence` don't exist
  as real computations. `time_to_event_seconds`/`confidence` are model-emitted or
  hardcoded. The PRD `risk_score` formula is never computed; ranking uses only
  severity + confidence.
- **The agent loop isn't agentic.** `runner.py` calls `plan_next_action` once,
  gets a fixed tool list, and executes it without feeding results back to the
  model. Plan-then-execute, not a ReAct/tool-use loop.
- **Verification is fake.** `verify_risk_reduced` flips every non-P0 risk to
  `mitigated` unconditionally — it never re-observes the scene.
- **Grounding/hallucination controls missing.** No confidence degradation under
  poor visibility (FR-005). SOP retrieval truncates to `text[:500]`, which can cut
  off the actual rule. Output parsing is "ask for JSON in text + regex + retry"
  rather than structured outputs.
- **No measurement.** No labeled data, no eval, no false-alarm-rate computation
  despite it being a stated metric.

## Prioritized accuracy improvements

1. **Send real frames to the VLM (multimodal).** Decode frames → JPEG bytes →
   base64 → `image_url` content blocks. Prerequisite for everything else.
2. **Split perception from reasoning — specialist models.** Detector + tracker
   (e.g. YOLO + ByteTrack) and pose estimation produce structured facts
   (entities, positions, velocities, posture); the VLM/planner reasons over them.
3. **Make prediction real and deterministic where possible.** Time-to-collision
   from velocity vectors; motionless-duration across windows vs.
   `p0_motionless_threshold_seconds`; queue growth rate; implement real
   `risk_score` and rank by it.
4. **Real verification.** Re-observe after intervention; only downgrade a risk if
   the hazard condition is actually gone. Preserve before/after evidence.
5. **Structured outputs + a real tool-use loop.** Native function-calling /
   JSON-schema mode with Pydantic validation and retry-on-validation-error; let
   the model see tool results and choose the next call.
6. **Second-opinion gate on P0 escalations.** Independent verifier or
   self-consistency vote before any P0 emergency tool fires (false EMS/police
   calls are the PRD's #1 risk).
7. **Eval harness with ground truth.** Label clips with event type + timing;
   track detection precision/recall, lead time, false-alarm rate, localization.

## Smaller code notes

- `get_settings()` is `@lru_cache`'d, so live env changes don't take effect.
- Denormalized SQLite child tables in `storage.py` are written but never read.
- Tool exceptions are swallowed into `{"error": ...}` the planner never sees.

## Progress

- [x] 1. Multimodal frames into the VLM — `video.py` now JPEG-encodes decoded
      frames to base64 (`FrameWindow.images_base64`); `OpenAICompatibleAdapter`
      sends them as `image_url` content blocks. Requires the `video` extra
      (`pip install -e .[video]`) + MP4 clips in `data/videos/`.
- [x] 2. Perception/reasoning split (detector + pose) — `ops_guardian/perception.py`
      `Perceptor` (YOLO detect + pose, lazy-loaded, graceful degrade) wired into the
      runner; facts attached to `FrameWindow.perception` so they flow into the vision
      prompt with no adapter change. Off by default (`ENABLE_PERCEPTION`). Validated
      on real clips. Known gap: forklifts/parcels aren't COCO classes → ROI/motion
      path is a #3 follow-up. (`tests/test_perception.py`)
- [x] 3. Deterministic prediction + real risk_score — `ops_guardian/scoring.py`
      implements PRD `risk_score = severity*probability*exposure*time_urgency*confidence`
      (0..1); runner scores every risk (exposure from perception entity counts) and
      `generate_live_risk_board` ranks by it. Cross-window motionless accumulation
      (`RunState.perception_motionless_seconds`) makes the P0 medical threshold real
      and is surfaced into the vision facts. (`tests/test_scoring.py`)
      Deferred: time-to-collision geometry (needs per-track trajectories/homography)
      and conveyor ROI-occupancy growth — both require richer Perceptor tracking.
- [x] 4. Real verification — `verify_risk_reduced` only downgrades a risk when the
      latest observation no longer shows the hazard; else `unresolved`; no
      observation → unchanged; P0 never auto-downgraded. (`tests/test_verification.py`)
- [x] 5a. Structured outputs — `ops_guardian/schemas.py` (`SceneAnalysisResponse`,
      `PlanResponse`); `_request_json` validates each model response against the schema
      and, on parse/validation failure, feeds the error back and retries. Preserves the
      qwen/gemma path (`chat_max_tokens`/`chat_think`/`_post_chat_completions`).
      Confirmed live against qwen3-vl:8b. (`tests/test_structured_outputs.py`)
      NOTE: qwen3-vl is a *thinking* model on the `/v1` endpoint — with a low
      `CHAT_MAX_TOKENS` (e.g. 400-512) reasoning consumes the whole budget and it
      returns EMPTY content. Use `CHAT_MAX_TOKENS>=1500` for the live qwen path.
- [x] 5b. ReAct tool-use loop — `runner.step_run` now loops plan→execute→observe up to
      `max_tool_iterations` (default 4), feeding each tool's result back into
      `plan_next_action(..., tool_results=...)`; `AgentDecision.done`/`PlanResponse.done`
      signal completion. Mock adapter stays single-iteration (done defaults True) so all
      tests/eval are unchanged. (`tests/test_react_loop.py`) Built via a parallel Workflow.
      Follow-up: a P0 surfacing in a later iteration doesn't retroactively gate a tool
      already executed earlier (gate evaluates per-execute) — fine today, revisit with #5/#6.
- [x] Positive collapse clip — sourced via the UR Fall Detection Dataset (URFD `fall-06`,
      CC BY-NC-SA), assembled to `data/videos/worker_collapse_motionless.mp4`; clean
      upright→prone with sustained prone 3–8s. `scenarios.json` medical scenario now points
      to it. Kept `worker_upright_negative.mp4` (snow) as the true-negative example.
- [x] Perceptor stillness metric — replaced the keypoint-centroid motion metric (which
      jittered on horizontal poses, reading ~0) with a frame-to-frame pixel-diff over a
      STABLE crop region (union of person boxes). URFD prone tail now reads
      motionless_fraction ~0.38 vs 0.0 for moving clips. Integrated full run (real YOLO
      perception on the URFD clip) accumulates 3.3s motionless and fires the P0 path:
      medical_collapse (escalated, scored) -> call_ems completed (P0 gate confirmed) ->
      medical incident -> handover.
- [x] Live path hardening — `request_timeout_seconds` (default 60) is now configurable
      (REQUEST_TIMEOUT_SECONDS); local thinking-VLM calls with images can exceed 60s.
      LIVE STATUS: qwen3-vl:8b vision verified standalone (schema-validated SceneObservation)
      and grounded-decision; the full all-live multi-step run is flaky on the 8B local model
      (empty/non-JSON content under thinking + large prompts) — a model/config limit, not a
      pipeline bug. Use CHAT_MAX_TOKENS>=1500 and a stronger/cloud planner for full-live runs.
- [x] 6. P0 second-opinion gate — emergency calls (EMS/fire/police) require an
      independent P0 confirmation (open P0 risk ≥ `p0_confirmation_confidence`,
      hazard corroborated in latest observation across hazards/posture/movement);
      otherwise blocked + a shift-supervisor review action is recorded.
      (`tests/test_p0_gate.py`)
- [x] 7. Eval harness — `scripts/eval.py` + `data/eval_labels.json` score every
      scenario (severity / escalation / tools) with escalation precision+recall;
      `tests/test_eval.py`. Currently 6/6 on the mock adapter.
