import os
import uuid
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine, get_db
from .dispatch import assign_next_task, mark_stale_robots_offline, suggest_for_task
from .models import DispatchDecisionLog, MapEdge, MapNode, Robot, Task
from .schemas import (
    DecisionLogOut,
    DispatchResult,
    MapEdgeOut,
    MapNodeOut,
    RobotCreate,
    RobotHeartbeat,
    RobotOut,
    TaskCreate,
    TaskOut,
)
from .seed import seed_initial_data
from .time_utils import utc_now

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_initial_data(db)
    yield


app = FastAPI(
    title="AI Robot Dispatch System",
    version="0.2.0",
    lifespan=lifespan,
)

CORS_ALLOW_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOW_ORIGINS",
        "http://localhost:8000,http://127.0.0.1:8000",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(_: Request, exc: SQLAlchemyError):
    logger.exception("Database operation failed", exc_info=exc)
    return JSONResponse(status_code=503, content={"detail": "Database operation failed"})


@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    return {"status": "ok", "service": "robot-dispatch", "database": "ok"}


@app.get("/api/robots", response_model=list[RobotOut])
def list_robots(db: Session = Depends(get_db)):
    if mark_stale_robots_offline(db):
        db.commit()
    return db.query(Robot).order_by(Robot.id).all()


@app.post("/api/robots", response_model=RobotOut)
def create_robot(payload: RobotCreate, db: Session = Depends(get_db)):
    if db.get(Robot, payload.id):
        raise HTTPException(status_code=409, detail="Robot already exists")
    robot = Robot(**payload.model_dump(), last_heartbeat_at=utc_now())
    db.add(robot)
    db.commit()
    db.refresh(robot)
    return robot


@app.post("/api/robots/{robot_id}/heartbeat", response_model=RobotOut)
def heartbeat(robot_id: str, payload: RobotHeartbeat, db: Session = Depends(get_db)):
    robot = db.get(Robot, robot_id)
    if not robot:
        raise HTTPException(status_code=404, detail="Robot not found")
    if robot.current_task_id:
        if payload.current_task_id != robot.current_task_id or payload.status != "busy":
            raise HTTPException(
                status_code=409,
                detail="Heartbeat conflicts with the robot's assigned task",
            )
    elif payload.current_task_id is not None or payload.status == "busy":
        raise HTTPException(
            status_code=409,
            detail="Busy tasks can only be assigned by the dispatch service",
        )
    robot.status = payload.status
    robot.battery = payload.battery
    robot.x = payload.x
    robot.y = payload.y
    robot.current_task_id = payload.current_task_id
    robot.last_heartbeat_at = utc_now()
    db.commit()
    db.refresh(robot)
    return robot


@app.get("/api/tasks", response_model=list[TaskOut])
def list_tasks(db: Session = Depends(get_db)):
    return db.query(Task).order_by(Task.created_at.desc()).limit(100).all()


@app.post("/api/tasks", response_model=TaskOut)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    if not db.get(MapNode, payload.start_node) or not db.get(MapNode, payload.end_node):
        raise HTTPException(status_code=400, detail="Unknown start_node or end_node")
    task = Task(id=f"T{uuid.uuid4().hex[:8].upper()}", **payload.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@app.post("/api/tasks/{task_id}/complete", response_model=TaskOut)
def complete_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).with_for_update().first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status == "completed":
        return task
    if task.status != "assigned":
        raise HTTPException(status_code=409, detail="Only assigned tasks can be completed")
    task.status = "completed"
    task.completed_at = utc_now()
    if task.assigned_robot_id:
        robot = (
            db.query(Robot)
            .filter(Robot.id == task.assigned_robot_id)
            .with_for_update()
            .first()
        )
        if robot and robot.current_task_id == task.id:
            robot.status = "idle"
            robot.current_task_id = None
    db.commit()
    db.refresh(task)
    return task


@app.post("/api/tasks/{task_id}/cancel", response_model=TaskOut)
def cancel_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).with_for_update().first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status == "cancelled":
        return task
    if task.status not in {"pending", "assigned"}:
        raise HTTPException(
            status_code=409,
            detail="Only pending or assigned tasks can be cancelled",
        )
    if task.assigned_robot_id:
        robot = (
            db.query(Robot)
            .filter(Robot.id == task.assigned_robot_id)
            .with_for_update()
            .first()
        )
        if robot and robot.current_task_id == task.id:
            robot.status = "idle"
            robot.current_task_id = None
    task.status = "cancelled"
    db.commit()
    db.refresh(task)
    return task


@app.post("/api/dispatch/run", response_model=DispatchResult)
def run_dispatch(db: Session = Depends(get_db)):
    task, robot, assigned, reason, scores = assign_next_task(db)
    return DispatchResult(
        task_id=task.id if task else None,
        selected_robot_id=robot.id if robot else None,
        assigned=assigned,
        reason=reason,
        score_detail=scores,
    )


@app.post("/api/dispatch/suggest/{task_id}", response_model=DispatchResult)
def suggest_dispatch(task_id: str, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != "pending":
        raise HTTPException(status_code=409, detail="Only pending tasks can be evaluated")
    robot, scores, reason = suggest_for_task(db, task)
    return DispatchResult(
        task_id=task.id,
        selected_robot_id=robot.id if robot else None,
        assigned=False,
        reason=reason,
        score_detail=scores,
    )


@app.get("/api/dispatch/logs", response_model=list[DecisionLogOut])
def dispatch_logs(db: Session = Depends(get_db)):
    return db.query(DispatchDecisionLog).order_by(DispatchDecisionLog.created_at.desc()).limit(50).all()


@app.get("/api/map/nodes", response_model=list[MapNodeOut])
def map_nodes(db: Session = Depends(get_db)):
    return db.query(MapNode).order_by(MapNode.id).all()


@app.get("/api/map/edges", response_model=list[MapEdgeOut])
def map_edges(db: Session = Depends(get_db)):
    return db.query(MapEdge).filter(MapEdge.enabled.is_(True)).order_by(MapEdge.id).all()


FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
