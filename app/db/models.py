from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, String, Text, JSON, Enum as SQLEnum,
    UniqueConstraint, Index
)
from sqlalchemy.orm import relationship

from .base import Base


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AssetType(str, Enum):
    DOMAIN = "domain"
    SUBDOMAIN = "subdomain"
    IP = "ip"
    URL = "url"
    ENDPOINT = "endpoint"


class CredentialProvider(str, Enum):
    FOFA = "fofa"
    HUNTER = "hunter"
    # reserved: SHODAN = "shodan" etc.


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 1:1 relationship with User
    user = relationship("User", back_populates="tenant", uselist=False)
    
    # 1:N relationships
    tasks = relationship("Task", back_populates="tenant")
    assets = relationship("Asset", back_populates="tenant")
    vulnerabilities = relationship("Vulnerability", back_populates="tenant")
    credentials = relationship("ApiCredential", back_populates="tenant")
    tools = relationship("Tool", back_populates="tenant")
    domains = relationship("Domain", back_populates="tenant")


class ApiCredential(Base):
    __tablename__ = "api_credentials"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(SQLEnum(CredentialProvider), nullable=False, index=True)
    # For FOFA we need email + key; other providers may only need key
    api_email = Column(String(255), nullable=True)
    api_key = Column(String(2048), nullable=False)
    is_active = Column(Boolean, default=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    tenant = relationship("Tenant", back_populates="credentials")

    __table_args__ = (
        UniqueConstraint("tenant_id", "provider", name="uix_tenant_provider"),
    )


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    role = Column(SQLEnum(UserRole), default=UserRole.USER)
    refresh_token = Column(String(255), nullable=True, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    # Foreign key to Tenant (1:1)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), unique=True, nullable=False)
    tenant = relationship("Tenant", back_populates="user")


class ToolDefinition(Base):
    __tablename__ = "tool_definitions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # e.g., "nmap", "nuclei"
    description = Column(Text, nullable=True)
    version = Column(String(50), nullable=False)
    enabled = Column(Boolean, default=True)
    default_queue = Column(String(100), nullable=False)  # e.g., "scan.nmap"
    supported_actions = Column(JSON, default=list)  # List of supported actions
    config_schema = Column(JSON, default=dict)  # JSON Schema for tool configuration
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_tool_name_version", "name", "version", unique=True),
    )


class WorkerNode(Base):
    __tablename__ = "worker_nodes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    hostname = Column(String(255), nullable=False)
    ip_address = Column(String(50), nullable=False)
    queues = Column(JSON, default=list)  # List of queues this worker listens to
    tags = Column(JSON, default=list)    # e.g., ["high_mem", "gpu"]
    last_heartbeat = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING, index=True)
    progress = Column(Integer, default=0)  # 0-100
    # 關聯掃描方案（可選）
    scan_plan_id = Column(Integer, ForeignKey("scan_plans.id"), nullable=True, index=True)
    input_data = Column(JSON, default=dict)  # Input parameters for the task
    output_data = Column(JSON, default=dict)  # Results or output from the task
    error = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign key to Tenant
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    tenant = relationship("Tenant", back_populates="tasks")
    
    # Relationships
    assets = relationship("Asset", back_populates="task")
    vulnerabilities = relationship("Vulnerability", back_populates="task")
    domains = relationship("Domain", back_populates="task")


class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)

    # 聚合表必有字段
    url = Column(String(2048), nullable=True, index=True)
    domain = Column(String(255), nullable=True, index=True)
    ip_address = Column(String(50), nullable=True, index=True)
    port = Column(Integer, nullable=True, index=True)
    product = Column(String(255), nullable=True)

    # 可選：協議/類型等（保留兼容）
    type = Column(SQLEnum(AssetType), nullable=False, index=True, default=AssetType.ENDPOINT)
    value = Column(String(1024), nullable=False, index=True, default="")
    protocol = Column(String(32), nullable=True)

    # 來源列表（fofa/hunter/subfinder...）
    sources = Column(JSON, default=list)

    # 新增：详细记录每个来源的贡献
    discovered_by = Column(JSON, default=dict)  # {"fofa": {"first_seen": "...", "count": N}, ...}
    source_urls = Column(JSON, default=dict)  # {"fofa": [...], "hunter": [...], "subfinder": [...]}

    # 新增：记录每个来源的首次发现时间
    fofa_discovered_at = Column(DateTime, nullable=True)
    hunter_discovered_at = Column(DateTime, nullable=True)
    subfinder_discovered_at = Column(DateTime, nullable=True)

    data = Column(JSON, default=dict)

    # CDN相关信息
    is_cdn = Column(Boolean, default=False, index=True)
    cdn_provider = Column(String(50), nullable=True, index=True)
    original_domain = Column(String(255), nullable=True, index=True)

    tags = Column(JSON, default=list)
    discovered_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True, index=True)

    tenant = relationship("Tenant", back_populates="assets")
    task = relationship("Task", back_populates="assets")
    vulnerabilities = relationship("Vulnerability", back_populates="asset")

    __table_args__ = (
        UniqueConstraint("tenant_id", "domain", "ip_address", "port", name="uix_tenant_agg_asset"),
    )


