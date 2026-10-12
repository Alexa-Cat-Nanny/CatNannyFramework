# Cat Nanny 团队分工、交付物与文档责任 README

这份 README 用于三人协作执行。它定义每个人负责什么、每天交付什么、交付前怎么自测、哪些文档由谁维护，以及集成时应该看哪些接口。

## 1. 总体目标

五天内完成一个可以 demo 的 Cat Nanny MVP：

```text
真实 Alexa 语音记录事件
  -> 后端创建 event_id
  -> 返回追问/危险提示和照片上传链接
  -> 用户手机上传照片
  -> Vet summary 显示事件和照片
  -> MCP simulator 展示 Alexa+ track 的 self-hosted MCP flow
```

项目有两条入口，但共用同一套核心逻辑：

```text
Alexa Custom Skill
  -> services/event_service.py

MCP Server / Simulator
  -> services/event_service.py

services/event_service.py
  -> domain/rules.py
  -> storage/repositories.py
```

## 2. 三人角色总览

### Person A：Alexa Real Voice Owner

目标：让真实 Alexa 或 Alexa Developer Console 可以记录猫咪事件。

负责范围：

```text
Alexa Skill
Interaction Model
Alexa 对话体验
真实语音 demo
```

主要代码：

```text
skill-package/interactionModels/custom/en-US.json
catnanny/alexa_skill/handlers.py
```

主要文档：

```text
docs/DEMO_SCRIPT.md
docs/TEAM_CONTRACT_CN.md 中 Alexa Adapter API 部分
README_CN.md 中 Alexa 使用流程相关段落
```

### Person B：Core + MCP + Simulator Owner

目标：完成健康规则、MCP tools，以及用于 Alexa+ track 的 MCP simulator。

负责范围：

```text
核心健康规则
MCP server/tools
MCP simulator
规则测试
```

主要代码：

```text
catnanny/domain/models.py
catnanny/domain/rules.py
catnanny/mcp_server/tools.py
tests/test_rules.py
```

后续可能新增：

```text
catnanny/web/routes_simulator.py
templates/simulator.html
tests/test_mcp_tools.py
```

主要文档：

```text
docs/ARCHITECTURE.md 中 Core/MCP 部分
docs/TEAM_CONTRACT_CN.md 中 Python Service API 和 MCP Tool API 部分
```

### Person C：DevOps + AWS + Reports Owner

目标：完成照片上传、报告、部署/AWS 方案，以及 AWS Builder mini challenge 支撑。

负责范围：

```text
照片上传
Vet summary / report
本地后端 route
部署和环境变量
AWS Builder 文档
```

主要代码：

```text
app.py
catnanny/storage/database.py
catnanny/storage/repositories.py
catnanny/services/photo_service.py
catnanny/services/report_service.py
```

后续可能新增：

```text
catnanny/services/email_service.py
templates/upload.html
templates/vet_summary.html
.env.example
infra/
docs/AWS_BUILDER.md
```

主要文档：

```text
README.md
docs/ARCHITECTURE.md 中部署/AWS 部分
docs/TEAM_CONTRACT_CN.md 中 Backend API、Photo、Report 部分
```

### 项目协调 Owner

建议由发起人暂时负责：

```text
README_CN.md
README_TEAM_CN.md
docs/TEAM_CONTRACT_CN.md
```

职责：

```text
保持接口名称一致
同步每日交付状态
防止字段名/API 路径被随意改动
组织 Day 5 demo flow
```

## 3. 不要随便改的接口名

为了减少集成摩擦，以下名称默认冻结。确实要改时，必须先同步团队并更新 `docs/TEAM_CONTRACT_CN.md`。

```text
POST /events
GET /photos/upload
POST /photos/upload
GET /reports/vet-summary

log_health_event
get_vet_summary
handle_log_health_event

event_id
event_type
details
follow_up
red_flags
upload_url
```

## 4. 每日交付计划与完成标准

