# Architecture / 产品与代码结构

Current as of 2026-10-14. Read [team onboarding](TEAM_HANDOFF_CURRENT_CN.md) first for setup and API names.
本文描述实际实现，不把真实 Alexa、MCP 或 AWS 规划当成已完成。

## Product model / 产品模型

- Companion: a cat profile in the demo household / 猫咪档案。
- Caregiver: a declared attribution identity, not an authenticated user / 自报照护者。
- Observation: one health event; follow-up answers update it / 一条观察事件。
- Care log: one cat's event history / 某只猫的历史。
- Report: a requested, time-bounded view; default rolling seven days / 按需时间范围汇总。
- Conversation: persisted turns and state; pending subject clarification can exist before any event / 会话可以先存在，事件尚未创建。

The current household is a shared demo household. Cat filtering is not user access control.
当前是单演示家庭；多猫隔离不等于多账户权限隔离。

## Runtime flow / 运行链路

```text
web simulator (typed input)
  → POST /conversations/turns
  → conversation_service.process_turn
      → language_action_service (management / corrections)
      → subject resolution (ask if missing)
      → ai_extraction_service (rules or OpenAI)
      → Pydantic validation
      → questionnaire + deterministic rules
      → SQLite transaction: event + session + turn
  → speech + status + identifiers + ui_action
  → UI refreshes profiles / event / requested report
```

OpenAI is called only by the backend. Both management classification and health extraction use the same Responses adapter with separate output schemas. Common management commands are recognized locally; not every turn calls a model twice.
OpenAI 不直接写数据库，也不负责所有回复；后端校验与状态机决定记录、确认、追问和提交。

## Source map / 目录职责

| Path | Responsibility / 职责 |
|---|---|
| `app.py` | FastAPI entry, routes, static files, startup database initialization |
| `catnanny/web/` | HTTP routes and existing HTML/CSS/JS client |
| `catnanny/domain/` | Schemas, questions, rules and model-independent definitions |
| `catnanny/services/` | Conversations, profiles, queries, correction, photo and report workflows |
| `catnanny/adapters/openai_responses.py` | Shared backend Responses REST call |
| `catnanny/prompts/` | Observation extraction and language-action classification instructions |
| `catnanny/storage/` | SQLite connections, repositories and additive migrations |
| `catnanny/alexa_skill/` | Shared text adapter and older slot adapter; not a live integration |
| `catnanny/mcp_server/` | Tool wrapper draft; no complete Streamable HTTP MCP service |
| `skill-package/` | Alexa interaction-model draft; optional future integration |
| `tests/` | Isolated backend tests and Node DOM-based behavior tests |
| `scripts/` | Database backup/init, local scenario and opt-in paid evaluations |
| `examples/` | Example conversations and extraction evaluation cases |
| `docs/` | Curated current documentation and OpenAPI snapshot |

## Data and integrity / 数据与一致性

SQLite defaults to `data/catnanny.sqlite3`; photos default to `uploads/events/{event_id}/`.
会话和原文落库，浏览器只缓存恢复所需的会话选择，不是唯一记录来源。

Registered names match case-insensitively. Missing subject causes a question before creating an event. Naming another cat for a new observation differs from explicitly correcting the current observation's cat.
已知目标的纠错直接改归；未知目标先确认建档。事件 ID、原始时间和照片关联保留，转移有审计记录；其他历史事件不动。

Each logical turn has a request ID. An identical retry replays the response; changing the payload under the same ID conflicts.
AI errors do not count as saved observations. Unknown fields remain unknown, rather than becoming false.

Photos are stored as files and referenced from SQLite. Photo URLs currently include the configured public base URL at creation time.
照片文件不是存在 SQLite 的图片二进制；换域名时旧地址需单独迁移。

## Reports and platform boundary / 报告与平台边界

The backend returns report JSON. The current web client renders tables and generates standalone HTML with embedded photos; there is no PDF/email delivery API.
报告仅在请求时获取或下载；不自动发给兽医。

The web simulator represents text received by a conversational assistant. Requesting an upload link is conversational; capturing/uploading the photo remains a browser action.
真实 Alexa 仍需要平台认证、路由、响应格式和设备测试。云端部署也不等于完成 Alexa 接入。

## Cloud handoff / 云端交接

For the present SQLite/file architecture, start with one Lightsail instance, HTTPS and persistent directories; back up both SQLite and uploaded files.
多实例无状态方案需要先改造共享数据库与对象存储。App Runner 的临时文件系统不能承载当前唯一的数据库和照片副本。
See [deployment handoff](TEAM_HANDOFF_CURRENT_CN.md) for configuration, migration boundaries and acceptance.

