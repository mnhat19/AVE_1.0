from __future__ import annotations

from pydantic import BaseModel, Field


class AuditScope(BaseModel):
    session_id: str
    stage: str
    objectives: list[str] = Field(default_factory=list)
    notes: str | None = None


class AuditTask(BaseModel):
    id: str
    task_type: str
    priority: int
    assigned_agent: str
    status: str = "PENDING"
    dependencies: list[str] = Field(default_factory=list)


class ExecutionPlan(BaseModel):
    scope: AuditScope
    tasks: list[AuditTask] = Field(default_factory=list)
    ordered_task_ids: list[str] = Field(default_factory=list)
