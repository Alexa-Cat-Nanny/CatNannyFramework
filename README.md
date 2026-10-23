October 23, 2026

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

## Team ownership / 团队分工 [updated Oct 23, 2026]

Frontend @ShuWangs: Develop the user interface and mobile layouts for cat profiles, conversations, photo uploads, and seven-day care reports. Improve loading states, error messages, and user interactions.
前端：负责用户界面与移动端适配，实现猫咪档案、对话记录、照片上传及七天护理报告展示，完善加载状态、错误提示和页面交互。

Backend @yifengp: Develop APIs, conversation workflows, and data management for symptom tracking, follow-up questions, corrections, photo linking, and report generation. Handle server-side AI integration and API testing.
后端：负责 API、对话流程与数据管理，实现症状记录、多轮追问、信息纠正、照片关联及报告生成，并完成服务端 AI 调用与接口测试。

AWS & MCP @Y1t1anL1u : Manage AWS deployment, HTTPS, server-side secrets, and persistent storage and backups for records and photos. Develop and test MCP services and connection adapters to support Alexa tool integration.
AWS 与 MCP：负责 AWS 云端部署、HTTPS 配置、密钥管理及数据库与照片的持久化备份；开发并测试 MCP 服务与连接适配，推进 Alexa 的工具调用集成。


## Hackathon positioning / 比赛定位

The official Alexa+ track permits a simulated experience as an alternate entry path. This repository demonstrates that path; it does not claim a deployed Alexa+ integration.
AWS is optional for this path; claiming an AWS mini-challenge requires documented actual use.
[Official rules / 官方规则](https://amazonappdev2026.devpost.com/rules).




