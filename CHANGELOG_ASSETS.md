# 修改说明

## 后端修改

### 1. 添加发现时间字段到来源资产表

#### app/db/models.py
- `FofaAsset` 表：添加 `discovered_at` 字段，记录 FOFA 发现该资产的时间
- `HunterAsset` 表：添加 `discovered_at` 字段，记录 Hunter 发现该资产的时间

#### app/workers/tasks.py
- `run_fofa_pull`：添加 `discovered_at` 字段到返回的 SearchRecord
- `run_hunter_pull`：添加 `discovered_at` 字段到返回的 SearchRecord
- `_upsert_aggregated_asset`：保存发现时间到 `discovered_by[source]`

### 2. 添加数据库迁移

#### alembic/versions/*_add_discovery_time_to_source_asset.py
- 为 `fofa_assets` 表添加 `discovered_at` 字段
- 为 `hunter_assets` 表添加 `discovered_at` 字段
- 为 `assets` 表添加 `fofa_discovered_at`、hunter_discovered_at`、subfinder_discovered_at` 字段

---

## 前端修改

### frontend/src/pages/Assets.tsx

### 1. 支持多种导出格式

#### 导入 xlsx 库
```bash
npm install xlsx
```

#### 修改代码
- 添加 xlsx 导出选项
- 实现 `handleExportXlsx` 函数
- 更新导出按钮菜单

#### 列配置
- `columns` 数组：为列添加 `resizable: true` 属性
- 移除固定 `width` 属性
- 添加表格列配置到 `scroll` 属性

### 2. 显示发现时间

#### 修改列定义
- "來源" 列：显示每个来源的发现时间
- `发现时间` 列：显示 FOFA/Hunter/Subfinder 的首次发现时间

#### 3. 优化空协议行显示

#### 修改 `protocol` 列渲染
- 当 `protocol` 为空时，显示 URL 中的协议信息

### 4. 创建 FOFA/Hunter 配置页面

#### 前端/src/pages/AssetSettings.tsx（新建）
```bash
touch frontend/src/pages/AssetSettings.tsx
```

#### 主要功能
- FOFA 配置：email、api_key、limit、is_web、page
- Hunter 配置：api_key、limit、page
- last_update_time 设置
- 搜索结果限制设置

---

## 执行步骤

### 1. 应用数据库迁移
```bash
source .venv/bin/activate && alembic upgrade head
```

### 2. 重启后端服务
```bash
source .venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. 重启前端服务
```bash
cd frontend
npm install xlsx
npm run dev
```

---

## 注意事项

### 后端
- `discovered_at` 字段记录的是 API 返回的时间，不是任务执行时间
- `discovered_by` 结构：`{"fofa": {"first_seen": "2024-01-01T12:00:00:00Z", "count": 1}, ...}`
- 优先显示 FOFA/Hunter 时间，然后显示任务执行时间

### 前端
- xlsx 库用于大数量数据导出
- 表格列宽调整需要在表格设置中配置
- 发现时间显示需要格式化为易读格式

### 预期功能
- FOFA/Hunter 配置页面需要进一步设计实现