class FofaAsset(Base):
    __tablename__ = "fofa_assets"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(SQLEnum(AssetType), nullable=False, index=True)
    value = Column(String(1024), nullable=False, index=True)

    url = Column(String(2048), nullable=True)
    domain = Column(String(255), nullable=True, index=True)
    ip_address = Column(String(50), nullable=True, index=True)
    port = Column(Integer, nullable=True, index=True)
    protocol = Column(String(32), nullable=True)
    product = Column(String(255), nullable=True)

    data = Column(JSON, default=dict)
    tags = Column(JSON, default=list)
    discovered_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True, index=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "task_id", "type", "value", name="uix_tenant_task_fofa_asset"),
    )


class HunterAsset(Base):
    __tablename__ = "hunter_assets"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(SQLEnum(AssetType), nullable=False, index=True)
    value = Column(String(1024), nullable=False, index=True)

    url = Column(String(2048), nullable=True)
    domain = Column(String(255), nullable=True, index=True)
    ip_address = Column(String(50), nullable=True, index=True)
    port = Column(Integer, nullable=True, index=True)
    protocol = Column(String(32), nullable=True)
    product = Column(String(255), nullable=True)

    data = Column(JSON, default=dict)
    tags = Column(JSON, default=list)
    discovered_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True, index=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "task_id", "type", "value", name="uix_tenant_task_hunter_asset"),
    )


class SubfinderAsset(Base):
    """
    Subfinder 来源资产表
    保存 subfinder 工具发现的完整数据（包括 URLs 和 domains）
    """
    __tablename__ = "subfinder_assets"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(SQLEnum(AssetType), nullable=False, index=True)
    value = Column(String(1024), nullable=False, index=True)

    url = Column(String(2048), nullable=True, index=True)
    domain = Column(String(255), nullable=True, index=True)

    # 关联的 root_domain（触发 subfinder 的种子域名）
    root_domain = Column(String(255), nullable=True, index=True)

    # 解析出的完整 URL 列表（如果有多个）
    discovered_urls = Column(JSON, default=list)

    data = Column(JSON, default=dict)
    tags = Column(JSON, default=list)
    discovered_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True, index=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "task_id", "type", "value", name="uix_tenant_task_subfinder_asset"),
    )


class ScanPlan(Base):
    """
    掃描方案：描述一組工具及其默認配置，任務可以關聯到某個方案。
    """

    __tablename__ = "scan_plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    # 任務級別的默認選項（如超時、並發等）
    options = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系：扫描方案中的工具配置
    tools = relationship("ScanPlanTool", back_populates="scan_plan", cascade="all, delete-orphan")


class ScanPlanTool(Base):
    """
    掃描方案與工具的關聯，以及每個工具在方案中的具體配置。
    """

    __tablename__ = "scan_plan_tools"

    id = Column(Integer, primary_key=True, index=True)
    scan_plan_id = Column(Integer, ForeignKey("scan_plans.id"), nullable=False, index=True)
    tool_name = Column(String(100), nullable=False)  # 對應 ToolDefinition.name
    enabled = Column(Boolean, default=True)
    # 工具級別的配置，例如命令模板、端口列表等
    config = Column(JSON, default=dict)

    __table_args__ = (
        UniqueConstraint("scan_plan_id", "tool_name", name="uix_scan_plan_tool"),
    )
    
    # 关系：所属的扫描方案
    scan_plan = relationship("ScanPlan", back_populates="tools")


