# AGENT_APP

基于 FastAPI + LangChain/LangGraph 的多智能体数据分析后端。当前版本采用 `supervisor + specialist agents` 架构，由主智能体统一编排数据库问答、图表生成、分析报告、仪表盘生成和文件分析，并通过统一协议返回给前端。

## 项目特性

- 单一聊天入口：普通问答、图表、分析、仪表盘、文件分析都走统一聊天协议
- 多智能体编排：主智能体负责拆解任务并调用子智能体
- 流式返回：`/chat/stream` 通过 SSE 向前端持续推送状态和最终结果
- 统一结果结构：前后端按 `type + payload` 渲染，避免多套分支协议
- 文件上传支持：上传后可把 `file_path` 继续带入聊天链路
- 可观测性：前端可看到本次请求实际调用了哪些子智能体

## 智能体架构

### 主智能体

- `supervisor`
  - 接收用户问题
  - 判断应该调用哪些子智能体
  - 汇总多个子结果
  - 以统一 JSON 协议输出给前端

### 子智能体

- `sql_specialist`：数据库问答、SQL 查询、结构化文本回答
- `chart_specialist`：生成单图表 ECharts 配置
- `analyze_specialist`：生成表格 + 分析结论 + 图表
- `dashboard_specialist`：生成多图表仪表盘链接
- `file_specialist`：分析上传文件并返回处理结果/下载地址

## 技术栈

### 后端

- FastAPI
- LangChain
- LangGraph
- PostgreSQL Checkpointer
- Pydantic

### 前端

- Vue 2
- Element UI
- ECharts

## 目录结构

```text
AGENT_APP/
├─ app/
│  ├─ ai/
│  │  ├─ agent/          # 各类智能体
│  │  ├─ tool/           # 数据库、文件、仪表盘等工具
│  │  ├─ model/          # 模型初始化
│  │  └─ schema/         # 结构化输出 schema
│  ├─ api/
│  │  ├─ chat/           # 聊天与上传接口
│  │  └─ system/
│  ├─ static/
│  │  ├─ dashboard/      # 生成后的仪表盘 HTML
│  │  └─ upload/         # 用户上传文件
│  └─ utils/
├─ main.py               # FastAPI 应用入口
├─ requirements.txt
└─ README.md
```

## 接口说明

### 1. 非流式聊天

`GET /chat`

请求参数：

- `question`：用户问题
- `user_id`：用户标识
- `file_path`：可选，已上传文件路径

返回结构：

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "type": "text|chart|analyze|dashboard|file",
    "payload": {},
    "meta": {
      "agentCalls": ["sql_specialist", "chart_specialist"]
    }
  }
}
```

### 2. 流式聊天

`GET /chat/stream`

请求参数与 `/chat` 一致，返回 `text/event-stream`。

SSE 事件：

```json
{"event":"chunk","type":"text","content":"...","meta":{"agentCalls":[]}}
{"event":"final","type":"chart","payload":{},"meta":{"agentCalls":["chart_specialist"]},"done":true}
{"event":"error","content":"...","meta":{"agentCalls":["sql_specialist"]},"done":true,"error":true}
```

### 3. 文件上传

`POST /upload`

表单参数：

- `user_id`
- `file`

返回结构：

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "file_path": "app\\static\\upload\\xxx.docx",
    "file_name": "demo.docx",
    "file_id": "uuid"
  }
}
```

## 统一结果类型

### `text`

```json
{
  "type": "text",
  "payload": {
    "content": "文本回答"
  }
}
```

### `chart`

```json
{
  "type": "chart",
  "payload": {
    "chartJson": "{...}",
    "msg": "图表说明"
  }
}
```

### `analyze`

```json
{
  "type": "analyze",
  "payload": {
    "table": {},
    "result": "分析结论",
    "chartJson": "{...}"
  }
}
```

### `dashboard`

```json
{
  "type": "dashboard",
  "payload": {
    "url": "http://localhost:8000/static/dashboard/xxx.html",
    "message": "仪表盘已生成"
  }
}
```

### `file`

```json
{
  "type": "file",
  "payload": {
    "summary": "文件处理说明",
    "downloadUrl": "http://..."
  }
}
```

## 本地启动

### 1. 启动后端

```bash
pip install -r requirements.txt
python main.py
```

默认启动地址：

- 后端：`http://localhost:8000`

### 2. 启动前端

当前配套前端为本地独立目录：

```text
D:\PROJECT\Front\chat_agent
```

启动方式：

```bash
cd D:\PROJECT\Front\chat_agent
npm install
npm run dev
```

默认启动地址：

- 前端：`http://localhost:8080`

## 环境说明

项目依赖数据库、模型配置和 `.env` 中的连接参数。至少需要确认以下内容可用：

- PostgreSQL 连接参数
- 大模型 API Key
- 文件上传与静态目录写权限
- 前端跨域白名单已包含 `http://localhost:8080`

## 当前前后端协作方式

- 前端统一调用 `/chat/stream`
- 普通文本通过 `chunk` 增量显示
- 最终结果统一按 `type` 分发渲染
- 图表使用 `payload.chartJson`
- 仪表盘使用 `payload.url`
- 文件分析使用 `payload.downloadUrl`
- 可观测信息只保留 `agentCalls`

## 适合继续扩展的方向

- 增加更细的 agent 调用日志和执行时序
- 为 supervisor 加任务路由评估与失败重试策略
- 给仪表盘结果增加模板主题能力
- 为文件分析补充更多格式支持
- 增加接口测试和端到端联调脚本
