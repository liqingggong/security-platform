# 领域驱动资产聚合系统设计文档

> **日期**: 2026-03-08
> **方案**: A (领域驱动聚合)
> **状态**: 设计完成，待实施

---

## 1. 背景与问题

### 1.1 现有问题

当前数据聚合逻辑存在以下设计缺陷：

1. **聚合Key冲突**: 以 `(domain, ip, port)` 或 `(url, ip, port)` 作为匹配Key，导致同一域名在不同任务中的资产被错误处理
2. **Sources传播不完整**: 第二轮查询结果未能正确继承 Subfinder 来源标记
3. **任务级隔离不清**: 资产表全局聚合，但展示时按 `task_id` 过滤，逻辑不一致
4. **数据血缘丢失**: 无法清晰追溯"哪个工具发现了什么"

### 1.2 设计目标

- **以域名为中心**: Subfinder 发现的域名作为根，FOFA/Hunter 发现的端点作为叶子
- **保留原始数据**: 不丢失任何来源的原始发现结果
- **查询时聚合**: 聚合逻辑发生在查询时，而非存储时
- **任务级隔离**: 每个任务的数据独立存储，支持跨任务对比

---

## 2. 数据库架构

### 2.1 核心表结构

```sql
-- ============================================
-- 表1: domains (域名)
-- 作用: Subfinder 发现的结果，作为聚合的锚点
-- ============================================
CREATE TABLE domains (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL,
    task_id INTEGER NOT NULL,

    name VARCHAR(255) NOT NULL,          -- 域名，如: api.example.com
    root_domain VARCHAR(255),            -- 根域名，如: example.com

    discovered_by VARCHAR(50) DEFAULT 'subfinder',
    discovered_at TIMESTAMP DEFAULT NOW(),

    -- 任务执行状态
    scan_status VARCHAR(20) DEFAULT 'pending',  -- pending, scanning, completed, failed

    -- 统计信息（聚合后更新）
    ip_count INTEGER DEFAULT 0,
    endpoint_count INTEGER DEFAULT 0,
    source_count INTEGER DEFAULT 0,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(tenant_id, task_id, name)
);

-- ============================================
-- 表2: domain_ips (域名对应的IP)
-- 作用: FOFA/Hunter 发现的 IP+Port 信息
-- ============================================
CREATE TABLE domain_ips (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL,
    task_id INTEGER NOT NULL,
    domain_id INTEGER NOT NULL REFERENCES domains(id) ON DELETE CASCADE,

    ip_address INET NOT NULL,
    port INTEGER NOT NULL,
    protocol VARCHAR(20),

    -- 来源信息（数组，支持多来源）
    sources VARCHAR(50)[],
    discovered_by JSONB,                 -- {fofa: {first_seen, count}, hunter: {...}}

    -- 技术指纹
    product VARCHAR(255),
    product_version VARCHAR(100),
    os VARCHAR(100),
    banner TEXT,

    -- 原始数据保留
    raw_data JSONB,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(tenant_id, domain_id, ip_address, port)
);

-- ============================================
-- 表3: domain_endpoints (端点)
-- 作用: Httpx 等工具进一步探测的端点信息
-- ============================================
CREATE TABLE domain_endpoints (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL,
    domain_ip_id INTEGER NOT NULL REFERENCES domain_ips(id) ON DELETE CASCADE,

    path VARCHAR(2048) NOT NULL,
    method VARCHAR(10) DEFAULT 'GET',

    status_code INTEGER,
    content_type VARCHAR(255),
    content_length INTEGER,

    title VARCHAR(512),
    technologies VARCHAR(100)[],

    discovered_by VARCHAR(50),
    discovered_at TIMESTAMP DEFAULT NOW(),

    response_body_hash VARCHAR(64),

    created_at TIMESTAMP DEFAULT NOW()
);
```

### 2.2 索引设计

```sql
-- domains 表索引
CREATE INDEX idx_domains_task ON domains(tenant_id, task_id);
CREATE INDEX idx_domains_root ON domains(tenant_id, root_domain);
CREATE INDEX idx_domains_status ON domains(tenant_id, scan_status);
CREATE INDEX idx_domains_discovered ON domains(discovered_at);

-- domain_ips 表索引
CREATE INDEX idx_domain_ips_domain ON domain_ips(domain_id);
CREATE INDEX idx_domain_ips_ip ON domain_ips(ip_address);
CREATE INDEX idx_domain_ips_sources ON domain_ips USING GIN(sources);

-- domain_endpoints 表索引
CREATE INDEX idx_endpoints_ip ON domain_endpoints(domain_ip_id);
CREATE INDEX idx_endpoints_path ON domain_endpoints(path);
```