class TaskLog(Base):
    """
    任務執行過程中的階段性日誌，用於前端展示流水線各階段狀態。
    """

    __tablename__ = "task_logs"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, index=True)
    phase = Column(String(50), nullable=False, index=True)  # 例如: "fofa", "subfinder", "port_scan", "fingerprint", "vuln_scan"
    level = Column(String(20), default="info")  # info / warning / error
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class FingerprintRule(Base):
    """
    指紋規則：用於對 URL / 端口的內容進行匹配，產生指紋結果。
    """

    __tablename__ = "fingerprint_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, default=True, index=True)
    # 匹配目標：url / body / title / header 等
    target = Column(String(50), nullable=False, default="url")
    # 具體匹配模式，例如正則表達式
    pattern = Column(String(2048), nullable=False)
    # 其他元數據，如嚴重程度、標籤等
    # 使用 meta 作為屬性名，實際列名仍為 metadata，避免 Declarative 保留字衝突
    meta = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class VulnerabilitySeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Vulnerability(Base):
    __tablename__ = "vulnerabilities"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(SQLEnum(VulnerabilitySeverity), nullable=False, index=True)
    cve_id = Column(String(50), nullable=True, index=True)
    cwe_id = Column(String(20), nullable=True)
    cvss_score = Column(Integer, nullable=True)
    references = Column(JSON, default=list)  # List of reference URLs
    raw_data = Column(JSON, default=dict)    # Raw data from the scanner
    status = Column(String(50), default="open")  # e.g., "open", "in_progress", "resolved", "false_positive"
    discovered_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign keys
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=True, index=True)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="vulnerabilities")
    task = relationship("Task", back_populates="vulnerabilities")
    asset = relationship("Asset", back_populates="vulnerabilities")


class Tool(Base):
    """工具插件表 - 用于动态管理扫描工具"""
    __tablename__ = "tools"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    display_name = Column(String(200), nullable=True)  # 显示名称
    description = Column(Text, nullable=True)
    version = Column(String(50), nullable=True)
    author = Column(String(100), nullable=True)
    
    # 工具类型：script（脚本）、binary（二进制）、docker（容器）
    tool_type = Column(String(50), default="script")
    
    # 文件路径（相对于工具目录）
    file_path = Column(String(500), nullable=True)
    
    # 执行命令模板，支持变量替换
    # 例如: "python3 {file_path} -t {target} -o {output}"
    command_template = Column(Text, nullable=True)
    
    # 工具配置（JSON格式）
    # 包含：支持的参数、默认值、输出格式等
    config = Column(JSON, default=dict)
    
    # 是否启用
    enabled = Column(Boolean, default=True)
    
    # 是否为内置工具
    is_builtin = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign keys
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="tools")
    
    __table_args__ = (
        UniqueConstraint('name', 'tenant_id', name='uq_tool_name_tenant'),
    )


# ============================================
# Domain-Driven Aggregation Models
# ============================================

class Domain(Base):
    __tablename__ = "domains"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, index=True)

    name = Column(String(255), nullable=False)  # e.g., api.example.com
    root_domain = Column(String(255), nullable=True)  # e.g., example.com

    discovered_by = Column(String(50), default="subfinder")
    discovered_at = Column(DateTime, default=datetime.utcnow)

    scan_status = Column(String(20), default="pending")  # pending, scanning, completed, failed

    # Statistics (updated after aggregation)
    ip_count = Column(Integer, default=0)
    endpoint_count = Column(Integer, default=0)
    source_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="domains")
    task = relationship("Task", back_populates="domains")
    ips = relationship("DomainIP", back_populates="domain", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("tenant_id", "task_id", "name"),
    )


class DomainIP(Base):
    __tablename__ = "domain_ips"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, index=True)
    domain_id = Column(Integer, ForeignKey("domains.id"), nullable=False, index=True)

    ip_address = Column(String(45), nullable=False)  # IPv6 compatible
    port = Column(Integer, nullable=False)
    protocol = Column(String(20), nullable=True)

    sources = Column(JSON, default=list)  # ['fofa', 'hunter']
    discovered_by = Column(JSON, default=dict)  # {fofa: {first_seen, count}, ...}

    # Technical fingerprint
    product = Column(String(255), nullable=True)
    product_version = Column(String(100), nullable=True)
    os = Column(String(100), nullable=True)
    banner = Column(Text, nullable=True)

    raw_data = Column(JSON, default=dict)  # Raw response from sources

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant")
    task = relationship("Task")
    domain = relationship("Domain", back_populates="ips")
    endpoints = relationship("DomainEndpoint", back_populates="domain_ip", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("tenant_id", "domain_id", "ip_address", "port"),
    )


class DomainEndpoint(Base):
    __tablename__ = "domain_endpoints"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    domain_ip_id = Column(Integer, ForeignKey("domain_ips.id"), nullable=False, index=True)

    path = Column(String(2048), nullable=False)
    method = Column(String(10), default="GET")

    status_code = Column(Integer, nullable=True)
    content_type = Column(String(255), nullable=True)
    content_length = Column(Integer, nullable=True)

    title = Column(String(512), nullable=True)
    technologies = Column(JSON, default=list)

    discovered_by = Column(String(50), nullable=True)
    discovered_at = Column(DateTime, default=datetime.utcnow)

    response_body_hash = Column(String(64), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant")
    domain_ip = relationship("DomainIP", back_populates="endpoints")
