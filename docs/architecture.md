# 项目架构文档

本文档内容：详细说明系统架构、数据流、通信协议与关键技术决策。

## 项目介绍

协同编辑器 MVP，目标是在浏览器端实现多人实时编辑同一文档，服务端负责冲突检测与数据持久化。当前版本以功能验证为主，未引入 OT 或 CRDT，冲突时直接拒绝操作。

## 技术栈

| 层级 | 技术 | 选型理由 |
|---|---|---|
| 前端框架 | Vue 3 + TypeScript | 响应式系统适合实时 UI 更新，Composition API 便于状态逻辑复用 |
| 前端构建 | Vite | 启动快、HMR 体验好 |
| 后端框架 | FastAPI | 原生支持异步，WebSocket 集成简单，类型注解与 Pydantic 模型天然契合 |
| 数据库 | SQLite（aiosqlite） | 零配置、单文件、适合 MVP 快速验证，异步驱动避免阻塞事件循环 |
| 通信协议 | 原生 WebSocket | 全双工、低延迟，浏览器与 FastAPI 均原生支持 |
| 测试 | pytest + pytest-asyncio | Python 生态标准，支持异步函数测试 |

## 项目目录

核心代码位置：

- `apps/server/app/websocket/` — WebSocket 端点与连接管理
- `apps/server/app/operation/manager.py` — 操作处理（加锁、版本校验、幂等）
- `apps/server/app/document/service.py` — 文档读写与 apply_operation
- `apps/server/app/database/repository.py` — SQLite 数据访问层
- `apps/web/src/editor/EditorState.ts` — 前端状态管理与冲突恢复
- `apps/web/src/websocket/WebSocketClient.ts` — 前端 WebSocket 连接与重连逻辑

## 总体架构

```
┌─────────────────┐                      ┌─────────────────┐
│   Browser A     │◄─────WebSocket──────►│                 │
│  (Editor.vue)   │                      │  FastAPI Server │
└─────────────────┘                      │                 │
                                         │  ┌───────────┐  │
┌─────────────────┐                      │  │ Operation │  │
│   Browser B     │◄─────WebSocket──────►│  │  Manager  │  │
│  (Editor.vue)   │                      │  └─────┬─────┘  │
└─────────────────┘                      │        │        │
                                         │  ┌─────┴─────┐  │
                                         │  │ Document  │  │
                                         │  │  Service  │  │
                                         │  └─────┬─────┘  │
                                         │        │        │
                                         │  ┌─────┴─────┐  │
                                         │  │  SQLite   │  │
                                         │  │ (aiosqlite)│  │
                                         │  └───────────┘  │
                                         └─────────────────┘
```

## 数据流

一次完整编辑操作的数据流：

1. **用户输入** → `Editor.vue` 捕获事件
2. `Editor.vue` 调用 `EditorState.buildOperation()` 构建 Operation
3. `EditorState` 将 Operation 推入 pending 队列，调用 `WebSocketClient.send()`
4. `WebSocketClient` 通过 WebSocket 发送 `operation` 消息到服务端
5. 服务端 `websocket/server.py` 接收消息，调用 `OperationManager.process()`
6. `OperationManager` 加文档锁 → 校验版本 → 调用 `DocumentService.apply_operation()` → 写入 SQLite → 返回 ack
7. `websocket/server.py` 向发送者返回 `ack`，向其他客户端广播 `operation`
8. **Browser A** 收到 `ack`，从 pending 队列移除该 Operation
9. **Browser B** 收到广播的 `operation`，调用 `EditorState.applyRemoteOperation()` 更新本地文档

## WebSocket 通信协议

所有消息均为 JSON，通过原生 WebSocket 传输。

### 消息类型总览

| 类型 | 方向 | 说明 |
|---|---|---|
| `join` | C → S | 客户端加入文档，携带 client_id |
| `operation` | C → S | 客户端发送编辑操作 |
| `ack` | S → C | 服务端确认操作已处理 |
| `conflict` | S → C | 操作被拒绝，携带原因与当前版本 |

### join（客户端 → 服务端）

```json
{
  "type": "join",
  "client_id": "c1"
}
```

服务端收到后记录连接关系，并将当前文档快照发送给客户端。

### operation（客户端 → 服务端）

```json
{
  "type": "operation",
  "id": "op1",
  "client_id": "c1",
  "document_id": "doc_1",
  "block_id": "b1",
  "type": "insert",
  "position": 2,
  "content": "hello",
  "version": 3
}
```

