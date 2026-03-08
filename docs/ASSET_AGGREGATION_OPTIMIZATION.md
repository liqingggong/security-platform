# 资产发现数据聚合优化方案

## 问题分析

### 当前问题
1. **FOFA/Hunter 聚合冲突**：同一个资产（相同 domain+ip+port）从多个来源时，只保留第一个
2. **Subfinder 数据丢失**：只保存 domains，丢失 urls 列表
3. **二轮查询未聚合**：第二轮 FOFA/Hunter 结果只写入来源表，未聚合到 Asset

### 优化目标
1. 保留所有来源的数据，智能合并（而非简单覆盖）
2. 保存 Subfinder 发现的完整 URL 列表
3. 确保二轮查询结果正确聚合到 Asset 表

---

## 方案设计

### 1. 数据模型优化

#### 新增 SubfinderAsset 来源表
```python
class SubfinderAsset(Base):
    __tablename__ = "subfinder_assets"
    
    id = Column(Integer, primary_key=True, index=True)
    type = Column(SQLEnum(AssetType), nullable=False, index=True)
    value = Column(String(1024), nullable=False, index=True)
    
    # Subfinder 特有字段
    url = Column(String(2048), nullable=True, index=True)
    domain = Column(String(255), nullable=True, index=True)
    
    # 关联的 root_domain（触发 subfinder 的种子域名）
    root_domain = Column(String(255), nullable=True, index=True)
    
    data = Column(JSON, default=dict)
    tags = Column(JSON, default=list)
    discovered_at = Column(DateTime, default=datetime.utcnow)
    
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True, index=True)
    
    __table_args__ = (
        UniqueConstraint("tenant_id", "task_id", "type", "value", name="uix_tenant_task_subfinder_asset"),
    )
```

#### Asset 表新增字段
```python
# 现有 sources 字段改为详细记录
# sources: {"fofa": {"count": 5, "last_seen": "2024-01-01"}, "hunter": {...}, "subfinder": {...}}

# 新增字段
discovered_by = Column(JSON, default=dict)  # 记录每个来源首次发现时间
source_urls = Column(JSON, default=dict)   # 记录每个来源发现的具体 URL
```

---

### 2. 聚合逻辑优化

#### 核心原则
1. **多来源合并**：同一资产的多个来源数据智能合并，而非覆盖
2. **来源追踪**：完整记录每个来源的贡献
3. **增量更新**：只更新变化的字段

#### 合并策略

**1. URL 合并（去重）**
```python
# 合并来自多个来源的 URL
def merge_urls(existing_urls, new_urls):
    all_urls = set(existing_urls or []) | set(new_urls or [])
    return list(all_urls)
```

**2. IP 地址合并**
- 优先使用有端口的 IP
- 记录所有发现的 IP 地址
- 示例：`{"fofa": ["1.1.1.1"], "hunter": ["2.2.2.2"]}`

**3. 产品信息合并**
- 记录所有来源的 product
- 示例：`{"fofa": "nginx/1.18", "hunter": "Apache/2.4"}`

---

### 3. 数据流程优化

#### 第一轮流程
```
1. FOFA/Hunter 查询
   ↓
2. 写入 FofaAsset/HunterAsset
   ↓
3. 聚合到 Asset 表（智能合并）
   ├─ 保留所有来源的 URL
   ├─ 合并 IP 地址列表
   ├─ 记录产品信息
   └─ 更新 discovered_by 和 source_urls
```

#### Subfinder 流程
```
1. Subfinder 发现 domains 和 urls
   ↓
2. 写入 SubfinderAsset（保存完整的 urls 列表）
   ├─ 记录每个 URL 对应的 domain
   └─ 记录 root_domain（种子域名）
   ↓
3. 聚合到 Asset 表
   ├─ Domain 级别聚合：domain 字段匹配
   ├─ URL 级别聚合：url 字段匹配（如有）
   └─ 记录 subfinder 发现的所有 URL
```

#### 第二轮流程
```
1. 对 subfinder 新发现的新域名
   ↓
2. 逐个查询 FOFA/Hunter
   ↓
3. 写入 FofaAsset/HunterAsset
   ↓
4. **关键修复**：触发第二轮聚合到 Asset 表
   ↓
5. 更新相关资产记录
   └─ 合并二轮查询的数据
```

---

### 4. 数据结构示例

#### Asset 记录示例
```json
{
  "id": 1,
  "domain": "example.com",
  "url": "https://example.com",
  "ip_address": "1.1.1.1",
  "port": 443,
  "protocol": "https",
  "product": "nginx",
  "sources": ["fofa", "hunter", "subfinder"],
  "discovered_by": {
    "fofa": {
      "first_seen": "2024-01-01T00:00:00Z",
      "count": 5
    },
    "hunter": {
      "first_seen": "2024-01-01T00:00:00Z",
      "count": 3
    },
    "subfinder": {
      "first_seen": "2024-01-01T00:01:00Z",
      "count": 1,
      "root_domain": "example.org"
    }
  },
  "source_urls": {
    "fofa": ["https://example.com:443", "http://example.com:80"],
    "hunter": ["https://example.com"],
    "subfinder": [
      "https://example.com",
      "https://api.example.com"
    ]
  },
  "data": {
    "fofa_data": {...},
    "hunter_data": {...},
    "subfinder_data": {...}
  }
}
```

---

### 5. 实现步骤

#### Phase 1: 数据库模型更新
1. 创建 SubfinderAsset 表
2. Asset 表新增 discovered_by 和 source_urls 字段
3. 生成并应用数据库迁移

#### Phase 2: 任务逻辑更新
1. 修改 run_subfinder - 保存完整数据到 SubfinderAsset
2. 修改 check_and_aggregate - 实现智能合并逻辑
3. 添加第二轮聚合步骤

#### Phase 3: API 更新
1. 更新 Asset 查询 API - 支持按 source 过滤
2. 新增聚合统计 API - 显示各来源贡献

#### Phase 4: 前端更新
1. Asset 详情页显示多来源信息
2. 可视化显示资产来源分布
3. 支持按来源筛选资产
