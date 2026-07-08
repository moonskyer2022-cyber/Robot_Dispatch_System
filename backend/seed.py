from datetime import datetime

from sqlalchemy.orm import Session

from .models import MapEdge, MapNode, Robot


def seed_initial_data(db: Session) -> None:
    if db.query(MapNode).count() == 0:
        nodes = [
            MapNode(id="A01", name="入库口 A01", x=8, y=18, type="work"),
            MapNode(id="A02", name="入库口 A02", x=20, y=18, type="work"),
            MapNode(id="B08", name="打包区 B08", x=68, y=22, type="work"),
            MapNode(id="C03", name="存储区 C03", x=42, y=48, type="work"),
            MapNode(id="D01", name="出库口 D01", x=80, y=64, type="work"),
            MapNode(id="CHG", name="充电站", x=12, y=68, type="charging"),
        ]
        db.add_all(nodes)
        db.commit()
        edges = [
            ("A01", "A02", 12),
            ("A02", "C03", 32),
            ("C03", "B08", 38),
            ("B08", "D01", 44),
            ("C03", "CHG", 35),
            ("A01", "CHG", 50),
        ]
        db.add_all([MapEdge(from_node=a, to_node=b, distance=d) for a, b, d in edges])

    if db.query(Robot).count() == 0:
        now = datetime.utcnow()
        db.add_all(
            [
                Robot(id="R01", name="一号车", status="idle", battery=86, x=15, y=20, capability="delivery,inspection", last_heartbeat_at=now),
                Robot(id="R02", name="二号车", status="idle", battery=62, x=44, y=45, capability="delivery", last_heartbeat_at=now),
                Robot(id="R03", name="三号车", status="charging", battery=18, x=12, y=68, capability="delivery", last_heartbeat_at=now),
                Robot(id="R04", name="四号车", status="offline", battery=54, x=76, y=60, capability="inspection", last_heartbeat_at=now),
            ]
        )

    db.commit()
