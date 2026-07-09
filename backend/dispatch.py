import json
import math
import os
from heapq import heappop, heappush
from datetime import timedelta

from sqlalchemy.orm import Session

from .models import DispatchDecisionLog, MapEdge, MapNode, Robot, Task
from .time_utils import utc_now

BATTERY_THRESHOLD = int(os.getenv("DISPATCH_BATTERY_THRESHOLD", "25"))
HEARTBEAT_OFFLINE_SECONDS = int(os.getenv("HEARTBEAT_OFFLINE_SECONDS", "120"))


def distance(a_x: float, a_y: float, b_x: float, b_y: float) -> float:
    return round(math.hypot(a_x - b_x, a_y - b_y), 2)


def shortest_route_distance(db: Session, start_node: str, end_node: str) -> float | None:
    if start_node == end_node:
        return 0

    edges = db.query(MapEdge).filter(MapEdge.enabled.is_(True)).all()
    graph: dict[str, list[tuple[str, float]]] = {}
    for edge in edges:
        graph.setdefault(edge.from_node, []).append((edge.to_node, edge.distance))
        graph.setdefault(edge.to_node, []).append((edge.from_node, edge.distance))

    queue: list[tuple[float, str]] = [(0, start_node)]
    best: dict[str, float] = {start_node: 0}

    while queue:
        current_distance, node = heappop(queue)
        if node == end_node:
            return round(current_distance, 2)
        if current_distance > best.get(node, math.inf):
            continue
        for next_node, edge_distance in graph.get(node, []):
            candidate = current_distance + edge_distance
            if candidate < best.get(next_node, math.inf):
                best[next_node] = candidate
                heappush(queue, (candidate, next_node))

    return None


def mark_stale_robots_offline(db: Session) -> int:
    stale_before = utc_now() - timedelta(seconds=HEARTBEAT_OFFLINE_SECONDS)
    stale_robots = (
        db.query(Robot)
        .filter(Robot.status.in_(["idle", "busy", "charging"]))
        .filter(Robot.last_heartbeat_at < stale_before)
        .all()
    )
    for robot in stale_robots:
        if robot.current_task_id:
            task = db.get(Task, robot.current_task_id)
            if (
                task
                and task.status == "assigned"
                and task.assigned_robot_id == robot.id
            ):
                task.status = "pending"
                task.assigned_robot_id = None
                task.assigned_at = None
                task.estimated_distance = None
                task.estimated_duration = None
                db.add(
                    DispatchDecisionLog(
                        task_id=task.id,
                        candidate_robots=json.dumps([robot.id]),
                        selected_robot_id=None,
                        score_detail=json.dumps([]),
                        decision_reason=f"机器人 {robot.name} 心跳超时，任务已退回队列",
                    )
                )
            robot.current_task_id = None
        robot.status = "offline"
    return len(stale_robots)


def estimate_task_distance(db: Session, robot: Robot, task: Task) -> tuple[float, int]:
    start = db.get(MapNode, task.start_node)
    end = db.get(MapNode, task.end_node)
    if not start or not end:
        return 0, 0
    approach = distance(robot.x, robot.y, start.x, start.y)
    route = shortest_route_distance(db, task.start_node, task.end_node)
    if route is None:
        route = distance(start.x, start.y, end.x, end.y)
    total = round(approach + route, 2)
    duration_seconds = int(total * 12)
    return total, duration_seconds


def score_robot(db: Session, robot: Robot, task: Task) -> dict:
    start = db.get(MapNode, task.start_node)
    end = db.get(MapNode, task.end_node)
    if not start or not end:
        return {
            "robot_id": robot.id,
            "eligible": False,
            "score": 999999,
            "reason": "任务起点或终点不存在",
        }

    if robot.status != "idle":
        return {
            "robot_id": robot.id,
            "eligible": False,
            "score": 999999,
            "reason": f"机器人状态为 {robot.status}",
        }
    if robot.battery < BATTERY_THRESHOLD:
        return {
            "robot_id": robot.id,
            "eligible": False,
            "score": 999999,
            "reason": f"电量低于阈值 {BATTERY_THRESHOLD}%",
        }
    if task.type not in robot.capability.split(","):
        return {
            "robot_id": robot.id,
            "eligible": False,
            "score": 999999,
            "reason": "能力不匹配",
        }

    approach = distance(robot.x, robot.y, start.x, start.y)
    route = shortest_route_distance(db, task.start_node, task.end_node)
    if route is None:
        route = distance(start.x, start.y, end.x, end.y)
    battery_cost = 100 - robot.battery
    priority_bonus = task.priority * 2
    score = round(approach * 0.55 + route * 0.25 + battery_cost * 0.12 - priority_bonus, 2)
    return {
        "robot_id": robot.id,
        "robot_name": robot.name,
        "eligible": True,
        "score": score,
        "approach_distance": approach,
        "route_distance": route,
        "battery": robot.battery,
        "reason": "在线空闲、电量充足、能力匹配",
    }


def suggest_for_task(db: Session, task: Task) -> tuple[Robot | None, list[dict], str]:
    robots = db.query(Robot).order_by(Robot.id).all()
    scores = [score_robot(db, robot, task) for robot in robots]
    eligible = [item for item in scores if item["eligible"]]
    if not eligible:
        return None, scores, "没有符合条件的空闲机器人"
    winner_score = sorted(eligible, key=lambda item: item["score"])[0]
    return db.get(Robot, winner_score["robot_id"]), scores, "选择综合评分最低的机器人"


def claim_best_robot(db: Session, task: Task) -> tuple[Robot | None, list[dict], str]:
    robots = db.query(Robot).order_by(Robot.id).all()
    scores = [score_robot(db, robot, task) for robot in robots]
    eligible = sorted(
        (item for item in scores if item["eligible"]),
        key=lambda item: item["score"],
    )

    for candidate in eligible:
        claimed = (
            db.query(Robot)
            .filter(
                Robot.id == candidate["robot_id"],
                Robot.status == "idle",
                Robot.current_task_id.is_(None),
            )
            .update(
                {
                    Robot.status: "busy",
                    Robot.current_task_id: task.id,
                },
                synchronize_session=False,
            )
        )
        if claimed:
            db.expire_all()
            robot = db.get(Robot, candidate["robot_id"])
            return robot, scores, "选择综合评分最低的机器人"

    return None, scores, "当前没有可用的机器人"


def assign_next_task(db: Session):
    mark_stale_robots_offline(db)
    task = (
        db.query(Task)
        .filter(Task.status == "pending")
        .order_by(Task.priority.desc(), Task.created_at.asc())
        .with_for_update(skip_locked=True)
        .first()
    )
    if not task:
        db.commit()
        return None, None, False, "没有待调度任务", []

    robot, scores, reason = claim_best_robot(db, task)
    selected_id = robot.id if robot else None

    if robot:
        total_distance, duration = estimate_task_distance(db, robot, task)
        task.status = "assigned"
        task.assigned_robot_id = robot.id
        task.assigned_at = utc_now()
        task.estimated_distance = total_distance
        task.estimated_duration = duration
        robot.status = "busy"
        robot.current_task_id = task.id
        reason = f"{reason}：{robot.name}"
        assigned = True
    else:
        assigned = False

    log = DispatchDecisionLog(
        task_id=task.id,
        candidate_robots=json.dumps([item.get("robot_id") for item in scores], ensure_ascii=False),
        selected_robot_id=selected_id,
        score_detail=json.dumps(scores, ensure_ascii=False),
        decision_reason=reason,
    )
    db.add(log)
    db.commit()
    return task, robot, assigned, reason, scores
