"""Initial application schema.

Revision ID: 0001
Revises:
"""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "map_nodes",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("x", sa.Float(), nullable=False),
        sa.Column("y", sa.Float(), nullable=False),
        sa.Column("type", sa.String(24), nullable=False),
    )
    op.create_table(
        "robots",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("battery", sa.Integer(), nullable=False),
        sa.Column("x", sa.Float(), nullable=False),
        sa.Column("y", sa.Float(), nullable=False),
        sa.Column("capability", sa.String(80), nullable=False),
        sa.Column("current_task_id", sa.String(40), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_robots_status", "robots", ["status"])
    op.create_table(
        "tasks",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("type", sa.String(40), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("start_node", sa.String(40), nullable=False),
        sa.Column("end_node", sa.String(40), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("assigned_robot_id", sa.String(40), nullable=True),
        sa.Column("estimated_distance", sa.Float(), nullable=True),
        sa.Column("estimated_duration", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("assigned_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["assigned_robot_id"], ["robots.id"]),
    )
    op.create_index("ix_tasks_type", "tasks", ["type"])
    op.create_index("ix_tasks_priority", "tasks", ["priority"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_created_at", "tasks", ["created_at"])
    op.create_table(
        "map_edges",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("from_node", sa.String(40), nullable=False),
        sa.Column("to_node", sa.String(40), nullable=False),
        sa.Column("distance", sa.Float(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["from_node"], ["map_nodes.id"]),
        sa.ForeignKeyConstraint(["to_node"], ["map_nodes.id"]),
    )
    op.create_table(
        "dispatch_decision_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("task_id", sa.String(40), nullable=False),
        sa.Column("candidate_robots", sa.Text(), nullable=False),
        sa.Column("selected_robot_id", sa.String(40), nullable=True),
        sa.Column("score_detail", sa.Text(), nullable=False),
        sa.Column("decision_reason", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
    )
    op.create_index(
        "ix_dispatch_decision_logs_task_id",
        "dispatch_decision_logs",
        ["task_id"],
    )
    op.create_index(
        "ix_dispatch_decision_logs_created_at",
        "dispatch_decision_logs",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_table("dispatch_decision_logs")
    op.drop_table("map_edges")
    op.drop_table("tasks")
    op.drop_table("robots")
    op.drop_table("map_nodes")
