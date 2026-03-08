from __future__ import annotations

from celery import Celery
from kombu import Exchange, Queue

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "security_platform",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks"],
)

# --- Queues (per-tool) ---
celery_app.conf.task_queues = (
    Queue("tool.fofa", Exchange("tool.fofa"), routing_key="tool.fofa"),
    Queue("tool.subfinder", Exchange("tool.subfinder"), routing_key="tool.subfinder"),
    Queue("tool.nmap", Exchange("tool.nmap"), routing_key="tool.nmap"),
    Queue("tool.httpx", Exchange("tool.httpx"), routing_key="tool.httpx"),
    Queue("tool.nuclei", Exchange("tool.nuclei"), routing_key="tool.nuclei"),
    Queue("tool.pipeline", Exchange("tool.pipeline"), routing_key="tool.pipeline"),
)

celery_app.conf.task_default_queue = "tool.pipeline"
celery_app.conf.task_default_exchange = "tool.pipeline"
celery_app.conf.task_default_routing_key = "tool.pipeline"

# --- Routing ---
celery_app.conf.task_routes = {
    "app.workers.tasks.run_fofa_pull": {"queue": "tool.fofa", "routing_key": "tool.fofa"},
    "app.workers.tasks.run_hunter_pull": {"queue": "tool.fofa", "routing_key": "tool.fofa"},  # Hunter 使用 fofa 队列
    "app.workers.tasks.run_subfinder": {"queue": "tool.subfinder", "routing_key": "tool.subfinder"},
    "app.workers.tasks.run_nmap": {"queue": "tool.nmap", "routing_key": "tool.nmap"},
    "app.workers.tasks.run_httpx": {"queue": "tool.httpx", "routing_key": "tool.httpx"},
    "app.workers.tasks.run_nuclei": {"queue": "tool.nuclei", "routing_key": "tool.nuclei"},
    "app.workers.tasks.run_pipeline": {"queue": "tool.pipeline", "routing_key": "tool.pipeline"},
    "app.workers.tasks.aggregate_pipeline_results": {"queue": "tool.pipeline", "routing_key": "tool.pipeline"},
    "app.workers.tasks.check_and_aggregate": {"queue": "tool.pipeline", "routing_key": "tool.pipeline"},
}

# Sensible defaults for long-running external tool execution
celery_app.conf.worker_prefetch_multiplier = 1
celery_app.conf.task_acks_late = True
celery_app.conf.task_reject_on_worker_lost = True
celery_app.conf.task_time_limit = 60 * 60 * 6  # 6h hard limit
celery_app.conf.task_soft_time_limit = 60 * 60 * 5 + 50  # 5h50m soft limit

