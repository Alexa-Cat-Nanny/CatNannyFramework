# Cat Nanny — Team Onboarding / 当前进度与团队交接

更新：2026-10-14。本文描述已核对的当前代码，不把规划当作完成。
供产品负责人、前端设计/开发同学、AWS 部署同学共同使用。

**Read this first after cloning.** This is the shared entry point for reproducing the demo, understanding the directory structure, integrating a frontend, and planning deployment. No OpenAI key or AWS account is required for the offline demo.

**先读本文再改代码。** 以下本地复现以新 clone 为前提；每位同学的数据库、照片、虚拟环境和密钥独立创建，不会从仓库自动获得。

## 0. Clone → configure → run / 新同学本地复现

### Before sharing the repository / 发给同学之前

The shared repository contains application source, current documentation, tests, prompts, migrations and a credential-free configuration template. Local data and credentials are excluded. Start with the offline template, then supply your own backend key for real AI.
共享版本包含运行所需代码与资源；实际记录、照片和密钥留在各自本机。后续发布也应检查 Git 变更并用干净副本复验。

Include / 应提交：`README.md`、当前文档、`docs/openapi.json`、`app.py`、`catnanny/`、`requirements.txt`、`pytest.ini`、`tests/`、`examples/`、`scripts/`、`skill-package/`（已标记为草稿）、`.gitignore`、`.env.example`。
Exclude / 不提交：实际 `.env`、密钥、`.venv/`、`data/`、`uploads/`、缓存和测试输出。不要直接复制本机数据库或照片给队友。

### Prerequisites / 环境

- Python 3.11+，建议 Python 3.12。不要使用 Python 3.10。
- Git；Node 只用于可选的前端逻辑测试，运行现有网页不需要 npm 安装或构建。
- 团队仓库：`https://github.com/Alexa-Cat-Nanny/CatNannyFramework.git`。

### Windows PowerShell

```powershell
git clone https://github.com/Alexa-Cat-Nanny/CatNannyFramework.git catNanny
cd catNanny
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000 --env-file .env
```

### macOS / Linux

```bash
git clone https://github.com/Alexa-Cat-Nanny/CatNannyFramework.git catNanny
cd catNanny
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
.venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8000 --env-file .env
```

If using Python 3.11, replace the version selector accordingly. Run all commands from the repository root. The server command stays running; use another terminal for tests.
已有 `.env` 时不要执行复制覆盖；已有环境时不必重建虚拟环境。端口已被占用时先确认现有服务，或改端口并同步 `.env` 的 `PUBLIC_BASE_URL`。

Open / 打开：

