# Collaborative Editor

> 基于 Vue 3 + FastAPI + WebSocket + SQLite 的实时协同 Block 编辑器。

🔗 **在线 Demo**：[https://collaborative-editor-wpju.onrender.com](https://collaborative-editor-wpju.onrender.com)

📦 **GitHub**：[https://github.com/jiangbei0921/collaborative-editor](https://github.com/jiangbei0921/collaborative-editor)

---

## 快速体验

1. 浏览器 A 打开 [在线 Demo](https://collaborative-editor-wpju.onrender.com)，新建一个文档。
2. 复制分享链接。
3. 浏览器 B 打开相同链接。
4. 两个浏览器同时编辑，观察实时同步效果。

---

## 核心功能

### 编辑器

- Block 级编辑（paragraph / heading / bullet / quote / code）
- DOM / contenteditable 原生编辑体验
- 创建 Block
- 修改 Block
- 删除 Block

### 实时协同

- WebSocket 实时通信
- Operation 原子操作同步
- Version Checking 版本校验
- ACK 确认机制
- Idempotency 幂等去重
- Retry 超时重试
- Reconnect 断线重连
- Pending Operations 暂存与重发
- Conflict Recovery 冲突恢复
- Online Users / Presence 在线用户显示

### 文档管理

- 创建文档
- Document ID
- Document Title 编辑
- 标题实时同步
- 标题持久化
- 分享链接（复制 ID 或完整链接）

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3, TypeScript, Vite, contenteditable |
| 后端 | FastAPI, Python 3.12 |
| 通信 | WebSocket（原生，前端自动 wss://） |
| 存储 | SQLite（aiosqlite 异步驱动） |
| 测试 | pytest, pytest-asyncio |
| 部署 | Docker, Docker Compose, Render |

---

## 系统架构

```
Browser                         Browser
   │                                │
   │  WebSocket (wss://)            │  WebSocket (wss://)
   │                                │
   ▼                                ▼
┌──────────────────────────────────────────┐
│               FastAPI                     │
│  ┌──────────────────────────────────┐     │
│  │       ConnectionManager          │     │
│  │   连接管理 / 在线用户 / 广播      │     │
│  └──────────────┬───────────────────┘     │
│                 ▼                         │
│  ┌──────────────────────────────────┐     │
│  │        OperationManager          │     │
│  │   版本校验 / 冲突检测 / 加锁      │     │
│  │   幂等去重 / ACK 生成            │     │
│  └──────────────┬───────────────────┘     │
│                 ▼                         │
│  ┌──────────────────────────────────┐     │
│  │   DocumentManager / Service      │     │
│  │   apply_operation / 文档缓存      │     │
│  └──────────────┬───────────────────┘     │
│                 ▼                         │
│  ┌──────────────────────────────────┐     │
│  │           Repository             │     │
│  │   documents / blocks / ops CRUD  │     │
│  └──────────────┬───────────────────┘     │
│                 ▼                         │
│  ┌──────────────────────────────────┐     │
│  │            SQLite                │     │
│  └──────────────────────────────────┘     │
└──────────────────────────────────────────┘
```

**协同流程**：客户端构建 Operation（version = doc.version + 1）→ WebSocket 发送 → OperationManager 校验版本 → 幂等检查 → apply → 返回 ACK → 广播给同文档其他客户端。

---

## 协同机制说明

### Version

文档维护单调递增版本号。客户端发来的每个 Operation 携带 `version` 字段，服务端校验 `op.version == doc.version + 1`，不匹配则拒绝并返回 conflict。

### ACK

服务端处理完 Operation 后返回 `ack` 消息：

- `applied`：操作已成功应用到文档
- `duplicate`：该操作已处理过（幂等去重）

### Idempotency

每个 Operation 有唯一 ID（UUID）。服务端将已处理的 operation 持久化到 `operations` 表，收到重复 operation 时返回 duplicate ACK，不会重复应用到文档。

### Retry

客户端发送 Operation 后启动 ACK 超时定时器（5s 基础）。超时未收到 ACK 则重发，指数退避（5s → 10s → 20s），最多重试 3 次。Operation ID 在重试过程中保持不变，服务端通过 Idempotency 保证不会重复应用。

### Reconnect

WebSocket 断开后自动重连，间隔 1s → 2s → 4s → 8s → 10s（上限）。重连成功后重新发送 `join` 消息，并 flush 所有 pending operations。

### Conflict Recovery

版本不匹配时，服务端返回 `conflict` 消息，拒绝当前 Operation。客户端自动通过 HTTP GET 拉取最新 Document，替换本地状态。用户可在最新文档基础上继续编辑。

> 当前不是 OT（Operational Transformation）或 CRDT 方案，冲突时直接拒绝而非自动合并。

### Presence

同一 Document 内维护在线用户列表。用户加入 / 离开时，ConnectionManager 广播完整在线用户列表到同文档所有客户端。前端 `OnlineUsers` 组件实时显示。

---

## 项目结构

```
collaborative-editor/
├── apps/
│   ├── server/              # FastAPI 后端
│   │   ├── app/
│   │   │   ├── database/    # SQLite 连接与 Repository
│   │   │   ├── document/    # DocumentManager & Service
│   │   │   ├── operation/   # apply_operation & OperationManager
│   │   │   ├── types/       # Pydantic 模型
│   │   │   ├── websocket/   # WebSocket 端点 & ConnectionManager
│   │   │   └── main.py      # 应用入口 & 静态文件托管
│   │   ├── tests/           # 测试套件
│   │   └── requirements.txt
│   └── web/                 # Vue 3 前端
│       ├── src/
│       │   ├── components/  # Editor, EditorHeader, OnlineUsers 等组件
│       │   ├── editor/      # EditorState 状态管理
│       │   ├── state/       # useEditorStore, usePresenceStore
│       │   ├── websocket/   # WebSocketClient（连接 + 重连 + 重试）
│       │   └── types/       # TypeScript 类型定义
│       └── package.json
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

---

## 本地运行

### 方式一：开发模式

**后端**：

```bash
cd apps/server
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**前端**：

```bash
cd apps/web
npm install
npm run dev
```

前端：`http://localhost:5173`，后端：`http://localhost:8000`。

### 方式二：Docker

```bash
docker compose up -d
```

浏览器打开 `http://localhost:8000`。

---

## 线上部署

项目使用 Docker 多阶段构建，部署在 [Render](https://render.com) Free Tier。

- **Dockerfile**：Node 20 构建前端 → Python 3.12-slim 运行后端
- **静态文件**：FastAPI 托管 Vue dist 目录
- **端口**：通过 `PORT` 环境变量配置（线上为 Render 注入）
- **WebSocket**：前端自动根据 `https://` 切换 `wss://`
- **健康检查**：`GET /health` → 200
- **数据库**：SQLite，数据路径 `/app/data/editor.db`

---

## 测试

```bash
cd apps/server
python -m pytest tests/ -v
```

共 53 个测试：

| 文件 | 数量 | 覆盖内容 |
|------|------|----------|
| `test_apply_operation.py` | 23 | insert / delete / create_block / delete_block / update_block / 幂等性 |
| `test_operation_manager.py` | 5 | 正常应用 / 重复去重 / 文档不存在 / 版本冲突 / apply 异常 |
| `test_websocket.py` | 9 | 连接 / 拒绝 / ACK / 广播 / 断线清理 / Presence |
| `test_collaboration.py` | 4 | 多人协同 / 冲突场景 / 重连清理 / 重复操作不广播 |
| `test_document_title.py` | 12 | 创建默认标题 / 更新标题 / 广播同步 / 跨文档隔离 / 持久化 |

前端类型检查与构建：

```bash
cd apps/web
npm run build       # vue-tsc 类型检查 + vite build
```

---

## 当前限制

- SQLite 单文件，不适合多机部署
- ConnectionManager 使用进程内存，当前架构使用单进程
- Render Free 实例的本地文件系统非常量磁盘，SQLite 数据可能在实例重启后丢失
- 无用户认证与权限系统
- 无历史版本回退功能
- Conflict 采用拒绝 + 拉取最新 Document 方案，不是 OT / CRDT 自动合并

---

## 未来扩展

- Operational Transformation 或 CRDT 实现无冲突自动合并
- Redis Pub/Sub 支持多机横向扩展
- PostgreSQL 作为持久化存储
- 用户认证与权限控制
- 历史版本与回退
- Undo / Redo
- Cursor 同步
- Slash Menu & Formatting Toolbar