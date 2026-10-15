# Cat Nanny — Start Here / 从这里开始

A working, local Alexa+ experience simulation for shared cat care.
面向多猫、多照护者家庭的本地文字对话 MVP；当前不是已上线的 Alexa 服务。

Describe an observation → answer follow-up questions → attach a photo → request a seven-day care report.
描述症状 → 回答追问 → 关联照片 → 按需查看七天报告。

## Read in this order / 阅读顺序

1. [Team onboarding / 团队交接与本地复现](docs/TEAM_HANDOFF_CURRENT_CN.md) — first document for everyone after cloning; setup, API list, frontend/backend ownership, AWS plan.
2. [Architecture / 产品与代码结构](docs/ARCHITECTURE.md) — conversation core, OpenAI calls, SQLite, photos and reports.
3. [Simulator guide / 模拟器用法](docs/SIMULATOR_GUIDE.md) — profiles, observations, history and reports.
4. [Language workflows / 语言与 Alexa 对应关系](docs/LANGUAGE_WORKFLOWS.md) — language equivalents, name corrections, platform boundaries.
5. [Demo and acceptance / 用例与验收](docs/DEMO_SCRIPT.md) — reproducible demonstration and module checks.

After starting the app: [Simulator](http://localhost:8000/simulator), [API docs](http://localhost:8000/docs), [Live OpenAPI](http://localhost:8000/openapi.json).
启动后使用以上入口；接口字段以实时 OpenAPI 与当前 Pydantic schema 为准。

## Local quick start / 本地启动

Requires Python 3.11+; Python 3.12 recommended. Node is optional, only for frontend logic tests.
需要 Python 3.11+，建议 3.12；运行现有网页不需要安装前端构建工具。

Windows PowerShell, from the cloned repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000 --env-file .env
```

Copy the template only on a fresh clone; do not overwrite an existing personal configuration.
模板默认使用离线 rules 模式，无密钥也能跑通支持的演示用例。复制步骤仅适用于没有 .env 的新 clone。

macOS/Linux commands and optional OpenAI setup are in the team handoff.
其他系统及真实 AI 配置见交接文档。

## Current scope / 当前范围

- Multi-turn text conversations for vomiting and appetite observations; structured validation and persistent context.
- 猫名识别与归属追问、多猫档案、照护者自报、当前事件口误纠正。
- Event-bound photos, requested seven-day reports, JSON and embedded-photo HTML exports.
- SQLite persistence; offline rules or backend-only OpenAI Responses extraction.
- Recent verification: 88 Python tests and 5 JavaScript behavior tests passed. Browser layout/click checks remain manual.

Not implemented / 尚未完成: live Alexa integration, a compliant hosted MCP server, AWS deployment, real SMS/email, document uploads, user authentication and multi-household access control. Existing Alexa/MCP files are adapters/drafts, not deployment evidence.

## Team ownership / 团队分工

Frontend: polish the existing pages or build another client against the conversation API; preserve subject clarification, correction, restore and explicit report behavior.
前端：页面、手机适配、加载与错误反馈、实际点按验收；不要在浏览器中持有 OpenAI 密钥。

Backend/AWS: keep the API contract stable; deploy HTTPS, manage server-side secrets, persist and back up both database and photos.
后端/AWS：先考虑单实例持久存储；换云数据库或 S3 是额外的代码适配工作。

## Hackathon positioning / 比赛定位

The official Alexa+ track permits a simulated experience as an alternate entry path. This repository demonstrates that path; it does not claim a deployed Alexa+ integration.
AWS is optional for this path; claiming an AWS mini-challenge requires documented actual use.
[Official rules / 官方规则](https://amazonappdev2026.devpost.com/rules).

## Repository hygiene / 仓库说明

`.env`, `.venv/`, `data/` and `uploads/` are ignored and not delivered by cloning. Each teammate creates local configuration and local data.
密钥、实际记录和照片不随 clone 分发。当前没有容器/基础设施部署模板，依赖尚未锁定版本。



