import unittest
from datetime import datetime

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base
from backend.dispatch import assign_next_task
from backend.main import heartbeat
from backend.models import MapEdge, MapNode, Robot, Task
from backend.schemas import RobotCreate, RobotHeartbeat, TaskCreate


class DispatchSafetyTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)()
        now = datetime.utcnow()
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


if __name__ == "__main__":
    unittest.main()
