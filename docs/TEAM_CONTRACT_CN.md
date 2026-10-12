# Cat Nanny 三人协作接口与交付契约

这份文档的目的：让三个人并行开发时，不会因为接口名字、输入输出或完成标准不一致而卡住。

原则：

```text
1. 所有人都调用 services 层，不直接跨模块抄逻辑。
2. 每个 deliverable 必须有固定名称、固定输入、固定输出。
3. 每个人交付前至少跑通自己的 smoke test。
4. 集成时优先看这份文档，不临时改接口名。
```

## 1. 统一核心对象

所有模块默认使用同一只 demo cat：

```text
household_id = demo_household
cat_id       = mochi
cat name     = Mochi
```

### Event

事件是整个系统最核心的数据。

最小字段：

```json
{
  "event_id": "evt_e69d3c1fd7e8",
  "cat": "Mochi",
  "type": "vomit",
  "details": {
    "content": "food"
  },
  "follow_up": "Did you see any blood?",
  "red_flags": [],
  "pattern_note": null,
  "upload_url": "http://localhost:8000/photos/upload?event_id=evt_e69d3c1fd7e8"
}
```

### 允许的 event_type

五天 MVP 只承诺这些：

```text
vomit
appetite
litter
energy
medication
meal
```

其中 Day 1-2 必须优先保证：

```text
vomit
appetite
```

### details 约定

`vomit`：

```json
{
  "content": "food",
  "has_blood": false,
  "minutes_after_meal": 10,
  "low_energy": false
}
```

`appetite`：

```json
{
  "status": "not_eating",
  "hours_since_food": 24
}
```

`litter`：

```json
{
  "straining": true,
  "passing_urine": false
}
```

不确定的信息可以不传，规则层会返回 `follow_up`。

## 2. 统一接口清单

### Backend API

这些是 Person A、B、C 都可以调用的 HTTP 接口。

#### POST /events

用途：创建一条猫咪健康事件。

请求：

```json
{
  "event_type": "vomit",
  "details": {
    "content": "food"
  },
  "reporter": "Alex",
  "source": "manual"
}
```

响应：

```json
{
  "event_id": "evt_xxx",
  "cat": "Mochi",
  "type": "vomit",
  "details": {
    "content": "food"
  },
  "follow_up": "Did you see any blood?",
  "red_flags": [],
  "pattern_note": null,
  "upload_url": "http://localhost:8000/photos/upload?event_id=evt_xxx"
}
```

完成标准：

```text
返回 200
返回 event_id
返回 upload_url
事件出现在 /reports/vet-summary
```

#### GET /photos/upload?event_id=evt_xxx

用途：打开手机照片上传页。

完成标准：

```text
页面能打开
页面包含文件选择按钮
页面包含 Upload 按钮
```

#### POST /photos/upload

用途：上传照片并绑定到事件。

字段：

```text
event_id
photo
```

完成标准：

```text
返回 ok: true
照片 URL 出现在 /reports/vet-summary
```

#### GET /reports/vet-summary

用途：生成兽医摘要。

响应最小结构：

```json
{
  "title": "Cat Nanny Vet Summary",
  "cat": "Mochi",
  "counts": {
    "vomit": 1,
    "appetite": 0,
    "total_events": 1
  },
  "timeline": [
    {
      "event_id": "evt_xxx",
      "time": "2026-10-12T19:01:16+00:00",
      "type": "vomit",
      "details": {
        "content": "food"
      },
      "photos": [
        "http://localhost:8000/uploads/events/evt_xxx/photo.jpg"
      ]
    }
  ],
  "safety_note": "Cat Nanny describes observations and does not diagnose. Contact a veterinarian for medical advice."
}
```

完成标准：

```text
能看到最近事件
能看到照片 URL
有 safety_note
```

### Python Service API

内部模块优先调用这些函数。

#### services.event_service.log_health_event()

签名：