---

## 3. 数据流设计

### 3.1 任务执行流程

```
┌─────────────────────────────────────────────────────────────────┐
│                         任务生命周期                              │
└─────────────────────────────────────────────────────────────────┘

1. 创建任务
   └── 参数: root_domains[], enable[]

2. Subfinder 扫描 (第一轮)
   ├── 扫描根域名
   └── 创建 Domain 记录 (scan_status='pending')
       └── discovered_by='subfinder'

3. 第二轮查询 (并行)
   ├── FOFA 查询: domain="xxx.example.com"
   │   └── 创建/更新 DomainIP 记录
   │       └── sources=['fofa']
   │
   └── Hunter 查询: domain="xxx.example.com"
       └── 创建/更新 DomainIP 记录
           └── sources=['hunter']

4. 聚合统计
   └── 更新 Domain 表统计字段
       ├── ip_count = COUNT(DISTINCT ip+port)
       ├── endpoint_count = 0 (待httpx扫描后更新)
       └── scan_status = 'completed'

5. 端点扫描 (可选)
   └── Httpx 扫描活跃 IP+Port
       └── 创建 DomainEndpoint 记录
```

### 3.2 关键设计决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 聚合时机 | 查询时聚合 | 保留原始数据，聚合逻辑可调整 |
| 同一IP多来源 | 保留多份记录 | 每个来源的数据可能不同（banner等） |
| 跨任务域名 | 独立存储 | 支持任务间对比，定期归档 |
| 层级关系 | Domain → IP → Endpoint | 自然反映发现流程 |

---

## 4. 聚合逻辑设计

### 4.1 查询时聚合服务

```python
class DomainAggregationService:
    """
    域名资产聚合服务
    将分散的 DomainIP 记录聚合为统一的展示视图
    """

    def get_domain_with_assets(self, domain_id: int) -> DomainView:
        """获取域名及其聚合后的资产视图"""
        domain = db.query(Domain).get(domain_id)

        # 获取该域名下所有IP
        ips = db.query(DomainIP).filter(
            DomainIP.domain_id == domain_id
        ).all()

        # 按 IP+Port 分组聚合
        ip_groups = {}
        for ip in ips:
            key = (ip.ip_address, ip.port)
            if key not in ip_groups:
                ip_groups[key] = {
                    "ip": str(ip.ip_address),
                    "port": ip.port,
                    "protocol": ip.protocol,
                    "sources": set(),
                    "products": {},
                    "banners": {},
                    "first_seen": ip.created_at,
                }

            # 合并来源
            ip_groups[key]["sources"].update(ip.sources or [])

            # 合并产品信息
            for source in (ip.sources or []):
                if ip.product:
                    ip_groups[key]["products"][source] = ip.product
                if ip.banner:
                    ip_groups[key]["banners"][source] = ip.banner

        return DomainView(
            domain=domain,
            ips=[{
                **data,
                "sources": list(data["sources"])
            } for data in ip_groups.values()],
            total_ips=len(ip_groups),
            total_sources=len(set().union(*[
                ip.sources for ip in ips if ip.sources
            ]))
        )

    def get_unique_domains(self, tenant_id: int) -> List[DomainView]:
        """
        获取租户下唯一的域名列表（跨任务去重）
        取每个域名最新任务的数据
        """
        # 子查询：获取每个域名最新的记录
        subquery = db.query(
            Domain.name,
            func.max(Domain.created_at).label('latest')
        ).filter(
            Domain.tenant_id == tenant_id
        ).group_by(
            Domain.name
        ).subquery()

        # 获取最新记录
        latest_domains = db.query(Domain).join(
            subquery,
            and_(
                Domain.name == subquery.c.name,
                Domain.created_at == subquery.c.latest
            )
        ).all()

        return [
            self.get_domain_with_assets(d.id)
            for d in latest_domains
        ]
```

### 4.2 聚合规则

| 字段 | 聚合规则 | 示例 |
|------|----------|------|
| `sources` | 取所有来源的并集 | `['fofa', 'hunter']` |
| `product` | 保留多来源的产品信息 | `{fofa: 'nginx', hunter: 'nginx/1.18'}` |
| `banner` | 保留多来源的banner | `{fofa: '...', hunter: '...'}` |
| `first_seen` | 取最早发现时间 | - |
| `endpoint_count` | 该IP下所有端点数量 | - |

---

## 5. API 设计

### 5.1 新的 Domain 管理 API

