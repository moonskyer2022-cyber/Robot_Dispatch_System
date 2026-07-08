from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Robot(Base):
    __tablename__ = "robots"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="idle", index=True)
    battery: Mapped[int] = mapped_column(Integer, default=100)
    x: Mapped[float] = mapped_column(Float, default=0)
    y: Mapped[float] = mapped_column(Float, default=0)
    capability: Mapped[str] = mapped_column(String(80), default="delivery")
    current_task_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    last_heartbeat_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    type: Mapped[str] = mapped_column(String(40), default="delivery", index=True)
    priority: Mapped[int] = mapped_column(Integer, default=3, index=True)
    start_node: Mapped[str] = mapped_column(String(40), nullable=False)
    end_node: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    assigned_robot_id: Mapped[str | None] = mapped_column(String(40), ForeignKey("robots.id"), nullable=True)
    estimated_distance: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
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
    selected_robot_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    score_detail: Mapped[str] = mapped_column(Text, nullable=False)
    decision_reason: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
