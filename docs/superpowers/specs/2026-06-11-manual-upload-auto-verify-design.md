# 手动上传 + 后端自动验证 设计文档

日期：2026-06-11
范围：nss-cli-agent（实验动作菜单）+ nss-evidence-server（验证后端与教师面板）

## 背景与目标

《计算机安全导论》课程实验防作弊证据系统。学生通过 nsscli 完成实验并生成报告，提交到证据后端留底；教师可在面板核验报告真伪。

核心模型：**学生可以编辑本地 `report.md` 正文，但不能伪造服务器端的证据记录与签名。** 服务器使用 HMAC-SHA256 对 `run_id:evidence_hash:server_submitted_at` 签名。

本次目标：把"生成报告"与"上传报告"分开为**手动**两步，并让后端能在最终上传时**自动验证**报告真伪、检测篡改，教师面板以 ✅/❌ 徽章展示结论。

## 动作菜单：init / report / submit 三步

1. **init**：创建 `序号-exerciseID/` 文件夹 + `README.md`。不问学生信息、不连后端。（保持现状）
2. **report**：
   - 问学生姓名/学号
   - 调 `POST /runs/start` 拿 `run_id`，存入 `.nss/evidence.json`
   - 本地写 `report.md` **骨架**（学生信息、实验开始时间，无签名块）
   - **不签名、不锁定文件哈希**。学生随后自由写代码、改报告。
3. **submit**（新增，手动触发，学生做完实验后）：
   - 读取学生本地最终的 `report.md` 全文
   - 采集**最终**文件哈希（`collectFileEvidence`）
   - 调 `POST /runs/{id}/finalize` 提交最终报告 + 文件哈希
   - **后端首次生成签名**，写入签名块，返回验证结论（✅）展示给学生
   - 此后再改签名块/代码文件 → 教师面板核验判 ❌

### 关键修正：签名只在 submit 阶段产生
根本原因（旧设计漏洞）：report 阶段就签名，会在文件还要变化时锁定哈希，导致认真做实验的学生在 submit 时被误判篡改。
修正：report 不签名，只 start + 写骨架；签名在 submit 时一次性产生。认真做实验 = 文件正常演进 → submit 定版 → ✅；只有 submit **之后**改签名块/代码才算篡改。

## 后端能力

### 1. `POST /runs/{run_id}/finalize`
请求体：
```json
{ "final_report_markdown": "...", "files": [{"path","sha256","size"}] }
```
后端处理（首次定版 + 签名）：
- 校验 run 存在且 `status = active`、`verify_status` 为空（未定版）。若已定版 → 返回"已定版，请重交"（见漏洞4处理）
- 计算 `evidence_hash = sha256_json({final_report_markdown, files})`
- 生成签名 `signature = sign(run_id, evidence_hash, server_submitted_at)`
- 把签名块写回返回值（供 nsscli 写入本地 report.md）
- 写入 `final_report_md`、`evidence_hash`、`signature`、`server_submitted_at`、`verify_status = "verified"`、`verified_at`

注意：finalize 是定版动作，本身一定 verified（签名此刻才生成）。"tampered" 只可能在**之后**教师核验时发现（学生改了已签名的 report.md / 代码文件）。

### 跨实验/冒用防护
finalize 时校验：report.md 中若已含签名块，其 run_id 必须等于本 run_id 且属于本学生本实验，否则拒绝（防止学生复制他人或他实验的签名块）。

### 2. `GET /runs/{run_id}/verify`
教师实时核验：
- 重算 DB 记录 HMAC，确认 `signature_valid`
- 若教师上传了学生当前的 report.md，提取签名块与 DB 逐字段比对、重采文件哈希比对 → 输出 verified / tampered + `detail`

### 3. 教师面板
- 状态列改为徽章：✅已验证 / ❌被篡改 / 📝已留底（report 完成未 submit）/ 🗑已删除
- 详情展示 `verify_detail` 差异明细
- 默认只看 `active`，可切换 all / superseded / deleted

## 数据模型变更（runs 表新增列）
- `final_report_md TEXT`
- `verify_status TEXT`（null / verified / tampered）
- `verified_at TEXT`
- `verify_detail TEXT`（JSON）
- `status TEXT NOT NULL DEFAULT 'active'`（soft-delete：active / superseded / deleted）

向后兼容：用 `ALTER TABLE ... ADD COLUMN`（IF NOT EXISTS 逻辑用 try/except）。

## 软删除策略

**核心原则：所有数据不物理删除，通过 `status` 字段标记。**

- `active`：当前有效的提交记录
- `superseded`：学生对同一实验重新执行 report 时，旧的 run 记录自动标记为 superseded（被取代），新 run 为 active。保留全部历史留底。
- `deleted`：教师/管理员主动删除的记录（面板提供"删除"按钮，实际只改 status）

行为规则：
1. `POST /runs/start`：用 SQLite 事务（`BEGIN IMMEDIATE`）原子地：若该学生+实验已有 `active` 的 run，先将其标为 `superseded`，再创建新 run（status=active）。避免并发产生两条 active。
2. 面板默认只展示 `status = active`，提供筛选切换查看 `all` / `superseded` / `deleted`
3. `DELETE /runs/{id}`：不物理删除，仅设 `status = deleted`
4. 历史版本在面板详情中可展开查看（同一学生+同一实验的所有历史 runs）

## 重复 submit 策略（漏洞4）

首次 finalize 后该 run 锁定（`verify_status` 已写）。学生若 submit 后还要改：
- 重新走 **report** 开一个新 run（旧 run 自动 `superseded`），再 submit
- 教师面板看到的 active 始终是最新定版
- 不允许对同一已定版 run 重复 finalize（返回提示引导重新 report）
- 全部历史 run 保留可追溯

## 签名块解析
`report.md` 中的签名块格式（由 `evidenceAppendix` 生成）：
```
## 服务器证据签名
- 提交编号：<run_id>
- 服务器提交时间：<server_submitted_at>
- 证据哈希：<evidence_hash>
- 服务端签名：<signature>
```
后端用正则提取四个字段。提取失败 → tampered（签名块被删/改）。

## 数据流
```
init   → 本地文件夹+README
report → start(拿 run_id) → 写本地 report.md 骨架（不签名）
[学生写代码、改报告，文件自由演进]
submit → finalize(最终 report.md + 文件哈希) → 后端生成签名 → verify_status=verified + 写回签名块
[若 submit 后再改签名块/代码]
教师   → 面板看徽章 / 点 verify 重算 HMAC + 比对当前文件 → 检出 ❌tampered
```

## 测试
- 后端 pytest：finalize 正常→verified；改签名块→tampered；改文件哈希→tampered；缺 submit→404；verify 接口返回正确。
- nsscli evidence-client：submit 函数读取 report.md、调 finalize、返回结论（临时 bun 脚本验证）。

## 非目标（YAGNI）
- 不做网页拖拽上传
- 不做自动上传（全手动）
- 不做学生鉴权/登录
