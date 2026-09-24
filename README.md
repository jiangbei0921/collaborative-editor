# 协同编辑器项目

基于 Vue 3 + FastAPI + WebSocket + SQLite 的实时协同 Block 编辑器。

## 项目介绍

一个支持多人实时协同编辑的 Block 级文档系统。多客户端通过 WebSocket 连接到服务端，编辑操作以原子 Operation 形式同步，服务端基于版本号进行冲突检测与恢复，确保数据一致性。

## 安装

### 后端

```bash
cd apps/server
pip install -r requirements.txt
```

### 前端

```bash
cd apps/web
npm install
```

## 启动

### 后端

```bash
cd apps/server
uvicorn app.main:app --reload --port 8000
```

### 前端

```bash
cd apps/web
npm run dev
```

前端默认运行在 `http://localhost:5173`，后端 API 地址为 `http://localhost:8000`。

## 使用方法

1. 启动前后端服务
2. 浏览器打开前端地址
3. 创建或打开一个文档
4. 多个浏览器窗口打开同一文档即可实时协同编辑

## 技术栈

- **前端**：Vue 3 + TypeScript + Vite
- **后端**：FastAPI + Python 3.12
- **通信**：WebSocket（原生）
- **数据库**：SQLite（aiosqlite 异步驱动）
- **测试**：pytest + pytest-asyncio

## 项目目录

```
collaborative-editor/
├── apps/
│   ├── server/              # FastAPI 后端
│   │   ├── app/
│   │   │   ├── database/    # SQLite 连接与 Repository
│   │   │   ├── document/    # 文档服务（apply_operation）
│   │   │   ├── operation/   # 操作处理（加锁、版本校验）
│   │   │   ├── types/       # Pydantic 模型
│   │   │   ├── websocket/   # WebSocket 端点与连接管理
│   │   │   └── main.py      # 应用入口
│   │   ├── tests/           # 测试套件
│   │   └── requirements.txt
│   └── web/                 # Vue 3 前端
│       ├── src/
│       │   ├── components/  # Editor.vue 等组件
│       │   ├── editor/      # EditorState（状态管理）
│       │   ├── websocket/   # WebSocketClient（连接+重连）
│       │   └── types/       # TypeScript 类型定义
│       └── package.json
└── docs/
    └── architecture.md      # 架构文档
```

## 总体架构

前端通过 WebSocket 与 FastAPI 服务端长连接通信，服务端基于 SQLite 持久化文档快照与操作日志。一次编辑操作的完整路径：客户端构建 Operation → WebSocket 发送 → 服务端校验版本并 apply → 返回 ack → 广播给其他客户端。

## WebSocket

用于实时推送操作与广播，支持自动重连。连接建立后客户端发送 `join` 消息，之后所有编辑操作通过 `operation` 消息传输。

## Operation

Block 级原子操作，支持五种类型：

- `insert`：在指定 Block 的指定位置插入文本
- `delete`：在指定 Block 的指定位置删除指定长度文本
- `update`：更新指定 Block 的全部内容
- `create_block`：在文档末尾新增一个 Block
- `delete_block`：删除指定 Block

## Version

服务端用单调递增的版本号检测冲突，确保操作按序执行。客户端发送的操作需携带 `version` 字段，服务端校验 `op.version == doc.version + 1`，不匹配则返回 conflict。

## ACK

服务端处理完操作后返回 `ack` 消息，包含两种状态：

- `applied`：操作已成功应用到文档
- `duplicate`：该操作已处理过（幂等去重）

## Conflict

版本不匹配时服务端返回 `conflict` 消息，客户端自动通过 HTTP 拉取最新文档并重置本地状态，用户可继续编辑。

## 重连

客户端网络断开时自动触发重连，采用指数退避策略（1s → 2s → 4s → … → 10s 上限）。重连成功后自动 flush 未发送的 pending 操作。

## SQLite

轻量级本地数据库，零配置，适合 MVP 阶段。存储两张核心表：

- `documents`：文档快照（id, version, blocks, updated_at）
- `operations`：操作日志（id, client_id, document_id, type, payload, created_at）

操作日志用于幂等去重，防止同一操作被重复应用。

## 测试

```bash
cd apps/server
python -m pytest tests/ -v
```

当前共 37 个测试，覆盖：

- `test_apply_operation.py`：核心 apply 逻辑（23 个）
- `test_operation_manager.py`：操作处理流程与冲突检测（5 个）
- `test_websocket.py`：WebSocket 连接与消息收发（5 个）
- `test_collaboration.py`：多客户端协同场景（4 个）

## 已知限制

- 无用户认证与权限系统
- 无历史版本回退功能
- 未实现 OT（Operational Transformation）或 CRDT，冲突时直接拒绝操作而非自动合并
- SQLite 单文件不支持多机部署，并发写存在瓶颈

## 未来规划

- 引入 Operational Transformation 或 CRDT，实现无冲突自动合并
- 支持 Redis Pub/Sub，实现多机横向扩展
- 增加用户系统、权限控制与文档分享
- 增加历史版本与回退功能