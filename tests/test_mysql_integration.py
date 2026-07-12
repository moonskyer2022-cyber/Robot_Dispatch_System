import os
import threading
import unittest
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.dispatch import assign_next_task
from backend.models import DispatchDecisionLog, MapEdge, MapNode, Robot, Task
from backend.time_utils import utc_now


@unittest.skipUnless(
    os.getenv("TEST_DATABASE_URL"),
    "TEST_DATABASE_URL is required for MySQL integration tests",
)
class MySQLDispatchConcurrencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            os.environ["TEST_DATABASE_URL"],
            pool_pre_ping=True,
        )
        cls.session_factory = sessionmaker(bind=cls.engine, expire_on_commit=False)

    def setUp(self):
        suffix = uuid.uuid4().hex[:8]
        self.start_id = f"S{suffix}"
        self.end_id = f"E{suffix}"
        self.robot_id = f"R{suffix}"
        self.task_ids = [f"T{suffix}A", f"T{suffix}B"]
        with self.session_factory() as db:
            db.add_all(
                [
                    MapNode(id=self.start_id, name="Start", x=0, y=0),
                    MapNode(id=self.end_id, name="End", x=10, y=0),
                    Robot(
                        id=self.robot_id,
                        name="Concurrent Robot",
                        status="idle",
                        battery=100,
                        capability="delivery",
                        last_heartbeat_at=utc_now(),
                    ),
                ]
            )
            db.flush()
            db.add(
                MapEdge(
                    from_node=self.start_id,
                    to_node=self.end_id,
                    distance=10,
                )
            )
            db.add_all(
                [
                    Task(
                        id=self.task_ids[0],
                        type="delivery",
                        priority=10,
                        start_node=self.start_id,
                        end_node=self.end_id,
                    ),
                    Task(
                        id=self.task_ids[1],
                        type="delivery",
                        priority=9,
                        start_node=self.start_id,
                        end_node=self.end_id,
                    ),
                ]
            )
            db.commit()

    def tearDown(self):
        with self.session_factory() as db:
            robot = db.get(Robot, self.robot_id)
            if robot:
                robot.current_task_id = None
            db.flush()
            db.query(DispatchDecisionLog).filter(
                DispatchDecisionLog.task_id.in_(self.task_ids)
            ).delete(synchronize_session=False)
            db.query(Task).filter(Task.id.in_(self.task_ids)).delete(
                synchronize_session=False
            )
            db.query(MapEdge).filter(
                MapEdge.from_node == self.start_id,
                MapEdge.to_node == self.end_id,
            ).delete(synchronize_session=False)
            db.query(Robot).filter(Robot.id == self.robot_id).delete(
                synchronize_session=False
            )
            db.query(MapNode).filter(
                MapNode.id.in_([self.start_id, self.end_id])
            ).delete(synchronize_session=False)
            db.commit()

    def test_only_one_task_claims_the_robot(self):
        barrier = threading.Barrier(2)
        results = []

        def dispatch():
            with self.session_factory() as db:
                barrier.wait()
                task, robot, assigned, _, _ = assign_next_task(db)
                results.append((task.id if task else None, robot.id if robot else None, assigned))

        threads = [threading.Thread(target=dispatch) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        assigned_to_test_robot = [
            result for result in results if result[1] == self.robot_id and result[2]
        ]
        self.assertEqual(1, len(assigned_to_test_robot))
