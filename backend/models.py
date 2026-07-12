from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base
from .time_utils import utc_now


class Robot(Base):
    __tablename__ = "robots"
    __table_args__ = (
        CheckConstraint(
            "status IN ('idle', 'busy', 'charging', 'offline')",
            name="ck_robots_status",
        ),
        CheckConstraint("battery BETWEEN 0 AND 100", name="ck_robots_battery"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="idle", index=True)
    battery: Mapped[int] = mapped_column(Integer, default=100)
    x: Mapped[float] = mapped_column(Float, default=0)
    y: Mapped[float] = mapped_column(Float, default=0)
    capability: Mapped[str] = mapped_column(String(80), default="delivery")
    current_task_id: Mapped[str | None] = mapped_column(
        String(40),
        ForeignKey(
            "tasks.id",
            name="fk_robots_current_task_id",
            use_alter=True,
        ),
        nullable=True,
    )
    last_heartbeat_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint("priority BETWEEN 1 AND 10", name="ck_tasks_priority"),
        CheckConstraint(
            "status IN ('pending', 'assigned', 'completed', 'cancelled')",
            name="ck_tasks_status",
        ),
        CheckConstraint("start_node <> end_node", name="ck_tasks_distinct_nodes"),
        Index("ix_tasks_dispatch_queue", "status", "priority", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    type: Mapped[str] = mapped_column(String(40), default="delivery", index=True)
    priority: Mapped[int] = mapped_column(Integer, default=3, index=True)
    start_node: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("map_nodes.id", name="fk_tasks_start_node"),
        nullable=False,
    )
    end_node: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("map_nodes.id", name="fk_tasks_end_node"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    assigned_robot_id: Mapped[str | None] = mapped_column(String(40), ForeignKey("robots.id"), nullable=True)
    estimated_distance: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, index=True)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class MapNode(Base):
    __tablename__ = "map_nodes"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    x: Mapped[float] = mapped_column(Float, nullable=False)
    y: Mapped[float] = mapped_column(Float, nullable=False)
    type: Mapped[str] = mapped_column(String(24), default="work")


class MapEdge(Base):
    __tablename__ = "map_edges"
    __table_args__ = (
        UniqueConstraint("from_node", "to_node", name="uq_map_edges_nodes"),
        CheckConstraint("distance > 0", name="ck_map_edges_distance"),
        CheckConstraint("from_node <> to_node", name="ck_map_edges_distinct_nodes"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    from_node: Mapped[str] = mapped_column(String(40), ForeignKey("map_nodes.id"), nullable=False)
    to_node: Mapped[str] = mapped_column(String(40), ForeignKey("map_nodes.id"), nullable=False)
    distance: Mapped[float] = mapped_column(Float, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class DispatchDecisionLog(Base):
    __tablename__ = "dispatch_decision_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(40), ForeignKey("tasks.id"), nullable=False, index=True)
    candidate_robots: Mapped[str] = mapped_column(Text, nullable=False)
    selected_robot_id: Mapped[str | None] = mapped_column(
        String(40),
        ForeignKey("robots.id", name="fk_dispatch_logs_selected_robot_id"),
        nullable=True,
    )
    score_detail: Mapped[str] = mapped_column(Text, nullable=False)
    decision_reason: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, index=True)