```python
log_health_event(
    event_type: str,
    details: dict | None = None,
    reporter: str | None = None,
    source: str = "api",
) -> dict
```

调用者：

```text
app.py
alexa_skill/handlers.py
mcp_server/tools.py
```

返回必须包含：

```text
event_id
cat
type
details
follow_up
red_flags
pattern_note
upload_url
```

#### services.photo_service.save_event_photo()

签名：

```python
save_event_photo(event_id: str, upload: UploadFile) -> Photo
```

返回必须包含：

```text
photo_id
event_id
url
uploaded_at
```

#### services.report_service.build_vet_summary()

签名：

```python
build_vet_summary() -> dict
```

返回必须包含：

```text
title
cat
counts
timeline
safety_note
```

### Alexa Adapter API

Person A 负责。

#### alexa_skill.handlers.handle_log_health_event()

签名：

```python
handle_log_health_event(slots: dict) -> dict
```

输入：

```python
{
    "event_type": "vomit",
    "content": "food",
    "minutes_after_meal": 10,
    "reporter": "Alex"
}
```

输出：

```python
{
    "speech": "Did you see any blood?",
    "card_title": "Add a Cat Nanny photo",
    "card_text": "Add a photo for this event: http://localhost:8000/photos/upload?event_id=evt_xxx",
    "data": {
        "event_id": "evt_xxx"
    }
}
```

完成标准：

```text
slots 能转成 event_service.log_health_event()
返回 speech
返回 card_text
data 里有 event_id 和 upload_url
```

### MCP Tool API

Person B 负责。

#### mcp_server.tools.log_health_event()

签名：

```python
log_health_event(event_type: str, details: dict | None = None) -> dict
```

输出必须和 `/events` 类似：

```text
event_id
follow_up
red_flags
upload_url
```

#### mcp_server.tools.get_vet_summary()

签名：

```python
get_vet_summary() -> dict
```

输出必须和 `/reports/vet-summary` 类似。

完成标准：

```text
web simulator 能调用 MCP tool
调用后能创建 event
event 出现在 vet summary
```

## 3. 每人每日交付计划

## Day 1

### Person A：Alexa

交付物：

```text
skill-package/interactionModels/custom/en-US.json 初版
docs/DEMO_SCRIPT.md 里的 Alexa 语音脚本
```

必须确认：

```text
至少有 LogHealthEventIntent
至少有 utterance: "log that Mochi threw up"
```

自测：

```text
人工检查 en-US.json 是合法 JSON
确认 intent 名称叫 LogHealthEventIntent
确认 slot 名称不要乱改：eventType, content
```

### Person B：Core

交付物：

```text
catnanny/domain/models.py
catnanny/domain/rules.py
tests/test_rules.py
```

必须确认：

```text
vomit 缺少 content 会返回 follow_up
vomit has_blood=true 会返回 red_flags
```

自测：

```powershell
python -m pytest tests/test_rules.py
```

### Person C：Backend Photo/Report

交付物：

```text
POST /events
GET /photos/upload
POST /photos/upload
GET /reports/vet-summary
```

自测：

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:8000/events" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"event_type":"vomit","details":{"content":"food"},"source":"manual"}'
```

通过标志：

```text
返回 event_id
返回 upload_url
上传照片后 vet summary 里能看到 photo URL
```

## Day 2

### Person A：Alexa

交付物：

```text
alexa_skill/handlers.py 可处理 LogHealthEventIntent 的 slots
Alexa response 里包含 speech 和 upload link card_text
```

接口名称不能改：

```python
handle_log_health_event(slots: dict) -> dict
```

自测：

```powershell
python - <<'PY'
from catnanny.storage.database import init_db
from catnanny.alexa_skill.handlers import handle_log_health_event

