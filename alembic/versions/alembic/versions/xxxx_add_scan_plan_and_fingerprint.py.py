"""add scan plans, task logs, fingerprint rules and asset normalization fields

Revision ID: xxxx_add_scan_plan_and_fingerprint
Revises: 2dda8be41af7
Create Date: 2026-01-07 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "xxxx_add_scan_plan_and_fingerprint"
down_revision: Union[str, None] = "2dda8be41af7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) 新增掃描方案相關表
    op.create_table(
        "scan_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("options", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_scan_plans_id", "scan_plans", ["id"], unique=False)

    op.create_table(
        "scan_plan_tools",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scan_plan_id", sa.Integer(), nullable=False),
        sa.Column("tool_name", sa.String(length=100), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=True),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["scan_plan_id"], ["scan_plans.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scan_plan_id", "tool_name", name="uix_scan_plan_tool"),
    )
    op.create_index(
        "ix_scan_plan_tools_id", "scan_plan_tools", ["id"], unique=False
    )
    op.create_index(
        "ix_scan_plan_tools_scan_plan_id",
        "scan_plan_tools",
        ["scan_plan_id"],
        unique=False,
    )

    # 2) 新增任務日誌表
    op.create_table(
        "task_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("phase", sa.String(length=50), nullable=False),
        sa.Column("level", sa.String(length=20), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_task_logs_id", "task_logs", ["id"], unique=False)
    op.create_index("ix_task_logs_task_id", "task_logs", ["task_id"], unique=False)
    op.create_index("ix_task_logs_phase", "task_logs", ["phase"], unique=False)
    op.create_index(
        "ix_task_logs_created_at", "task_logs", ["created_at"], unique=False
    )

    # 3) 新增指紋規則表
    op.create_table(
        "fingerprint_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=True),
        sa.Column("target", sa.String(length=50), nullable=False),
        sa.Column("pattern", sa.String(length=2048), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(
        "ix_fingerprint_rules_id", "fingerprint_rules", ["id"], unique=False
    )
    op.create_index(
        "ix_fingerprint_rules_enabled",
        "fingerprint_rules",
        ["enabled"],
        unique=False,
    )

    # 4) tasks 表增加 scan_plan_id
    op.add_column(
        "tasks",
        sa.Column("scan_plan_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_tasks_scan_plan_id", "tasks", ["scan_plan_id"], unique=False
    )
    op.create_foreign_key(
        "fk_tasks_scan_plan_id_scan_plans",
        source_table="tasks",
        referent_table="scan_plans",
        local_cols=["scan_plan_id"],
        remote_cols=["id"],
    )

    # 5) assets 表增加規範化字段
    op.add_column(
        "assets",
        sa.Column("domain", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "assets",
        sa.Column("ip_address", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "assets",
        sa.Column("port", sa.Integer(), nullable=True),
    )
    op.add_column(
        "assets",
        sa.Column("protocol", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "assets",
        sa.Column("product", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "assets",
        sa.Column("url", sa.String(length=2048), nullable=True),
    )

    op.create_index("ix_assets_domain", "assets", ["domain"], unique=False)
    op.create_index("ix_assets_ip_address", "assets", ["ip_address"], unique=False)
    op.create_index("ix_assets_port", "assets", ["port"], unique=False)


def downgrade() -> None:
    # 5) 回滾 assets 字段與索引
    op.drop_index("ix_assets_port", table_name="assets")
    op.drop_index("ix_assets_ip_address", table_name="assets")
    op.drop_index("ix_assets_domain", table_name="assets")
    op.drop_column("assets", "url")
    op.drop_column("assets", "product")
    op.drop_column("assets", "protocol")
    op.drop_column("assets", "port")
    op.drop_column("assets", "ip_address")
    op.drop_column("assets", "domain")

    # 4) 回滾 tasks.scan_plan_id
    op.drop_constraint(
        "fk_tasks_scan_plan_id_scan_plans", "tasks", type_="foreignkey"
    )
    op.drop_index("ix_tasks_scan_plan_id", table_name="tasks")
    op.drop_column("tasks", "scan_plan_id")

    # 3) 回滾 fingerprint_rules
    op.drop_index("ix_fingerprint_rules_enabled", table_name="fingerprint_rules")
    op.drop_index("ix_fingerprint_rules_id", table_name="fingerprint_rules")
    op.drop_table("fingerprint_rules")

    # 2) 回滾 task_logs
    op.drop_index("ix_task_logs_created_at", table_name="task_logs")
    op.drop_index("ix_task_logs_phase", table_name="task_logs")
    op.drop_index("ix_task_logs_task_id", table_name="task_logs")
    op.drop_index("ix_task_logs_id", table_name="task_logs")
    op.drop_table("task_logs")

    # 1) 回滾掃描方案相關表
    op.drop_index(
        "ix_scan_plan_tools_scan_plan_id", table_name="scan_plan_tools"
    )
    op.drop_index("ix_scan_plan_tools_id", table_name="scan_plan_tools")
    op.drop_table("scan_plan_tools")

    op.drop_index("ix_scan_plans_id", table_name="scan_plans")
    op.drop_table("scan_plans")