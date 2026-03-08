import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# --- 動態載入專案配置 ---
# 將專案根目錄加入 sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.core.config import get_settings
from app.db.base import Base
# 務必導入所有模型，Alembic 才能偵測到它們
from app.db import models # noqa

# ----------------------

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    # 在離線模式下，我們直接使用配置中的 URL
    settings = get_settings()
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # 獲取專案的配置
    settings = get_settings()
    
    # 建立一個包含動態資料庫 URL 的配置字典
    connectable_config = config.get_section(config.config_ini_section, {})
    connectable_config["sqlalchemy.url"] = settings.database_url
    
    connectable = engine_from_config(
        connectable_config,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
