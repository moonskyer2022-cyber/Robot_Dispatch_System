import json
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


RobotStatus = Literal["idle", "busy", "charging", "offline"]


class RobotCreate(BaseModel):
    id: str
    name: str
    status: Literal["idle", "charging", "offline"] = "idle"
    battery: int = Field(default=100, ge=0, le=100)
    x: float = 0
    y: float = 0
    capability: str = "delivery"

    @field_validator("id", "name")
    @classmethod
    def must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("capability")
    @classmethod
    def normalize_capabilities(cls, value: str) -> str:
        capabilities = list(dict.fromkeys(item.strip() for item in value.split(",") if item.strip()))
        if not capabilities:
            raise ValueError("must contain at least one capability")
        return ",".join(capabilities)


class RobotHeartbeat(BaseModel):
    status: RobotStatus
    battery: int = Field(ge=0, le=100)
    x: float
    y: float
    current_task_id: str | None = None


class RobotOut(RobotCreate):
    status: RobotStatus
    current_task_id: str | None = None
    last_heartbeat_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskCreate(BaseModel):
    type: str = "delivery"
    priority: int = Field(default=3, ge=1, le=10)
    start_node: str
    end_node: str

    @field_validator("type", "start_node", "end_node")
    @classmethod
    def must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @model_validator(mode="after")
    def nodes_must_differ(self):
        if self.start_node == self.end_node:
            raise ValueError("start_node and end_node must differ")
        return self


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

    model_config = ConfigDict(from_attributes=True)


class MapNodeOut(BaseModel):
    id: str
    name: str
    x: float
    y: float
    type: str

    model_config = ConfigDict(from_attributes=True)


class MapEdgeOut(BaseModel):
    id: int
    from_node: str
    to_node: str
    distance: float
    enabled: bool

    model_config = ConfigDict(from_attributes=True)


class DispatchResult(BaseModel):
    task_id: str | None
    selected_robot_id: str | None
    assigned: bool
    reason: str
    score_detail: list[dict[str, Any]] = Field(default_factory=list)


class DecisionLogOut(BaseModel):
    id: int
    task_id: str
    candidate_robots: list[str]
    selected_robot_id: str | None
    score_detail: list[dict[str, Any]]
    decision_reason: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("candidate_robots", "score_detail", mode="before")
    @classmethod
    def parse_json_fields(cls, value):
        return json.loads(value) if isinstance(value, str) else value