- [Simulator / 对话页](http://localhost:8000/simulator)
- [API docs / 接口页](http://localhost:8000/docs)
- [Live contract / 实时契约](http://localhost:8000/openapi.json)
- [Health check / 健康检查](http://localhost:8000/health)

`.env.example` defaults to `CATNANNY_EXTRACTION_PROVIDER=rules`. This offline mode supports the documented examples without a key; it is not general-purpose language understanding. Startup creates the local database and applies migrations; no database download is needed.
首次打开有演示猫 Mochi；按 `DEMO_SCRIPT.md` 的用例测试，避免用离线模式衡量任意自然语言能力。

### Optional real AI / 可选真实模型

In the local `.env`, set `CATNANNY_EXTRACTION_PROVIDER=openai`, supply your own `OPENAI_API_KEY`, and set `OPENAI_MODEL` to a supported model available to your account. The template lists the model previously verified for this project; account availability can differ. Restart the server after changing configuration. Calls incur provider usage.
密钥仅填本机后端配置，不发到聊天、前端或 Git；删除配置文件中的密钥后，也要重启进程才能清除已经加载的环境变量。无需为普通前端联调开启真实 AI。

### Tests / 测试

```powershell
.\.venv\Scripts\python.exe -m pytest -q
node --test tests/frontend_behavior.test.cjs
```

macOS/Linux: use `.venv/bin/python -m pytest -q`. Tests force offline AI and use independent databases. The current baseline is 88 Python tests and 5 Node behavior tests; verify current output after future changes. If Node is absent, the app and Python tests still work.

The scripts `evaluate_ai.py` and `evaluate_subject_correction.py` are optional paid evaluations and require explicit `--live`; do not use them as routine onboarding checks. `simulate_conversation.py` writes demo events to its configured database and is not an isolated test.

Onboarding verification on 2026-10-14: the offline template, application startup, page endpoints, documented vomiting conversation, unknown-cat correction, report and current documentation links passed a check using a separate database. The OpenAPI snapshot was refreshed. See the release commit for the shared delivery description.
验证使用独立测试数据；不会把开发者实际记录或密钥随仓库分发。

Common fixes / 常见排错：

- `/docs` 是接口文档；要直接打字请打开 `/simulator`。
- 找不到依赖：确认安装与运行使用同一个 `.venv` 解释器。
- 没有密钥却报 AI 配置错误：确认 provider 为 `rules`；终端中已设置的环境变量可能覆盖 `.env`，改正后重启。
- `rules` 模式无法理解任意表达：先使用本文链接的标准用例，或配置真实 AI。
- 手机不能访问 localhost：localhost 指手机本身，跨设备需局域网/云端可达地址，并同步配置公开链接；当前默认命令仅监听本机。
- 新 clone 没有旧记录/图片：这是正常行为，`data/` 与 `uploads/` 不纳入 Git。

## Reading map / 文档架构

| Document | Read it for / 阅读目的 |
|---|---|
| `README.md` | Shared starting point / 唯一项目入口 |
| 本文 `TEAM_HANDOFF_CURRENT_CN.md` | Setup, ownership, API list, deployment / 本地复现与分工 |
| `ARCHITECTURE.md` | Product concepts, directory map, data flow / 产品逻辑和代码结构 |
| `SIMULATOR_GUIDE.md` | Existing UI behavior / 页面用法 |
| `LANGUAGE_WORKFLOWS.md` | Language equivalents, corrections, Alexa boundary / 语言动作与 Alexa 对应 |
| `DEMO_SCRIPT.md` | Demo and acceptance scenarios / 用例与验收 |
| `/openapi.json` | Current machine contract / 运行中真实字段契约 |

The checked-in `docs/openapi.json` is a reference snapshot. Prefer the running app contract when code changes. Prompts in `catnanny/prompts/` are runtime resources, not obsolete documentation to remove.

## 1. Current status / 已经做到什么程度

The local end-to-end MVP is ready for UI polish and deployment preparation. Actual Alexa integration, authenticated users, notifications and cloud hosting remain unimplemented.

当前是可本地运行、端到端测试通过的文字对话 MVP，可开始前端设计和部署准备；不是已上线的多租户产品，也不是已验证的真实 Alexa+ 集成。

| 模块 | 已完成 | 边界 |
|---|---|---|
| 文字模拟器 | 英文默认、连续对话、刷新恢复、照片卡片、记录面板 | 目前通过打字模拟语音转写；不是语音识别 |
| AI 提取 | 后端调用 OpenAI Responses API，结构化输出和 Pydantic 校验；规则模式可离线联调 | 主要对话类型是呕吐 `vomit`、食欲 `appetite`；回复主要由规则和问卷拼接，并非所有话术都由模型生成 |
| 对象与上下文 | 按对话识别猫名；不明归属先追问；新增猫/照护者有语言入口 | 固定演示家庭；照护者是选择/自报身份，不是登录身份验证 |
| 口误纠正 | 当前事件改归另一只猫；未知猫确认后创建；照片随事件转移；保留审计历史 | 仅更正当前事件；不会批量搬动该猫全部历史，也不保证任意复合指令一次执行 |
| 数据 | SQLite 保存会话、原文、结构化事件、照护者和照片关联 | 本机文件存储，尚未接云数据库 |
| 照片 | JPEG/PNG/WebP、最大 8 MB、上传绑定事件、报告展示 | 本机上传链接；未实现真实短信/邮件、过期令牌、文档上传 |
| 报告 | 用户主动请求；默认最近七天；时间、症状、照片表格；JSON/内嵌照片 HTML 下载 | 不自动推送；没有 PDF 和真实邮件发送 |
| 验证 | 最近全量 88 项 Python 测试、5 项前端逻辑测试通过；此前独立真实模型纠错测试通过 | 前端测试使用 DOM 替身；布局和实际浏览器点按仍需人工验证 |
| 平台接入 | 共享对话核心、Alexa 文本适配函数 | 无真实 Alexa 上线证明；无已完成 MCP 服务或 AWS 部署交付 |

事件是一条观察；照护记录是某只猫的事件历史；报告是按请求和时间范围整理的视图。

## 2. OpenAI integration / 两条连接线到底是什么

The browser calls our backend, which alone calls OpenAI. Management classification and health extraction share one REST adapter and use different schemas; model output is validated before persistence.

前端只调用自己的后端。OpenAI 密钥不能进入前端代码、浏览器请求或 Git 仓库。

```text
网页文字输入
  → POST /conversations/turns
  → 对话核心
      A. 管理动作：常见表达本地识别；部分间接表达调用 OpenAI 分类
         例如新增猫、纠正猫名、请求报告
      B. 健康观察：OpenAI 提取症状字段和原文证据
         例如 vomit、episode_count、low_energy
  → Pydantic 校验 + 对话状态 + 规则/追问
  → SQLite 保存
  → 返回 speech、状态、事件、UI 动作
  → 前端显示；按需再读取记录/报告或打开照片页
```

A 和 B 共用同一个后端 OpenAI REST 适配器、服务端密钥和模型配置，使用不同输出结构。不是两套前端 OpenAI 连接，也不是每句话必定调用两次模型。当前截图原句的明确纠错可本地路由。

入口文件：

- `catnanny/services/conversation_service.py`：会话编排、上下文、数据库写入。
- `catnanny/services/language_action_service.py`：管理动作、确认、原子归属更正。
- `catnanny/services/ai_extraction_service.py`：规则/OpenAI 模式选择、症状字段校验。
- `catnanny/adapters/openai_responses.py`：唯一共用 Responses REST 调用封装。
- `catnanny/domain/schemas.py`、`language_actions.py`、`extraction.py`：输入输出契约。
- `catnanny/prompts/`：管理分类与健康提取提示词。

## 3. Frontend handoff / 前端同学接手什么

Use the existing UI or replace it with another client. Preserve conversation IDs, explicit subject clarification, correction updates and on-demand report generation. Styling does not require rebuilding business rules.

可以保留现有原生 HTML/CSS/JS 美化，也可换前端框架。业务规则、归属判断、问卷、数据库写入继续由后端负责。

优先读：

1. 本文：当前边界和分工。
2. `docs/LANGUAGE_WORKFLOWS.md`：按钮与语言动作的对应、纠错和恢复语义。
3. 运行服务的 `/docs` 与 `/openapi.json`：以实时接口为准。
4. `catnanny/web/static/chat.js`：现有请求、状态恢复、UI 动作、报告下载实现。
5. `simulator.html`、`app.css`、`upload.html`、`upload.js`：可复用页面。
6. `tests/frontend_behavior.test.cjs`：改版必须保持的行为。

### API 清单

| API | 前端用途 |
|---|---|
| `GET /capabilities` | 模式与功能能力；配置存在不等于真实调用已验证 |
| `GET /event-types` | 当前类别、字段结构和问题 |
| `POST /conversations/turns` | 发言、追问回答、纠错、语言管理；聊天主入口 |
| `GET /conversations/{session_id}` | 恢复当前状态 |
| `GET /conversations/{session_id}/messages` | 分页恢复对话历史 |
| `GET/POST /cats` | 列出/新增猫咪档案 |
| `GET /cats/{cat_id}` | 单只猫档案 |
| `GET/POST /caregivers` | 列出/新增照护者 |
| `GET /events?cat_id=...` | 该猫记录，支持分页/日期筛选 |
| `GET /events/{event_id}?cat_id=...` | 记录与照片详情，可核对猫归属 |
| `GET /photos/upload?event_id=...` | 现成上传页面 |
| `POST /photos/upload` | multipart：`event_id` 与 `photo` |
| `GET /reports/vet-summary?cat_id=...` | 默认七天；可传带时区的 `start`、`end` |
| `GET /health` | 服务健康检查 |

不要用旧 `POST /events` 实现连续聊天。HTML 报告和下载目前由前端根据报告 JSON 与照片生成，不是独立 PDF/下载 API。

第一轮示例：

```json
{"request_id":"unique-per-turn","text":"Mochi vomited twice.","source":"simulator"}
```

后续带上返回的 `session_id`，每个新回合生成新的 `request_id`；网络重试同一回合时复用原 ID 和相同请求体。`cat_id` 只在用户明确选择猫时提供；不要默认把所有话写进当前展示的猫。`caregiver_id` 可以来自明确的照护者选择。

必须保留的行为：

- 以返回的 `cat_id`、`cat_name` 为准；后端追问归属时不能自行补默认猫。
- 展示 `speech`；不要把相同 `follow_up` 再显示一遍。
- 支持 `awaiting_cat`、`awaiting_confirmation`、`awaiting_answer`、`completed` 四种状态。
- 处理 `ui_action`：更新档案/照护者、打开报告/历史、开始新观察、归属更正、照片链接、刷新记录。
- 纠错后更新所选猫、缓存的会话归属和照片卡片标题；同一事件保持同一 ID。旧对话原文保留。
- 报告仅在用户主动操作时获取/下载；恢复历史不能自动重复下载。
- 上传后刷新记录照片；手机页面、键盘、加载中、失败重试、空状态需人工验收。
- 处理 404（记录/会话不存在）、409（冲突）、422（输入校验）及 AI 失败；失败不能显示“已保存”。

前端交付物：英文响应式页面、聊天/档案/历史/报告/上传的完整界面、上述状态与错误处理、人工演示录像或验收记录。不必为美化改数据库结构。

## 4. Backend & AWS handoff / 后端与部署同学接手什么

Deploy the entire application behind HTTPS, inject secrets on the server, persist both SQLite and photos, and verify backup/restore. A single-instance deployment is the lowest-change starting point; cloud-native storage needs code adaptation.

部署目标：让队友/评委通过 HTTPS 打开同一套应用，手机可打开上传链接，服务重启后记录和照片仍存在。

### 建议第一阶段：单台 Lightsail Linux 实例

这是根据当前 SQLite + 本地文件架构给出的低改动方案，不代表已部署或已估算费用。

1. 在服务器安装 Python 3.11+，建立虚拟环境并安装 `requirements.txt`；该文件尚未锁定依赖版本。
2. 将前后端一起部署，反向代理提供同域 HTTPS；后端只监听本机地址，使用进程服务管理器开机启动/故障重启。可用 Caddy 或 Nginx。
3. 使用单实例、单应用 worker 起步；不要让多个独立实例各保存一份 SQLite。
4. `data/` 与 `uploads/` 放在持久磁盘，发布代码时不能覆盖数据目录；配置备份，并用 SQLite 备份接口获取一致备份，另备份照片。做一次恢复验证。
5. 配置服务端密钥、模型、公开网址，使用虚构演示数据进行完整验收。
6. 公网演示至少加入入口访问保护和调用限额；当前应用没有账号权限隔离、上传令牌或用户配额。手机上传也需能通过所选访问保护。

配置项：

| 配置 | 用途/注意事项 |
|---|---|
| `CATNANNY_EXTRACTION_PROVIDER` | `rules` 离线；`openai` 真实提取 |
| `OPENAI_API_KEY` | 仅服务端注入，不提交或输出 |
| `OPENAI_MODEL` | 部署时明确设置已验证的模型；不要直接照搬旧示例默认值 |
| `OPENAI_TIMEOUT_SECONDS` | 模型调用超时 |
| `PUBLIC_BASE_URL` | 实际 HTTPS 域名，用于生成上传和照片链接 |
| `CATNANNY_DATA_DIR` | SQLite 数据目录 |
| `CORS_ORIGINS` | 前后端分域才需设置对应来源；同域部署更简单 |

注意：照片目录目前固定为项目根目录 `uploads/`，没有 `CATNANNY_UPLOAD_DIR` 配置。部署同学需保留该目录、挂载持久目录，或先补这个配置；不能只保护数据库。

旧照片地址已以绝对 URL 保存到数据库。改 `PUBLIC_BASE_URL` 只影响后续生成的链接；迁移旧数据时需备份后另行转换旧 localhost 地址，或直接用新的虚构演示数据。手机访问电脑的 localhost 不能打开电脑上的服务。

服务进程必须在启动时加载环境变量；本地可使用 `--env-file .env`，云端由服务管理器/密钥机制注入。仅创建一个配置文件不会保证服务读取它。

### 后续云原生阶段：需要额外改造

若团队选 App Runner 等临时文件系统的运行环境，先将照片改为 S3，并将 SQLite 换为共享的持久数据库，例如 RDS PostgreSQL。当前代码直接使用 SQLite SQL，不能只替换一个数据库 URL；事务、迁移、查询和照片更正需要一起适配并重新测试。

真实邮件可再接 SES；短信使用相应 AWS 消息服务并单独验证投递。它们不是当前聊天页面已经实现的能力。

暂不需要为了演示同时引入所有云服务。先完成稳定可访问的单实例版本，再决定是否增加 S3、云数据库和通知。

AWS 同学优先读：`app.py`、`requirements.txt`、`catnanny/config.py`、`storage/database.py`、`storage/repositories.py`、`services/photo_service.py`、`adapters/openai_responses.py`、`scripts/initialize_core.py`。当前未提供 Dockerfile、基础设施模板或完整部署流水线。

AWS 交付物：部署/回滚操作说明、环境变量模板（无密钥）、HTTPS 地址、进程托管配置、持久目录规划、数据库与照片备份恢复步骤、访问保护和基本用量限制、端到端验收结果。

## 5. Acceptance / 团队联调验收

1. 新建/切换两只猫，声明照护者；不说猫名时正确追问。
2. 连续描述症状，回答问题；只生成当前一条观察，刷新后恢复。
3. 请求上传链接，用手机上传照片，回到对应记录看到照片。
4. 说“no actually it is for jeremy”；未知猫确认后创建，当前事件和照片一起改归，无重复、无串猫。
5. 主动请求七天报告，表格与下载文件包含正确照片。
6. 重启服务，再查看会话、记录、图片均保留。
7. API 失败时前端可重试且不重复写入；没有密钥出现在前端/仓库/日志。

## 6. Documentation and Alexa+ scope / 文档优先级与比赛边界

实时 `/openapi.json` + 当前 schema 作为字段契约；本文与 `LANGUAGE_WORKFLOWS.md` 作为当前行为说明。
Use the reading map above as the current documentation set. Obsolete Day 1 and single-cat documents have been retired; they are not required to run or understand this release.

Alexa+ 允许模拟体验替代路径；AWS 部署不是该路径的强制条件。若参加 AWS Builder 小挑战，需另外说明实际使用的 AWS 工具/服务。真实 Alexa 接入与网站发布是两个不同任务；云端上线不等于 Alexa 已接入。

参考：

- [比赛官方规则](https://amazonappdev2026.devpost.com/rules)
- [Lightsail 磁盘与备份](https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-faq-block-storage.html)
- [App Runner 临时存储与无状态设计](https://docs.aws.amazon.com/apprunner/latest/dg/develop.html)
- [App Runner 密钥环境变量](https://docs.aws.amazon.com/apprunner/latest/dg/env-variable.html)



