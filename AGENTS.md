# Security Platform - AGENTS.md

为在此代码库工作的编码代理提供的构建和测试命令。

---

## 后端命令

### Python 3.9.18 环境（使用 venv）

### 运行后端服务器
```bash
# 首先激活 venv
source .venv/bin/activate

# 使用自动重载运行开发服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 访问 API 文档：http://127.0.0.1:8000/docs
```

### 数据库迁移
```bash
# 首先激活 venv
source .venv/bin/activate

# 创建新迁移
alembic revision --autogenerate -m "描述"

# 应用迁移
alembic upgrade head

# 回滚一步
alembic downgrade -1
```

### 测试
```bash
# 运行手动 API 测试脚本
python test_api.py

# 当前没有自动化测试 - test_api.py 是唯一的测试文件
```

### 安装依赖
```bash
# 创建/激活 venv
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 运行 Celery Worker
```bash
# 首先激活 venv
source .venv/bin/activate

# 运行 Celery worker（用于后台任务处理）
celery -A app.workers.celery_app worker --loglevel=info
```

---

## 前端命令

### 开发
```bash
cd frontend

# 安装依赖
npm install

# 运行开发服务器（Vite 代理到后端 http://127.0.0.1:8000）
npm run dev
# 运行在 http://localhost:3000

# 生产构建
npm run build
# 这会运行：tsc && vite build（TypeScript 检查 + Vite 构建）

# 预览生产构建
npm run preview
```

---

## 代码风格指南

### 后端 (Python/FastAPI)

#### 导入语句
- 按标准库、第三方库、本地模块分组，各组之间用空行分隔
- 新文件中使用 `from __future__ import annotations` 以保持向前兼容
- 优先使用绝对导入而非相对导入
- 顺序：标准库 → 第三方库 → 本地应用模块

```python
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.db.session import get_db
from app.schemas.user import UserCreate
```

#### 类型和注解
- 使用 `typing.Annotated` 进行依赖注入
- 使用 Pydantic v2 语法，Config 中设置 `from_attributes = True`
- 所有函数（包括端点）都要有返回类型
- 使用 `Optional[T]` 而非 `T | None` 以保持一致性
- 使用 `List[T]` 而非 `list[T]` 以保持兼容性

```python
def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    token: Annotated[str, Depends(oauth2_scheme)]
) -> User:
    ...

class UserInDB(UserBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True
```

#### 命名规范
- 类名：PascalCase（例如：`UserRole`, `AssetProvider`）
- 函数/变量：snake_case（例如：`get_current_user`, `tenant_id`）
- 常量：UPPER_SNAKE_CASE（例如：`ALGORITHM`, `SECRET_KEY`）
- 私有方法：前导下划线（例如：`_generate_signature`）
- 数据库表：小写加下划线（例如：`api_credentials`）
- API 端点：URL 中用 kebab-case，参数中用 snake_case

```python
class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"

def hash_password(password: str) -> str:
    ...

API_KEY = "change_me"
```

#### 错误处理
- 使用 `HTTPException` 处理 API 错误，使用适当的状态码
- 使用繁体中文提供描述性错误信息
- 使用 `fastapi` 中的 `status` 定义状态码
- 适当记录错误（不要静默失败）
- 数据库操作前验证用户输入

```python
from fastapi import HTTPException, status

raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="該資源不存在"
)
```

#### FastAPI 模式
- 使用 `Depends()` 进行依赖注入（db 会话、认证）
- 使用 `Query()` 进行带验证的查询参数
- 使用 `OAuth2PasswordRequestForm` 处理登录端点
- 使用繁体中文添加文档字符串
- 返回 Pydantic 模型或字典作为响应

```python
@router.get("", response_model=AssetListResponse)
def list_assets(
    *,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """列出當前租戶的所有資產"""
    ...
```

#### 数据库 (SQLAlchemy)
- 使用声明式基类模型，在 `app/db/models.py` 中
- 定义关系时使用正确的 back_populates
- 使用 `SQLEnum` 作为枚举列
- 使用 `datetime.utcnow` 作为时间戳
- 使用 `__table_args__` 定义约束

```python
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True)
    tenant = relationship("Tenant", back_populates="user")

    __table_args__ = (
        UniqueConstraint("tenant_id", "provider", name="uix_tenant_provider"),
    )
