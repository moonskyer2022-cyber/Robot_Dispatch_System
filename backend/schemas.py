from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RobotCreate(BaseModel):
    id: str
    name: str
    status: str = "idle"
    battery: int = Field(default=100, ge=0, le=100)
    x: float = 0
    y: float = 0
    capability: str = "delivery"


class RobotHeartbeat(BaseModel):
    status: str
    battery: int = Field(ge=0, le=100)
    x: float
    y: float
    current_task_id: str | None = None


class RobotOut(RobotCreate):
    current_task_id: str | None = None
    last_heartbeat_at: datetime

    class Config:
        from_attributes = True


class TaskCreate(BaseModel):
    type: str = "delivery"
    priority: int = Field(default=3, ge=1, le=10)
    start_node: str
    end_node: str


class TaskOut(BaseModel):
    id: str
    type: str
    priority: int
    start_node: str
    end_node: str
    status: str
    assigned_robot_id: str | None
    estimated_distance: float | None
    estimated_duration: int | None
    created_at: datetime
    assigned_at: datetime | None
    completed_at: datetime | None

    class Config:
        from_attributes = True


class MapNodeOut(BaseModel):
    id: str
    name: str
    x: float
    y: float
    type: str

    class Config:
        from_attributes = True


class DispatchResult(BaseModel):
    task_id: str | None
    selected_robot_id: str | None
    assigned: bool
    reason: str
    score_detail: list[dict[str, Any]] = Field(default_factory=list)


class DecisionLogOut(BaseModel):
    id: int
    task_id: str
    candidate_robots: str
    selected_robot_id: str | None
    score_detail: str
    decision_reason: str
    created_at: datetime

    class Config:
        from_attributes = True
