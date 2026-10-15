# Demo and acceptance / 演示与验收用例

Use the offline quick start in [team onboarding](TEAM_HANDOFF_CURRENT_CN.md).
使用新的浏览器会话/新观察，避免把演示输入误认为已有记录的更新。以下不会发送真实短信或邮件。

## Main story / 主演示（建议小于三分钟）

| Step | Typed message or action / 输入或操作 | Expected / 预期 |
|---|---|---|
| 1 | “Mochi vomited food twice.” | Identify Mochi, create one observation and ask for missing details |
| 2 | Answer the actual questions: “No blood.” / “Energy is normal.” | Update the same event until required details are complete |
| 3 | “Send me the photo link.”; open the card and upload a JPEG/PNG/WebP | The photo belongs to that event; label the card as simulated delivery |
| 4 | “No, actually it is for Jeremy.” | If Jeremy is unknown, ask whether to create and move this observation |
| 5 | “Yes” when confirmation is requested | Same event and photo move to Jeremy; original time and details stay |
| 6 | “Show me Jeremy's care report for the last 7 days.” | Requested seven-day table contains the event and photo |
| 7 | Select Mochi and view its log | The corrected event is absent; unrelated observations remain |

If Jeremy already exists, the explicit correction applies directly; the confirmation step is not required.
此前对话仍可显示原始 Mochi 发言，这是历史原文；判断最终归属看当前记录与报告。

Narration / 英文讲解：
“Cat Nanny helps shared households turn scattered care conversations into reliable records. This demonstration shows context, follow-up questions, correction of a mistaken cat name, event-linked photos and a report requested by the caregiver. It is a web-based Alexa+ experience simulation; real Alexa and message delivery are not connected.”

## Additional cases / 补充用例

| Case / 用例 | Expected / 预期 |
|---|---|
| New conversation: “My cat vomited twice.” then “Mochi.” | Ask for cat first; preserve symptom description when subject is confirmed |
| “Add a cat named Jeremy.” | Create/select profile, not a health event |
| “I am Sam.” then log a new observation | Attribution uses Sam; self-declaration does not authenticate identity |
| Start a new observation: “Jeremy is not eating.” | Appetite flow; answer the time-since-food question in the same session |
| Screenshot regression: “no actually it is for jeremy, vomit today and already saw 6 times in 3 days” | Recognize correction intent; move current observation instead of silently saving to Mochi |
| Decline unknown-cat creation with “No” | Original event and photos retain their original ownership |
| Refresh browser / restart server | Recover saved state and photos; no duplicate event |
| Request standalone report download | Embedded photos visible in the downloaded HTML; no automatic email |

The screenshot case verifies subject correction; it does not promise that all dates/durations in a combined sentence are parsed. Existing details are preserved by the ownership-correction operation.
自然语言日期尚未作为完整时间解析功能实现。

## Automated checks / 自动检查

From the repository root after installing dependencies:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
node --test tests/frontend_behavior.test.cjs
```

Node is optional for running the app. Backend tests use isolated workspace databases and force offline AI; the JavaScript tests use a DOM double, not browser automation.
最近验证：88 项 Python 测试、5 项 JavaScript 测试通过。以后功能变化时以实际输出为准。

| Test file | Coverage / 验证重点 |
|---|---|
| `tests/test_language_actions_and_corrections.py` | Known/unknown target, screenshot phrasing, same event/photo, rollback, cancellation, idempotency |
| `tests/test_profiles_and_identity.py` | Profiles, subject clarification, cat separation, seven-day reports |
| `tests/test_openai_extraction.py` | Mocked Responses integration and structured output errors |
| `tests/test_simulator_flow.py` | Conversation → upload → report |
| `tests/frontend_behavior.test.cjs` | Requested reports, export, subject handling, correction and cache updates |

Paid real-model evaluations are explicit opt-in scripts, not required for cloning or offline tests. See the handoff before running them.
实际布局、手机文件选择和浏览器下载需人工验收。不要把“API 配置已填写”当成模型连通性已经验证。

