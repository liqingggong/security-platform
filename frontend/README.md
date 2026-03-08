# Security Platform Frontend

信息安全扫描平台前端界面

## 技术栈

- React 18
- TypeScript
- Ant Design 5
- Vite
- React Router 6
- Axios

## 安装依赖

```bash
npm install
# 或
yarn install
# 或
pnpm install
```

## 开发

```bash
npm run dev
```

前端将在 http://localhost:3000 启动

## 构建

```bash
npm run build
```

## 功能模块

- ✅ 用户认证（登录/注册）
- ✅ 仪表盘（统计概览）
- ✅ 任务管理（创建、查看、取消任务）
- ✅ 资产管理（查看、搜索资产）
- ✅ 漏洞管理（查看、搜索、更新漏洞状态）
- ✅ API 凭据管理（FOFA 等）

## 项目结构

```
frontend/
├── src/
│   ├── components/      # 公共组件
│   ├── pages/          # 页面组件
│   ├── utils/          # 工具函数
│   ├── App.tsx         # 主应用组件
│   └── main.tsx        # 入口文件
├── package.json
└── vite.config.ts
```

## API 配置

前端通过 Vite 代理连接到后端 API（http://127.0.0.1:8000）

如需修改 API 地址，请编辑 `vite.config.ts` 中的 proxy 配置。

