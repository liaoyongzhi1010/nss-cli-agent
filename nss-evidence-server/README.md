# NSS Evidence Server

《计算机安全导论》课程实验的证据后端：记录学生实验的"开始/提交时间 + 实验过程 QA 对话"，并用 HMAC 签名定版，供教师查验。

产品定位：**鼓励学生用 AI 做实验，但要求真正逐步参与**。防的是"一句话甩给 AI 做完"，不是防用 AI。

## 验证模型（两层）

1. **技术层（哈希 + 签名）**：`evidence_hash = SHA256({qa_transcript})`，`signature = HMAC-SHA256(密钥, "run_id:evidence_hash:提交时间")`。
   - 只锁 **QA 对话**，不锁代码文件（允许用 AI 生成代码，重点是过程）。
   - 保证 QA 提交后不可篡改、确实由本平台本人本次产生。
2. **人工层（教师看 QA）**：技术层无法判断 QA 是认真做还是水的——这要教师在面板看对话内容判断。

> PDF 报告仅供教师阅读，**不参与任何验证逻辑**。

## 双端

| 端 | 路径 | 鉴权 | 用途 |
|----|------|------|------|
| 教师端 | `/`、`/api/runs`、`/runs/{id}`、`/runs/{id}/verify`、`/runs/{id}/pdf`(下载)、`DELETE /runs/{id}` | **需登录**（见下） | 看表格、查 QA、验证签名、下载 PDF、删除 |
| 学生端 | `/student`、`POST /runs/start`、`POST /runs/{id}/finalize`、`POST /runs/{id}/pdf`(上传) | 无需密码 | nsscli 自动上报；学生上传 PDF |

**学生端不是网页**：学生用 `nsscli` 命令行做实验，证据由 nsscli 自动上报。`/student` 网页只用于学生**额外上传 PDF 报告**。

## 教师端登录

教师端用**自定义登录页**（暗色科技风，和面板统一），不是浏览器原生弹框：

1. 打开任意教师端地址 → 自动跳转到 `/login` 登录页。
2. 输入账号密码（默认 **admin / nsscli2026**），登录成功后种一个签名 Cookie（有效期 12 小时），即可访问面板。
3. 右上角"退出登录"清除会话。

账号密码可用环境变量覆盖：`NSS_TEACHER_USER`（默认 `admin`）、`NSS_TEACHER_PASSWORD`（默认 `nsscli2026`）。

- Cookie 值是 `HMAC-SHA256(NSS_EVIDENCE_SECRET, "teacher:用户名")`，无密钥无法伪造。
- ⚠️ 公网部署**必须套 HTTPS**（如 nginx/caddy 反代加证书），否则登录密码与 Cookie 会明文暴露。内网/本地教学可不强制。

## 环境变量

| 变量 | 说明 | 默认 |
|------|------|------|
| `NSS_EVIDENCE_SECRET` | HMAC 签名密钥（必改，同时用于会话 Cookie） | `dev-secret-change-me` |
| `NSS_EVIDENCE_DB` | SQLite 数据库路径 | `data/evidence.db` |
| `NSS_EVIDENCE_PDF_DIR` | PDF 存储目录 | `data/pdf` |
| `NSS_TEACHER_USER` | 教师端用户名 | `admin` |
| `NSS_TEACHER_PASSWORD` | 教师端密码 | `nsscli2026` |

## 运行

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

NSS_EVIDENCE_SECRET=change-me \
NSS_EVIDENCE_DB=data/evidence.db \
NSS_EVIDENCE_PDF_DIR=data/pdf \
NSS_TEACHER_USER=admin \
NSS_TEACHER_PASSWORD=nsscli2026 \
  .venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000
```

## 教师使用

1. 浏览器打开 `http://<host>:8000/`，自动跳到登录页，输入 **admin / nsscli2026**。
2. 表格按姓名/学号/实验/状态筛选，列含：开始时间、提交时间、证据哈希/签名、**查看报告(QA)**、操作。
3. 点 **查看 QA** 看学生与 AI 的完整实验对话（空对话显示"无对话记录"）。
4. 点 **PDF**（若学生上传过）下载报告；点 **验证** 校验签名有效性；右上角 **退出登录**。

## 学生使用

- 做实验：在终端用 `nsscli`，`/lesson` → init 开始、report 生成并签名上传（自动采集 QA）。
- 交 PDF（可选）：浏览器打开 `http://<host>:8000/student`，填 report 时得到的提交编号 `run_id` + 选 PDF 上传。

## 关键 API

```bash
# 开始一次实验（nsscli 自动调用）
curl -s -X POST http://127.0.0.1:8000/runs/start \
  -H 'content-type: application/json' \
  -d '{"student_name":"张三","student_id":"20240001","exercise_id":"01-crypto-basic","computer":{}}'

# 定版：上传 QA + 签名（nsscli 自动调用）
curl -s -X POST http://127.0.0.1:8000/runs/<run_id>/finalize \
  -H 'content-type: application/json' \
  -d '{"qa_transcript":"## 学生\n...\n\n## AI\n..."}'

# 学生上传 PDF（无需密码）
curl -s -X POST http://127.0.0.1:8000/runs/<run_id>/pdf \
  -F "file=@report.pdf;type=application/pdf"

# 教师查询 / 验证 / 下载（需先登录拿 Cookie）
curl -s -c ck.txt -X POST http://127.0.0.1:8000/login -d "username=admin&password=nsscli2026"
curl -s -b ck.txt http://127.0.0.1:8000/runs/<run_id>
curl -s -b ck.txt http://127.0.0.1:8000/runs/<run_id>/verify
curl -s -b ck.txt http://127.0.0.1:8000/runs/<run_id>/pdf -o report.pdf
```

## 测试

```bash
.venv/bin/pytest -q
```
