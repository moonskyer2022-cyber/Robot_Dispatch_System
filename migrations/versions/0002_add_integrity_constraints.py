"""Add relational and domain integrity constraints.

Revision ID: 0002
Revises: 0001
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_robots_status",
        "robots",
        "status IN ('idle', 'busy', 'charging', 'offline')",
    )
    op.create_check_constraint(
        "ck_robots_battery",
        "robots",
        "battery BETWEEN 0 AND 100",
    )
    op.create_check_constraint(
        "ck_tasks_priority",
        "tasks",
        "priority BETWEEN 1 AND 10",
    )
    op.create_check_constraint(
        "ck_tasks_status",
        "tasks",
        "status IN ('pending', 'assigned', 'completed', 'cancelled')",
    )
    op.create_check_constraint(
        "ck_tasks_distinct_nodes",
        "tasks",
        "start_node <> end_node",
    )
    op.create_check_constraint(
        "ck_map_edges_distance",
        "map_edges",
        "distance > 0",
    )
    op.create_check_constraint(
        "ck_map_edges_distinct_nodes",
        "map_edges",
        "from_node <> to_node",
    )
    op.create_foreign_key(
        "fk_robots_current_task_id",
        "robots",
        "tasks",
        ["current_task_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_tasks_start_node",
        "tasks",
        "map_nodes",
        ["start_node"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_tasks_end_node",
        "tasks",
        "map_nodes",
        ["end_node"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_dispatch_logs_selected_robot_id",
        "dispatch_decision_logs",
        "robots",
        ["selected_robot_id"],
        ["id"],
    )
    op.create_unique_constraint(
        "uq_map_edges_nodes",
        "map_edges",
        ["from_node", "to_node"],
    )
    op.create_index(
        "ix_tasks_dispatch_queue",
        "tasks",
        ["status", "priority", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_tasks_dispatch_queue", table_name="tasks")
    op.drop_constraint("uq_map_edges_nodes", "map_edges", type_="unique")
    op.drop_constraint(
        "fk_dispatch_logs_selected_robot_id",
        "dispatch_decision_logs",
        type_="foreignkey",
    )
    op.drop_constraint("fk_tasks_end_node", "tasks", type_="foreignkey")
    op.drop_constraint("fk_tasks_start_node", "tasks", type_="foreignkey")
    op.drop_constraint("fk_robots_current_task_id", "robots", type_="foreignkey")
    op.drop_constraint("ck_map_edges_distinct_nodes", "map_edges", type_="check")
    op.drop_constraint("ck_map_edges_distance", "map_edges", type_="check")
    op.drop_constraint("ck_tasks_distinct_nodes", "tasks", type_="check")
    op.drop_constraint("ck_tasks_status", "tasks", type_="check")
    op.drop_constraint("ck_tasks_priority", "tasks", type_="check")
    op.drop_constraint("ck_robots_battery", "robots", type_="check")
    op.drop_constraint("ck_robots_status", "robots", type_="check")
