"""Reset the configured database to the built-in demo dataset."""

from backend.database import SessionLocal
from backend.models import DispatchDecisionLog, MapEdge, MapNode, Robot, Task
from backend.seed import seed_initial_data


def reset_demo_data() -> None:
    with SessionLocal() as db:
        # Break the circular robot <-> task references before deleting rows.
        db.query(Robot).update({Robot.current_task_id: None})
        db.flush()
        db.query(DispatchDecisionLog).delete(synchronize_session=False)
        db.query(Task).delete(synchronize_session=False)
        db.query(Robot).delete(synchronize_session=False)
        db.query(MapEdge).delete(synchronize_session=False)
        db.query(MapNode).delete(synchronize_session=False)
        db.commit()
        seed_initial_data(db)


if __name__ == "__main__":
    reset_demo_data()
    print("demo data reset")