## Day 1：骨架和核心链路

目标：

```text
后端可以创建事件
系统返回 event_id 和 upload_url
照片可以上传并绑定到事件
Vet summary 能看到事件和照片 URL
```

### Person A 交付物

```text
skill-package/interactionModels/custom/en-US.json 初版
Alexa demo 语句初版
```

完成标准：

```text
有 LogHealthEventIntent
有 GetVetSummaryIntent
有 utterance: "log that Mochi threw up"
slot 名称使用 eventType 和 content
```

自测：

```text
确认 en-US.json 是合法 JSON
确认 intent 名称和 slot 名称与契约一致
```

### Person B 交付物

```text
catnanny/domain/models.py
catnanny/domain/rules.py
tests/test_rules.py
```

完成标准：

```text
vomit 缺少 content 会返回 follow_up
vomit has_blood=true 会返回 red_flags
24 小时内第三次呕吐会返回 red_flags
```

自测：

```powershell
python -m pytest tests/test_rules.py
```

### Person C 交付物

```text
POST /events
GET /photos/upload
POST /photos/upload
GET /reports/vet-summary
```

完成标准：

```text
POST /events 返回 event_id
POST /events 返回 upload_url
上传照片后，/reports/vet-summary 能看到 photo URL
```

自测：

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:8000/events" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"event_type":"vomit","details":{"content":"food"},"source":"manual"}'
```

## Day 2：Alexa Adapter、MCP Tool、报告页面

目标：

```text
Alexa handler 可以调用 event service
MCP tools 可以调用 event service
报告页面从 JSON 逐步变成可展示页面
```

### Person A 交付物

```text
catnanny/alexa_skill/handlers.py
handle_log_health_event(slots: dict) -> dict
```

完成标准：

```text
输入 slots 后能创建 event
返回 speech
返回 card_text
返回 data.event_id
返回 data.upload_url
```

自测：

```powershell
python -c "from catnanny.storage.database import init_db; from catnanny.alexa_skill.handlers import handle_log_health_event; init_db(); r=handle_log_health_event({'event_type':'vomit','content':'food'}); print(r); assert 'speech' in r and 'upload_url' in r['data']"
```

### Person B 交付物

```text
catnanny/mcp_server/tools.py
log_health_event(event_type, details)
get_vet_summary()
```

完成标准：

```text
MCP tool 可以创建 event
MCP tool 返回 upload_url
get_vet_summary 能看到刚创建的 event
```

自测：

```powershell
python -c "from catnanny.storage.database import init_db; from catnanny.mcp_server.tools import log_health_event, get_vet_summary; init_db(); e=log_health_event('vomit', {'content':'food'}); s=get_vet_summary(); print(e); print(s); assert 'event_id' in e and s['counts']['total_events'] >= 1"
```

### Person C 交付物

```text
Vet summary HTML 页面
照片 URL 可点击
```

建议新增：

```text
GET /reports/vet-summary.html
templates/vet_summary.html
```

完成标准：

```text
浏览器打开 summary 页面
能看到 Mochi
能看到事件
能点击照片链接
能看到 safety note
```

## Day 3：真实 Alexa 测试与 MCP Simulator

目标：

```text
Alexa Developer Console 可以测试语音事件
MCP simulator 可以调用 MCP tool
```

### Person A 交付物

```text
Alexa Developer Console 中可测试 LogHealthEventIntent
```

完成标准：

```text
输入或说：
ask cat nanny to log that Mochi threw up