字段说明：

- `id`：操作唯一标识（UUID），用于幂等去重
- `client_id`：发送者标识
- `document_id`：目标文档 ID
- `block_id`：目标 Block ID
- `type`：操作类型（insert / delete / update / create_block / delete_block）
- `position`：文本操作位置（insert / delete 适用）
- `content`：文本内容（insert / update / create_block 适用）
- `version`：客户端期望的文档版本（应为 doc.version + 1）

### ack（服务端 → 客户端）

```json
{
  "type": "ack",
  "operation_id": "op1",
  "document_id": "doc_1",
  "version": 3,
  "status": "applied"
}
```

`status` 取值：

- `applied`：操作已成功应用到文档
- `duplicate`：该操作已处理过，直接返回已有结果

### conflict（服务端 → 客户端）

```json
{
  "type": "conflict",
  "operation_id": "op1",
  "document_id": "doc_1",
  "current_version": 5,
  "reason": "Version mismatch: expected 6, got 3"
}
```

触发场景：

- 文档不存在
- 版本号不匹配（`op.version != doc.version + 1`）
- `apply_operation` 抛出异常（如位置越界）

## Operation

### 五种操作类型

| 类型 | 必填字段 | 行为 |
|---|---|---|
| `insert` | block_id, position, content | 在 block_id 的 position 处插入 content |
| `delete` | block_id, position, length | 从 block_id 的 position 处删除 length 个字符 |
| `update` | block_id, content | 将 block_id 的内容替换为 content |
| `create_block` | content | 在文档末尾新增一个 Block，内容为 content |
| `delete_block` | block_id | 删除指定 block_id 的 Block |

### 幂等性

所有操作以 `operation.id` 为唯一键。服务端收到操作后先查 `operations` 表，若已存在则直接返回 `duplicate` 状态的 ack，确保同一操作重复发送不会导致文档状态异常。

### apply_operation 核心逻辑

```python
def apply_operation(doc: Document, op: Operation) -> Document:
    if op.type == "insert":
        block = find_block(doc, op.block_id)
        block.content = block.content[:op.position] + op.content + block.content[op.position:]
    elif op.type == "delete":
        block = find_block(doc, op.block_id)
        block.content = block.content[:op.position] + block.content[op.position + op.length:]
    # ... 其他类型
    doc.version += 1
    return doc
```

## Version

### 版本号机制

- 每个文档有一个单调递增的 `version` 字段，初始为 0
- 每次成功 apply 一个操作，version + 1
- 客户端发送操作时携带 `version`，服务端校验 `op.version == doc.version + 1`

### 为什么不用 OT 而直接拒绝

MVP 阶段优先保证正确性与实现简单性。直接拒绝冲突操作并通知客户端拉取最新文档，虽然用户体验上会有"编辑被驳回"的感觉，但避免了 OT 算法的复杂性与 CRDT 的存储开销。后续迭代可引入 OT 或 CRDT 实现无冲突自动合并。

## ACK

### applied

操作通过版本校验并成功 apply 后返回。字段包含：

- `operation_id`：对应操作的 id
- `version`：apply 后的新文档版本
- `status`: "applied"

### duplicate

操作 id 已存在于 `operations` 表中时返回。字段包含：

- `operation_id`：对应操作的 id
- `version`：客户端传入的 version（或上次处理的 version）
- `status`: "duplicate"

客户端收到 `duplicate` 后只需从 pending 队列移除该操作，无需其他处理。

## Conflict

### 触发场景

1. **文档不存在**：`DocumentService.get_document(doc_id)` 返回 None
2. **版本不匹配**：`op.version != doc.version + 1`，说明客户端基于过期文档编辑
3. **apply 异常**：如 `position` 超出文本长度、`block_id` 不存在等

### 返回字段

- `operation_id`：冲突的操作 id
- `current_version`：服务端当前文档版本（场景 2 时用于客户端校准）
- `reason`：人类可读的冲突原因

### 客户端恢复策略

收到 `conflict` 后：

1. 从 pending 队列移除该操作
2. 通过 HTTP GET `/api/documents/{doc_id}` 拉取最新文档
3. 用最新文档替换本地 `EditorState.doc`
4. 触发 UI 刷新，用户基于最新内容继续编辑

## 重连

### 指数退避算法

```typescript
private getReconnectDelay(): number {
  const delay = 1000 * Math.pow(2, this.reconnectAttempts);
  return Math.min(delay, 10000); // 上限 10s
}
```