```

#### 配置
- 使用 `pydantic-settings` 进行配置
- 环境变量使用大写
- 使用 `lru_cache` 实现设置单例
- 配置从 `config/.env` 加载

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./test.db"
    SECRET_KEY: str = "change_me"

settings = get_settings()
```

---

### 前端 (React + TypeScript)

#### 导入语句
- 分组导入：React → 第三方库 → 本地模块
- 工具函数使用命名导出
- Ant Design 组件：`import { Button, Table } from 'antd'`

```typescript
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button, Table, message } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import { tasksAPI } from '../utils/api'
```

#### 组件
- 使用函数式组件和 Hooks
- 使用 TypeScript 接口定义 props
- 使用 Ant Design 组件构建 UI
- 样式对象中使用内联样式
- 注释使用中文

```typescript
interface Props {
  id: number
  onUpdate: () => void
}

const Tasks = () => {
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  return (
    <div style={{ padding: 24 }}>
      <Button onClick={() => navigate('/tasks/new')}>创建</Button>
    </div>
  )
}
```

#### API 调用
- 使用 `utils/api.ts` 中的 axios 实例
- API 函数按资源分组
- 使用 try/catch 和 `message.error()` 处理错误
- 异步操作使用 `await`

```typescript
const loadTasks = async () => {
  setLoading(true)
  try {
    const data = await tasksAPI.list()
    setTasks(Array.isArray(data) ? data : [])
  } catch (error) {
    message.error('加载失败')
  } finally {
    setLoading(false)
  }
}
```

#### TypeScript
- 启用严格模式
- 使用接口定义对象类型
- 避免使用 `any` - 使用正确的类型
- 类型清晰时使用类型推断
- 仅在灵活配置对象中使用 `Record<string, any>`

```typescript
interface Task {
  id: number
  name: string
  status: 'pending' | 'running' | 'completed'
}

const tasks: Task[] = []
```

#### 命名规范
- 组件：PascalCase（例如：`TaskList`, `UserForm`）
- 函数/变量：camelCase（例如：`loadTasks`, `isLoading`）
- 常量：UPPER_SNAKE_CASE（例如：`API_BASE_URL`）
- 文件：组件用 PascalCase（例如：`Tasks.tsx`），工具用 camelCase（例如：`api.ts`）

---

## 架构说明

### 多租户
- 所有数据都限定在 `tenant_id` 范围内
- 在端点中使用 `get_current_tenant_id()` 依赖
- 自动按 tenant_id 过滤查询

### 后台任务
- 使用 Celery 处理异步任务
- Redis 作为代理/结果后端
- Worker 在 `app/workers/` 中
- 任务状态在数据库中跟踪

### 资产发现
- FOFA 和 Hunter API 提供程序在 `tools/` 中
- 新提供程序实现 `IAssetSearchProvider` 接口
- 工具存储在 `tools/builtin/` 或系统 PATH 中

### 前后端通信
- 通过 Vite 开发服务器进行 API 代理
- Bearer token 认证在 Authorization 头中
- API 基础 URL：`/api/v1`
- Axios 拦截器用于 token 注入和错误处理

---

## 环境配置

### 后端 (config/.env)
- `DEBUG` - 开发模式标志
- `SECRET_KEY` - JWT 签名密钥
- `POSTGRES_*` - 数据库连接
- `REDIS_*` - Celery 代理/后端
- `FOFA_EMAIL`, `FOFA_KEY` - FOFA API 凭证

### 前端 (vite.config.ts)
- 开发服务器端口：3000
- 代理 `/api` 到 `http://127.0.0.1:8000`
- 当前不需要 .env 文件

---

## 常见模式

### 创建新的 API 端点
1. 在 `app/schemas/` 中创建 Pydantic 模型
2. 在 `app/api/v1/endpoints/` 中添加端点
3. 在 `app/api/v1/api.py` 中注册路由
4. 更新前端 API 客户端 `frontend/src/utils/api.ts`
5. 创建/更新前端页面组件

### 数据库变更
1. 修改 `app/db/models.py` 中的模型
2. 运行 `alembic revision --autogenerate -m "描述"`
3. 检查生成的迁移脚本
4. 运行 `alembic upgrade head`

### 添加新工具提供程序
1. 在 `tools/` 中创建实现 `IAssetSearchProvider` 的提供程序类
2. 在模型的 `CredentialProvider` 中添加枚举
3. 使用迁移更新数据库架构
4. 更新前端以显示/管理凭证
