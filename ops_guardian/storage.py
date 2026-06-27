from __future__ import annotations

from contextlib import contextmanager
import json
import sqlite3
from pathlib import Path
from typing import Any, Iterator

from pydantic import BaseModel

from .models import (
    Action,
    EmergencyIncident,
    Evidence,
    RunState,
    ShiftHandover,
    ToolCall,
    utc_now,
)


def _json_default(value: Any) -> str:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value)!r} is not JSON serializable")


def to_json(model_or_value: BaseModel | Any) -> str:
    if isinstance(model_or_value, BaseModel):
        return model_or_value.model_dump_json()
    return json.dumps(model_or_value, default=_json_default)


class Storage:
    def __init__(self, sqlite_path: Path):
        self.sqlite_path = sqlite_path
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self.init()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.sqlite_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def init(self) -> None:
        with self.connect() as db:
            db.executescript(
                """
                create table if not exists runs (
                    run_id text primary key,
                    scenario_id text not null,
                    status text not null,
                    step_index integer not null,
                    state_json text not null,
                    started_at text not null,
                    updated_at text not null
                );
                create table if not exists evidence (
                    evidence_id text primary key,
                    run_id text not null,
                    type text not null,
                    source text not null,
                    timestamp text not null,
                    payload_json text not null
                );
                create table if not exists risks (
                    risk_id text primary key,
                    run_id text not null,
                    severity text not null,
                    status text not null,
                    payload_json text not null
                );
                create table if not exists tool_calls (
                    tool_call_id text primary key,
                    run_id text not null,
                    tool_name text not null,
                    status text not null,
                    payload_json text not null
                );
                create table if not exists actions (
                    action_id text primary key,
                    run_id text not null,
                    action_type text not null,
                    status text not null,
                    payload_json text not null
                );
                create table if not exists incidents (
                    incident_id text primary key,
                    run_id text not null,
                    emergency_type text not null,
                    severity text not null,
                    status text not null,
                    payload_json text not null
                );
                create table if not exists handovers (
                    shift_id text primary key,
                    run_id text not null,
                    payload_json text not null
                );
                """
            )

    def reset(self) -> None:
        with self.connect() as db:
            for table in ("handovers", "incidents", "actions", "tool_calls", "risks", "evidence", "runs"):
                db.execute(f"delete from {table}")

    def save_run(self, state: RunState) -> RunState:
        state.updated_at = utc_now()
        with self.connect() as db:
            db.execute(
                """
                insert into runs (run_id, scenario_id, status, step_index, state_json, started_at, updated_at)
                values (?, ?, ?, ?, ?, ?, ?)
                on conflict(run_id) do update set
                    status=excluded.status,
                    step_index=excluded.step_index,
                    state_json=excluded.state_json,
                    updated_at=excluded.updated_at
                """,
                (
                    state.run_id,
                    state.scenario.scenario_id,
                    state.status,
                    state.step_index,
                    state.model_dump_json(),
                    state.started_at.isoformat(),
                    state.updated_at.isoformat(),
                ),
            )
            self._sync_children(db, state)
        return state

    def get_run(self, run_id: str) -> RunState:
        with self.connect() as db:
            row = db.execute("select state_json from runs where run_id = ?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(f"Unknown run_id: {run_id}")
        return RunState.model_validate_json(row["state_json"])

    def list_runs(self) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute(
                "select run_id, scenario_id, status, step_index, updated_at from runs order by updated_at desc"
            ).fetchall()
        return [dict(row) for row in rows]

    def _sync_children(self, db: sqlite3.Connection, state: RunState) -> None:
        for evidence in state.evidence:
            self._upsert_evidence(db, state.run_id, evidence)
        for observation in state.observations:
            for evidence in observation.evidence:
                self._upsert_evidence(db, state.run_id, evidence)
        for risk in state.risks:
            db.execute(
                """
                insert into risks (risk_id, run_id, severity, status, payload_json)
                values (?, ?, ?, ?, ?)
                on conflict(risk_id) do update set
                    status=excluded.status,
                    payload_json=excluded.payload_json
                """,
                (risk.risk_id, state.run_id, risk.severity, risk.status, to_json(risk)),
            )
        for tool_call in state.tool_calls:
            self._upsert_tool_call(db, state.run_id, tool_call)
        for action in state.actions:
            self._upsert_action(db, state.run_id, action)
        for incident in state.incidents:
            self._upsert_incident(db, state.run_id, incident)
        if state.handover:
            self._upsert_handover(db, state.run_id, state.handover)

    def _upsert_evidence(self, db: sqlite3.Connection, run_id: str, evidence: Evidence) -> None:
        db.execute(
            """
            insert into evidence (evidence_id, run_id, type, source, timestamp, payload_json)
            values (?, ?, ?, ?, ?, ?)
            on conflict(evidence_id) do update set payload_json=excluded.payload_json
            """,
            (evidence.evidence_id, run_id, evidence.type, evidence.source, evidence.timestamp.isoformat(), to_json(evidence)),
        )

    def _upsert_tool_call(self, db: sqlite3.Connection, run_id: str, tool_call: ToolCall) -> None:
        db.execute(
            """
            insert into tool_calls (tool_call_id, run_id, tool_name, status, payload_json)
            values (?, ?, ?, ?, ?)
            on conflict(tool_call_id) do update set
                status=excluded.status,
                payload_json=excluded.payload_json
            """,
            (tool_call.tool_call_id, run_id, tool_call.tool_name, tool_call.status, to_json(tool_call)),
        )

    def _upsert_action(self, db: sqlite3.Connection, run_id: str, action: Action) -> None:
        db.execute(
            """
            insert into actions (action_id, run_id, action_type, status, payload_json)
            values (?, ?, ?, ?, ?)
            on conflict(action_id) do update set
                status=excluded.status,
                payload_json=excluded.payload_json
            """,
            (action.action_id, run_id, action.action_type, action.status, to_json(action)),
        )

    def _upsert_incident(self, db: sqlite3.Connection, run_id: str, incident: EmergencyIncident) -> None:
        db.execute(
            """
            insert into incidents (incident_id, run_id, emergency_type, severity, status, payload_json)
            values (?, ?, ?, ?, ?, ?)
            on conflict(incident_id) do update set
                status=excluded.status,
                payload_json=excluded.payload_json
            """,
            (
                incident.incident_id,
                run_id,
                incident.emergency_type,
                incident.severity,
                incident.status,
                to_json(incident),
            ),
        )

    def _upsert_handover(self, db: sqlite3.Connection, run_id: str, handover: ShiftHandover) -> None:
        db.execute(
            """
            insert into handovers (shift_id, run_id, payload_json)
            values (?, ?, ?)
            on conflict(shift_id) do update set payload_json=excluded.payload_json
            """,
            (handover.shift_id, run_id, to_json(handover)),
        )