- 第 1 次重连：1s
- 第 2 次重连：2s
- 第 3 次重连：4s
- 第 4 次重连：8s
- 第 5 次及以后：10s（上限）

### 重连流程

1. `onclose` / `onerror` 触发 `scheduleReconnect()`
2. 按退避延迟等待后创建新 WebSocket 连接
3. `onopen` 时：
   - `reconnectAttempts = 0`（重置计数器）
   - 发送 `join` 消息
   - 调用 `flush()` 发送 pending 队列中所有未确认的操作

### pending 队列

- 调用 `send()` 时若连接断开，Operation 被暂存到 `pendingOps` 数组
- 重连成功后 `flush()` 按 FIFO 顺序逐个发送
- 收到 `ack` 后从队列移除

## SQLite

### 表结构

**documents**

| 字段 | 类型 | 说明 |
|---|---|---|
| id | TEXT PRIMARY KEY | 文档唯一标识 |
| version | INTEGER | 当前版本号 |
| blocks | TEXT (JSON) | Block 数组序列化 |
| updated_at | TIMESTAMP | 最后更新时间 |

**operations**

| 字段 | 类型 | 说明 |
|---|---|---|
| id | TEXT PRIMARY KEY | 操作唯一标识 |
| client_id | TEXT | 发送者标识 |
| document_id | TEXT | 所属文档 |
| type | TEXT | 操作类型 |
| payload | TEXT (JSON) | 操作参数序列化 |
| created_at | TIMESTAMP | 创建时间 |

### 为什么持久化操作日志

1. **幂等去重**：通过 `operations.id` 的唯一约束防止重复 apply
2. **审计追踪**：可回溯谁在什么时间做了什么修改
3. **未来扩展**：为引入 OT 或历史版本提供数据基础

### 并发控制

SQLite 写锁是文件级的，服务端通过 `asyncio.Lock` 按 `document_id` 加细粒度锁，避免同一文档的并发操作竞争，同时允许不同文档的操作并行处理。

## 测试

### 测试架构

| 测试文件 | 测试对象 | 策略 |
|---|---|---|
| `test_apply_operation.py` | `apply_operation()` 纯函数 | 直接调用，构造 Document + Operation，断言结果 |
| `test_operation_manager.py` | `OperationManager.process()` | mock `OperationRepository` 和 `DocumentService`，验证流程分支（正常、重复、冲突、异常） |
| `test_websocket.py` | WebSocket 端点 | `TestClient` 模拟连接，mock `ConnectionManager`，验证消息收发与断开清理 |
| `test_collaboration.py` | 多客户端场景 | 同上，验证广播排除发送者、冲突场景、重复操作不广播 |

### mock 策略

- `AsyncMock` 模拟所有异步依赖（Repository、Service、ConnectionManager 方法）
- `MagicMock` 构造 ack/conflict 返回值，确保 `model_dump()` 返回可序列化的 dict
- `side_effect` 模拟 `join` 方法向测试客户端发送文档快照，避免 `receive_json()` 阻塞

## 已知限制

- **无分布式锁**：单进程 `asyncio.Lock` 无法跨多机部署，后续需引入 Redis 分布式锁
- **无 OT/CRDT**：冲突时直接拒绝，用户体验受限，高并发场景下冲突率会上升
- **SQLite 并发写瓶颈**：文件级写锁，大量并发写操作会串行化，成为性能瓶颈
- **无 WebSocket 心跳**：当前依赖 TCP 层检测断开，弱网环境下可能感知延迟较大

## 未来规划

### 技术演进路线

1. **引入 OT 或 CRDT**
   - OT：保留现有版本号机制，增加变换函数，将冲突操作自动变换后应用
   - CRDT：替换版本号机制，采用 Yjs 或 Automerge 方案，实现最终一致性

2. **Redis Pub/Sub 横向扩展**
   - 多台 FastAPI 实例通过 Redis 广播操作，突破单机连接数限制
   - 替换 `asyncio.Lock` 为 Redis 分布式锁

3. **分片存储**
   - 文档按 ID 哈希分片到多个 SQLite 文件或迁移到 PostgreSQL
   - 操作日志独立存储，支持按时间范围查询

4. **用户系统与权限**
   - JWT 认证，WebSocket 连接时校验 token
   - 文档级权限：读、写、管理

5. **历史版本与回退**
   - 基于操作日志回放生成任意版本快照
   - UI 支持查看历史时间轴与一键回退