```typescript
// ============================================
// 域名列表
// GET /api/v1/domains
// ============================================
interface ListDomainsRequest {
  task_id?: number;           // 按任务筛选
  root_domain?: string;       // 按根域名筛选
  scan_status?: string;       // 按状态筛选
  page?: number;
  page_size?: number;
}

interface ListDomainsResponse {
  items: {
    id: number;
    name: string;              // api.example.com
    root_domain: string;       // example.com
    scan_status: 'pending' | 'scanning' | 'completed' | 'failed';
    ip_count: number;
    endpoint_count: number;
    sources: string[];         // ['fofa', 'hunter']
    discovered_at: string;
    created_at: string;
  }[];
  total: number;
}

// ============================================
// 域名详情（包含聚合后的IP）
// GET /api/v1/domains/{id}
// ============================================
interface GetDomainResponse {
  id: number;
  name: string;
  root_domain: string;
  scan_status: string;

  // 聚合后的IP列表
  ips: {
    ip: string;
    port: number;
    protocol: string;
    sources: string[];                    // ['fofa', 'hunter']
    products: Record<string, string>;     // {fofa: 'nginx', hunter: 'nginx/1.18'}
    banners?: Record<string, string>;     // 各来源的banner
    endpoints_count: number;
    first_seen: string;
  }[];

  total_ips: number;
  total_sources: number;
}

// ============================================
// IP 下的端点列表
// GET /api/v1/domain-ips/{id}/endpoints
// ============================================
interface ListEndpointsResponse {
  items: {
    id: number;
    path: string;
    method: string;
    status_code: number;
    title: string;
    technologies: string[];
    discovered_by: string;
    discovered_at: string;
  }[];
  total: number;
}
```

### 5.2 向后兼容（可选）

```typescript
// GET /api/v1/assets（展平视图，兼容旧API）
interface AssetResponse {
  id: number;
  type: 'domain' | 'ip' | 'endpoint';
  value: string;

  domain?: string;
  ip_address?: string;
  port?: number;
  path?: string;

  sources: string[];
  discovered_by: Record<string, any>;
}
```

---

## 6. 任务级隔离与归档

### 6.1 数据隔离策略

```sql
-- 每个任务独立存储，通过 task_id 区分
-- 优点：支持任务间对比，可追溯历史
-- 缺点：数据可能膨胀

-- 查询时按任务筛选
SELECT * FROM domains WHERE task_id = ?;
SELECT * FROM domain_ips WHERE task_id = ?;
```

### 6.2 归档策略

```sql
-- 归档表
CREATE TABLE domains_archive (LIKE domains INCLUDING ALL);
CREATE TABLE domain_ips_archive (LIKE domain_ips INCLUDING ALL);

-- 归档策略：任务完成7天后
-- 1. 将数据插入归档表
-- 2. 从主表删除
-- 3. 需要时可从归档表恢复
```

---

## 7. 迁移计划

### 7.1 阶段1：新表创建（零停机）

```python
# 1. 创建新表（不删除旧表）
# 2. 双写：新数据同时写入新旧表
# 3. 后台任务：迁移历史数据
```

### 7.2 阶段2：切换读取

```python
# 1. 读取逻辑切换为新表
# 2. 验证数据一致性
# 3. 停止写入旧表
```

### 7.3 阶段3：清理

```python
# 1. 删除旧表（或保留作归档）
# 2. 移除双写逻辑
```

---

## 8. 实现检查清单

- [ ] 数据库迁移脚本（创建新表）
- [ ] Domain / DomainIP / DomainEndpoint 模型定义
- [ ] 新的聚合服务（DomainAggregationService）
- [ ] 修改任务执行流程（Subfinder → Domain, FOFA/Hunter → DomainIP）
- [ ] 新的 API 端点（/domains, /domain-ips, /endpoints）
- [ ] 前端页面适配（展示 Domain → IP → Endpoint 层级）
- [ ] 数据迁移脚本（历史数据迁移）
- [ ] 归档任务（定时清理旧数据）
- [ ] 单元测试和集成测试

---

## 9. 风险评估

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| 数据迁移失败 | 中 | 高 | 保留旧表，可回滚 |
| 性能下降（查询时聚合） | 低 | 中 | 添加缓存层，优化索引 |
| 存储空间增加 | 高 | 低 | 定期归档旧数据 |
| 前端适配工作量大 | 中 | 中 | 提供兼容API，渐进式迁移 |

---

## 10. 决策记录

| 日期 | 决策 | 理由 |
|------|------|------|
| 2026-03-08 | 采用方案A（领域驱动） | 符合业务场景，层级清晰 |
| 2026-03-08 | 查询时聚合 | 保留原始数据，逻辑灵活 |
| 2026-03-08 | 任务级隔离 | 支持任务对比，可追溯 |

---

**设计完成，等待实施**
