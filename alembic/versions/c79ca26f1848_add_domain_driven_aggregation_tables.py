"""add domain driven aggregation tables

Revision ID: c79ca26f1848
Revises: 4acb54529c8f
Create Date: 2026-03-08 13:03:54.039460

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c79ca26f1848'
down_revision: Union[str, None] = '4acb54529c8f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 domains 表
    op.create_table(
        'domains',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('root_domain', sa.String(255), nullable=True),
        sa.Column('discovered_by', sa.String(50), nullable=False, server_default='subfinder'),
        sa.Column('discovered_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('scan_status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('ip_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('endpoint_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('source_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'task_id', 'name')
    )

    op.create_index('idx_domains_task', 'domains', ['tenant_id', 'task_id'])
    op.create_index('idx_domains_root', 'domains', ['tenant_id', 'root_domain'])
    op.create_index('idx_domains_status', 'domains', ['tenant_id', 'scan_status'])

    # 创建 domain_ips 表
    op.create_table(
        'domain_ips',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('domain_id', sa.Integer(), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=False),  # IPv6 compatible
        sa.Column('port', sa.Integer(), nullable=False),
        sa.Column('protocol', sa.String(20), nullable=True),
        sa.Column('sources', postgresql.ARRAY(sa.String(50)), nullable=True),
        sa.Column('discovered_by', postgresql.JSONB(), nullable=True),
        sa.Column('product', sa.String(255), nullable=True),
        sa.Column('product_version', sa.String(100), nullable=True),
        sa.Column('os', sa.String(100), nullable=True),
        sa.Column('banner', sa.Text(), nullable=True),
        sa.Column('raw_data', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['domain_id'], ['domains.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('tenant_id', 'domain_id', 'ip_address', 'port')
    )

    op.create_index('idx_domain_ips_domain', 'domain_ips', ['domain_id'])
    op.create_index('idx_domain_ips_ip', 'domain_ips', ['ip_address'])
    op.create_index('idx_domain_ips_sources', 'domain_ips', ['sources'], postgresql_using='gin')

    # 创建 domain_endpoints 表
    op.create_table(
        'domain_endpoints',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('domain_ip_id', sa.Integer(), nullable=False),
        sa.Column('path', sa.String(2048), nullable=False),
        sa.Column('method', sa.String(10), nullable=False, server_default='GET'),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('content_type', sa.String(255), nullable=True),
        sa.Column('content_length', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(512), nullable=True),
        sa.Column('technologies', postgresql.ARRAY(sa.String(100)), nullable=True),
        sa.Column('discovered_by', sa.String(50), nullable=True),
        sa.Column('discovered_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('response_body_hash', sa.String(64), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['domain_ip_id'], ['domain_ips.id'], ondelete='CASCADE')
    )

    op.create_index('idx_endpoints_ip', 'domain_endpoints', ['domain_ip_id'])
    op.create_index('idx_endpoints_path', 'domain_endpoints', ['path'])


def downgrade() -> None:
    op.drop_index('idx_endpoints_path', table_name='domain_endpoints')
    op.drop_index('idx_endpoints_ip', table_name='domain_endpoints')
    op.drop_table('domain_endpoints')

    op.drop_index('idx_domain_ips_sources', table_name='domain_ips')
    op.drop_index('idx_domain_ips_ip', table_name='domain_ips')
    op.drop_index('idx_domain_ips_domain', table_name='domain_ips')
    op.drop_table('domain_ips')

    op.drop_index('idx_domains_status', table_name='domains')
    op.drop_index('idx_domains_root', table_name='domains')
    op.drop_index('idx_domains_task', table_name='domains')
    op.drop_table('domains')
