# nss-cli 重构设计 v2：流程简化 + QA 过程证据 + 双端后端

日期：2026-06-22
状态：待用户评审（设计阶段，暂不改码）
背景：基于用户对"提交方式 + 记录信息"的最新决策

## 一、产品决策（用户最新确认）

1. **TUI 只保留 init + report**，去掉 submit（report 一步完成生成报告+记录哈希+签名定版）
2. **时间语义**：开始时间 = init 时间；提交时间 = report 时间
3. **核心变化**：教师端"查看报告"展示的不是报告正文，而是**实验过程中的 QA 对话**（学生与 AI 的问答）——证明学生真在平台逐步做实验
4. **不再需要** final_report_markdown
5. **PDF 仅供阅读**，不参与任何验证逻辑
6. **后端拆两端**：教师端（需密码）+ 学生端（不需密码，上传 PDF 用）
7. 教师端表格新增"查看报告"列

## 二、新流程

```
① init    建实验目录 + README + 调后端记录【开始时间】（学生信息此时已配置）
② 做实验  和 AI 对话，AI 按教学脚本带做（对话即 QA，后续可提取）
③ report  采集代码哈希 + 提取实验过程 QA → 上传后端 + 生成 HMAC 签名定版
          （report 时间 = 提交时间 = 定版时间）
```
去掉 submit。report 一步到位。

## 三、记录的信息

| 记录项 | 来源 | 说明 |
|--------|------|------|
| 姓名、学号 | 配置/环境变量 | 身份 |
| 实验ID、run_id | 系统生成 | 关联 |
| **init 时间** | init 时后端记录 | 开始证据 |
| **report 时间** | report 时后端记录 | 提交/定版证据 |
| 代码文件哈希 | collectFileEvidence | 辅助（不进签名，见下） |
| HMAC 签名 | 后端生成 | 防伪核心 |
| **实验过程 QA** ⭐ | report 时从 session 提取 | 证明真在平台逐步做 |
| ~~final_report_markdown~~ | — | **移除** |

## 三点五、哈希与签名设计（核心：只锁 QA）

用户决策：**evidence_hash 只锁实验过程 QA 对话**，不锁代码文件（因为允许用 AI 生成代码，重点是过程）。

```
evidence_hash = SHA256({ "qa_transcript": 实验过程QA对话 })
signature      = HMAC-SHA256(服务端密钥, "run_id : evidence_hash : report时间")
```

**这层验证什么**：保证学生提交的那段 QA 对话**事后不能被篡改**、且确实是本平台本人本次产生的。

**这层验证不了什么**（必须知道的边界）：
- 不能判断 QA 是认真做实验还是随便敷衍几句。
- "学生是否真懂、是否认真做" 需要**老师看 QA 人工判断**。

所以"验证学生真做了实验" = 哈希签名（保证QA真实未改）+ 老师看QA（判断够不够认真）。两层配合。

## 四、QA 采集方案（调研已确认可行）

调研结论（基于 explore 子代理对 nss-cli-agent 的代码调研）：

- session 消息存在 sync context：`message[sessionID]`（元信息含 role）+ `part[messageID]`（文本在 type==="text" 的 part.text）
- onReport 闭包内可访问 `sync` / `sdk` / `route`（app.tsx:385/393/397）
- 取当前 sessionID：`route.data.type === "session"` → `route.data.sessionID`
- 取完整消息：SDK `sdk.client.session.messages({ sessionID, limit })`（最权威，不受 store 100 条裁剪影响）
- role 区分：小写 `user` / `assistant`
- **现成工具**：`util/transcript.ts` 的 `formatTranscript(session, messages)` 直接把对话渲染成 `## User` / `## Assistant` 的 Markdown

落地：report 时调 `sdk.client.session.messages` 取当前 session 全部消息 → 用 formatTranscript 格式化成 QA 文本 → 随证据上传后端。

**障碍/注意**：
1. report 必须在会话路由里执行（学生得先和 AI 对话过，有 session）。若在 home 页执行 report，没有 session → 需提示学生"请先和 AI 做实验"。
2. 默认 limit 100，需要时传更大值。
3. QA 可能含敏感内容，本期先存全文（后续可考虑只存哈希+摘要）。

## 五、后端拆两端

| 端 | 路径 | 鉴权 | 功能 |
|----|------|------|------|
| 教师端 | `/` 或 `/teacher` | **需密码**（如 HTTP Basic 或简单口令） | 表格、筛选、验证签名、查看报告(=QA) |
| 学生端 | `/student` | 不需密码 | 上传 PDF（仅阅读，不验证） |

数据模型变更（runs 表）：
- 移除/停用 `final_report_md`
- 新增 `qa_transcript TEXT`（实验过程 QA）
- 新增 `init_at TEXT`（init 时间，区别于 server_started_at 的语义）
- 新增 `pdf_path TEXT` 或 PDF 存储引用（学生端上传）

教师端鉴权：环境变量 `NSS_TEACHER_PASSWORD`，无密码访问教师端返回 401。

## 六、教师端表格

列：姓名 ｜ 学号 ｜ 实验 ｜ 状态 ｜ 提交编号 ｜ 开始时间(init) ｜ 提交时间(report) ｜ 证据哈希/签名 ｜ **查看报告(QA)** ｜ 操作

"查看报告"点开 → 弹出/展开该 run 的 `qa_transcript`（学生与 AI 的对话过程）。

## 七、实施优先级（建议分阶段，避免一次改太大）

### 阶段 A：流程与时间语义（前端为主）
1. TUI 去掉 submit，report 合并签名定版
2. init 调后端记录开始时间
3. 时间语义调整

### 阶段 B：QA 采集（前后端）
4. report 时提取 session QA（formatTranscript）并上传
5. 后端存 qa_transcript，移除 final_report_md
6. 教师端表格加"查看报告(QA)"列

### 阶段 C：双端拆分
7. 教师端加密码鉴权
8. 学生端 PDF 上传页（仅阅读）

## 八、待确认问题
- 教师端密码用什么方式（HTTP Basic / 登录页 / 固定口令环境变量）？
- 学生端 PDF 上传后，在教师端哪里展示/下载？
- init 没有 session、也没和 AI 对话，report 时如果学生根本没和 AI 互动（QA 为空）怎么处理？（建议：QA 为空时提示学生"请先和 AI 做实验"）

## 九、一句话总结
流程简化成 init+report；report 时把"代码哈希+实验过程QA"一起签名上传；教师端（需密码）能看每个学生的真实做题对话过程，PDF 仅供阅读不参与验证。核心是用"过程QA"证明学生真在平台逐步做实验。
