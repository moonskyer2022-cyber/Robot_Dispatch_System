from sqlalchemy.orm import Session

from .models import MapEdge, MapNode, Robot
from .time_utils import utc_now


def seed_initial_data(db: Session) -> None:
    nodes = [
        MapNode(id="A01", name="入库口 A01", x=8, y=18, type="work"),
        MapNode(id="A02", name="入库口 A02", x=20, y=18, type="work"),
        MapNode(id="B08", name="打包区 B08", x=68, y=22, type="work"),
        MapNode(id="C03", name="存储区 C03", x=42, y=48, type="work"),
        MapNode(id="D01", name="出库口 D01", x=80, y=64, type="work"),
        MapNode(id="CHG", name="充电站", x=12, y=68, type="charging"),
    ]
    for node in nodes:
        if not db.get(MapNode, node.id):
            db.add(node)
    db.flush()

    edges = [
        ("A01", "A02", 12),
        ("A02", "C03", 32),
        ("C03", "B08", 38),
        ("B08", "D01", 44),
        ("C03", "CHG", 35),
        ("A01", "CHG", 50),
    ]
    existing_edges = {
        (edge.from_node, edge.to_node)
        for edge in db.query(MapEdge).all()
    }
    for from_node, to_node, edge_distance in edges:
        if (from_node, to_node) not in existing_edges:
            db.add(
                MapEdge(
                    from_node=from_node,
                    to_node=to_node,
                    distance=edge_distance,
                )
            )

    now = utc_now()
    robots = [
        Robot(id="R01", name="一号车", status="idle", battery=86, x=15, y=20, capability="delivery,inspection", last_heartbeat_at=now),
        Robot(id="R02", name="二号车", status="idle", battery=62, x=44, y=45, capability="delivery", last_heartbeat_at=now),
        Robot(id="R03", name="三号车", status="charging", battery=18, x=12, y=68, capability="delivery", last_heartbeat_at=now),
        Robot(id="R04", name="四号车", status="offline", battery=54, x=76, y=60, capability="inspection", last_heartbeat_at=now),
    ]
    for robot in robots:
        if not db.get(Robot, robot.id):
            db.add(robot)

    db.commit()
