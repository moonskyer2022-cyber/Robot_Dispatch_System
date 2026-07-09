import unittest
from datetime import timedelta

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base
from backend.dispatch import assign_next_task, mark_stale_robots_offline
from backend.main import cancel_task, heartbeat, suggest_dispatch
from backend.models import DispatchDecisionLog, MapEdge, MapNode, Robot, Task
from backend.schemas import DecisionLogOut, RobotCreate, RobotHeartbeat, RobotOut, TaskCreate
from backend.time_utils import utc_now


class DispatchSafetyTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)()
        now = utc_now()
        self.session.add_all(
            [
                MapNode(id="A", name="Start", x=0, y=0),
                MapNode(id="B", name="End", x=10, y=0),
                MapEdge(from_node="A", to_node="B", distance=10),
                Robot(
                    id="R1",
                    name="Robot 1",
                    status="idle",
                    battery=100,
                    capability="delivery",
                    last_heartbeat_at=now,
                ),
                Task(
                    id="T1",
                    type="delivery",
                    priority=5,
                    start_node="A",
                    end_node="B",
                ),
                Task(
                    id="T2",
                    type="delivery",
                    priority=4,
                    start_node="A",
                    end_node="B",
                ),
            ]
        )
        self.session.commit()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_robot_cannot_be_claimed_by_two_tasks(self):
        first_task, first_robot, assigned, _, _ = assign_next_task(self.session)
        self.assertTrue(assigned)
        self.assertEqual("T1", first_task.id)
        self.assertEqual("R1", first_robot.id)

        second_task, second_robot, assigned, _, _ = assign_next_task(self.session)
        self.assertFalse(assigned)
        self.assertEqual("T2", second_task.id)
        self.assertIsNone(second_robot)
        self.assertEqual("pending", second_task.status)

    def test_heartbeat_cannot_clear_server_assignment(self):
        assign_next_task(self.session)
        payload = RobotHeartbeat(
            status="idle",
            battery=90,
            x=1,
            y=1,
            current_task_id=None,
        )

        with self.assertRaises(HTTPException) as raised:
            heartbeat("R1", payload, self.session)

        self.assertEqual(409, raised.exception.status_code)

    def test_heartbeat_cannot_claim_busy_without_assignment(self):
        payload = RobotHeartbeat(
            status="busy",
            battery=90,
            x=1,
            y=1,
            current_task_id=None,
        )

        with self.assertRaises(HTTPException) as raised:
            heartbeat("R1", payload, self.session)

        self.assertEqual(409, raised.exception.status_code)

    def test_request_models_reject_invalid_or_blank_values(self):
        with self.assertRaises(ValidationError):
            RobotCreate(id=" ", name="Robot", status="busy")
        with self.assertRaises(ValidationError):
            TaskCreate(type=" ", start_node="A", end_node="B")
        with self.assertRaises(ValidationError):
            TaskCreate(type="delivery", start_node="A", end_node="A")

    def test_capabilities_are_normalized_and_busy_robot_can_be_serialized(self):
        payload = RobotCreate(
            id="R2",
            name="Robot 2",
            capability="delivery, inspection,delivery",
        )
        self.assertEqual("delivery,inspection", payload.capability)
        robot = self.session.get(Robot, "R1")
        robot.status = "busy"
        output = RobotOut.model_validate(robot)
        self.assertEqual("busy", output.status)

    def test_cancelling_assigned_task_releases_robot(self):
        assign_next_task(self.session)

        task = cancel_task("T1", self.session)

        robot = self.session.get(Robot, "R1")
        self.assertEqual("cancelled", task.status)
        self.assertEqual("idle", robot.status)
        self.assertIsNone(robot.current_task_id)

    def test_stale_robot_requeues_assigned_task(self):
        assign_next_task(self.session)
        robot = self.session.get(Robot, "R1")
        robot.last_heartbeat_at = utc_now() - timedelta(days=1)
        self.session.commit()

        changed = mark_stale_robots_offline(self.session)
        self.session.commit()

        task = self.session.get(Task, "T1")
        self.assertEqual(1, changed)
        self.assertEqual("offline", robot.status)
        self.assertIsNone(robot.current_task_id)
        self.assertEqual("pending", task.status)
        self.assertIsNone(task.assigned_robot_id)

    def test_suggestion_rejects_non_pending_task(self):
        assign_next_task(self.session)

        with self.assertRaises(HTTPException) as raised:
            suggest_dispatch("T1", self.session)

        self.assertEqual(409, raised.exception.status_code)

    def test_decision_log_output_parses_json_fields(self):
        log = DispatchDecisionLog(
            id=1,
            task_id="T1",
            candidate_robots='["R1"]',
            selected_robot_id="R1",
            score_detail='[{"robot_id": "R1", "score": 1}]',
            decision_reason="selected",
            created_at=utc_now(),
        )

        output = DecisionLogOut.model_validate(log)

        self.assertEqual(["R1"], output.candidate_robots)
        self.assertEqual("R1", output.score_detail[0]["robot_id"])


if __name__ == "__main__":
    unittest.main()