后端创建 event
summary 中出现该 event
```

自测：

```text
Alexa Developer Console Test tab 中能看到 response
/reports/vet-summary 能看到新事件
```

### Person B 交付物

```text
Web MCP simulator 初版
```

建议新增：

```text
GET /simulator
POST /simulator/tool-call
templates/simulator.html
```

完成标准：

```text
页面能展示 tools/list
页面能触发 tools/call log_health_event
调用后显示 event_id 和 upload_url
```

自测：

```text
浏览器打开 /simulator
点击或提交 log_health_event
页面显示 event_id
/reports/vet-summary 能看到该事件
```

### Person C 交付物

```text
.env.example
docs/AWS_BUILDER.md 初版
部署方案
```

完成标准：

```text
能解释 PUBLIC_BASE_URL 怎么设置
能解释照片从本地迁移到 S3 的计划
能解释 AWS Builder 里用到哪些服务
```

## Day 4：Demo Polish 与部署能力

目标：

```text
Alexa demo 可录
MCP simulator demo 可录
报告/照片链路稳定
```

### Person A 交付物

```text
真实 Echo 或 Alexa Simulator demo 录制片段
```

完成标准：

```text
视频里能展示用户说话
Alexa 返回 Logged 或 follow_up
后端 summary 中出现事件
```

### Person B 交付物

```text
MCP simulator 录制片段
get_vet_summary tool 可用
```

完成标准：

```text
视频里能展示 tools/list
视频里能展示 tools/call
调用结果包含 event_id 和 upload_url
```

### Person C 交付物

```text
Vet summary 页面稳定
照片链接稳定
S3 或 email report 至少完成一个
```

完成标准：

```text
最终 demo 里照片能打开
summary 能展示照片链接
AWS Builder 文档能说明实际接入或计划接入
```

## Day 5：整合、视频、提交

目标：

```text
完成最终 smoke test
录制 3 分钟英文 demo
整理 Devpost submission
```

### 三人共同交付

```text
最终 demo 视频
最终 README
Devpost 文案
Friction log
Track 和 Mini Challenge 说明
```

最终 smoke test：

```text
1. POST /events 创建事件
2. 上传照片
3. /reports/vet-summary 显示事件和照片
4. Alexa 或 Alexa Simulator 创建事件
5. MCP simulator 创建事件
6. 两个入口创建的事件都出现在 summary 中
```

通过标准：

```text
Alexa Skill 入口可展示
MCP simulator 入口可展示
照片上传可展示
Vet summary 可展示
README 能说明如何运行
```

## 5. 文档责任分配

### Person A 负责维护

```text
docs/DEMO_SCRIPT.md
skill-package/interactionModels/custom/en-US.json
README_CN.md 中 Alexa 相关段落
docs/TEAM_CONTRACT_CN.md 中 Alexa Adapter API 部分
```

### Person B 负责维护

```text
docs/ARCHITECTURE.md 中 Core/MCP 部分
docs/TEAM_CONTRACT_CN.md 中 Python Service API 部分
docs/TEAM_CONTRACT_CN.md 中 MCP Tool API 部分
tests/ 相关说明
```

### Person C 负责维护

```text
README.md
docs/ARCHITECTURE.md 中部署/AWS 部分
docs/AWS_BUILDER.md
.env.example
README_CN.md 中运行方式和报告/照片相关段落
```

### 项目协调 Owner 负责维护

```text
README_CN.md
README_TEAM_CN.md
docs/TEAM_CONTRACT_CN.md
```

职责：

```text
确认接口名没有被随意改动
确认每个人的交付物和测试结果同步
确认最终 demo flow 没有断点
```

## 6. 集成前检查清单

每个人交付前必须回答：

```text
1. 我交付的函数/API 名称是什么？
2. 输入参数或 JSON 长什么样？
3. 输出返回值长什么样？
4. 我用什么测试证明它成功运行？
5. 这个输出是否符合 docs/TEAM_CONTRACT_CN.md？
```

如果答不出来，不进入集成。

## 7. 当前已完成状态

当前已经跑通：

```text
POST /events 创建事件
返回 follow_up
返回 upload_url
照片上传绑定 event_id
/reports/vet-summary 显示事件和照片 URL
```

这意味着 Day 1 后端主链路已经成立。接下来三个人可以基于固定接口并行推进。