init_db()
result = handle_log_health_event({"event_type": "vomit", "content": "food"})
print(result)
assert "speech" in result
assert "data" in result
assert "upload_url" in result["data"]
PY
```

通过标志：

```text
输出里有 speech
输出里有 data.event_id
输出里有 data.upload_url
```

### Person B：MCP

交付物：

```text
mcp_server/tools.py 中 log_health_event() 和 get_vet_summary()
```

接口名称不能改：

```python
log_health_event(event_type: str, details: dict | None = None) -> dict
get_vet_summary() -> dict
```

自测：

```powershell
python - <<'PY'
from catnanny.storage.database import init_db
from catnanny.mcp_server.tools import log_health_event, get_vet_summary

init_db()
event = log_health_event("vomit", {"content": "food"})
summary = get_vet_summary()
print(event)
print(summary)
assert "event_id" in event
assert "upload_url" in event
assert summary["counts"]["total_events"] >= 1
PY
```

通过标志：

```text
MCP tool 创建 event
summary 能看到至少一条 event
```

### Person C：Report

交付物：

```text
vet summary HTML 页面
照片 URL 可点击
```

建议新增接口：

```text
GET /reports/vet-summary.html
```

自测：

```text
浏览器打开 /reports/vet-summary.html
能看到 Mochi
能看到 vomit event
能看到 photo link
```

## Day 3

### Person A：Alexa

交付物：

```text
Alexa Developer Console 中能测试 LogHealthEventIntent
```

自测：

```text
在 Test tab 输入：
ask cat nanny to log that Mochi threw up

预期：
后端创建 event
Alexa 返回 follow_up 或 Logged
```

通过标志：

```text
后端 /reports/vet-summary 里出现 Alexa 创建的 event
```

### Person B：MCP Simulator

交付物：

```text
web MCP simulator 页面
展示 tools/list
展示 tools/call log_health_event
```

建议新增：

```text
GET /simulator
POST /simulator/tool-call
```

自测：

```text
浏览器打开 /simulator
点击 log_health_event
页面显示 event_id 和 upload_url
```

通过标志：

```text
simulator 调用后，vet summary 里能看到这个 event
```

### Person C：DevOps

交付物：

```text
.env.example
docs/AWS_BUILDER.md
公网部署计划
```

自测：

```text
README 能解释如何设置 PUBLIC_BASE_URL
docs/AWS_BUILDER.md 能解释 S3 / SES / deployment plan
```

## Day 4

### Person A：Alexa polish

交付物：

```text
真实 Echo 或 Alexa Simulator demo 可录屏
```

通过标志：

```text
可以录到一段语音创建事件的视频
```

### Person B：MCP polish

交付物：

```text
MCP simulator demo 可录屏
get_vet_summary tool 可用
```

通过标志：

```text
视频里能展示 tools/list 和 tools/call
```

### Person C：Report + AWS

交付物：

```text
vet summary 页面可展示照片
email report 或 S3 photo storage 至少完成一个
```

通过标志：

```text
照片不是只存在本地临时状态；demo 能稳定打开图片链接
```

## Day 5

三人共同交付：

```text
3 分钟英文 demo 视频
Devpost submission text
README run instructions
friction log
final smoke test
```

最终 smoke test：

```text
1. 创建 event
2. 上传照片
3. 打开 vet summary
4. Alexa 或 Alexa Simulator 创建 event
5. MCP simulator 创建 event
```

通过标志：

```text
两个入口都能创建事件：
Alexa Skill -> event_service
MCP Simulator -> MCP tool -> event_service

summary 里能看到这些事件。
```

## 4. 集成前检查清单

每个人交付前回答这四个问题：

```text
1. 我交付的函数/API 名称是什么？
2. 输入 JSON 或参数长什么样？
3. 输出 JSON 或返回值长什么样？
4. 我用什么测试证明它跑通？
```

如果这四个问题答不出来，先不要合并。

## 5. 不要改的名字

为了减少集成摩擦，下面这些名字不要随便改：

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

如果必须改，先在组里同步，然后更新这份文档。
