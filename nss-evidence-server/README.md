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
| 教师端 | `/`、`/api/runs`、`/runs/{id}`、`/runs/{id}/verify`、`/runs/{id}/pdf`(下载)、`DELETE /runs/{id}` | **需密码**（见下） | 看表格、查 QA、验证签名、下载 PDF、删除 |
| 学生端 | `/student`、`POST /runs/start`、`POST /runs/{id}/finalize`、`POST /runs/{id}/pdf`(上传) | 无需密码 | nsscli 自动上报；学生上传 PDF |

**学生端不是网页**：学生用 `nsscli` 命令行做实验，证据由 nsscli 自动上报。`/student` 网页只用于学生**额外上传 PDF 报告**。

## 教师端密码怎么工作

用的是 **HTTP Basic Auth**，密码不写在任何前端代码里：

1. 启动服务器时设环境变量 `NSS_TEACHER_PASSWORD`（只在服务器端）。
2. 教师打开教师端页面时，**浏览器自动弹出登录框**，密码填这个环境变量的值（用户名随意）。
3. 浏览器把凭据放进 `Authorization` 头发给后端，后端用 `secrets.compare_digest` 比对。

- 未设 `NSS_TEACHER_PASSWORD` 时，教师端**开放无密码**（方便本地开发）。
- ⚠️ **HTTP Basic 凭据是 base64 编码而非加密**。公网部署**必须套 HTTPS**（如 nginx/caddy 反代加证书），否则密码会明文暴露。内网/本地教学可不强制。

## 环境变量

| 变量 | 说明 | 默认 |
|------|------|------|
| `NSS_EVIDENCE_SECRET` | HMAC 签名密钥（必改） | `dev-secret-change-me` |
| `NSS_EVIDENCE_DB` | SQLite 数据库路径 | `data/evidence.db` |
| `NSS_EVIDENCE_PDF_DIR` | PDF 存储目录 | `data/pdf` |
| `NSS_TEACHER_PASSWORD` | 教师端密码；未设则教师端开放 | （空） |

## 运行

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

NSS_EVIDENCE_SECRET=change-me \
NSS_EVIDENCE_DB=data/evidence.db \
NSS_EVIDENCE_PDF_DIR=data/pdf \
NSS_TEACHER_PASSWORD=老师密码 \
  .venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000
```

## 教师使用

1. 浏览器打开 `http://<host>:8000/`，在弹框输入 `NSS_TEACHER_PASSWORD` 设的密码。
2. 表格按姓名/学号/实验/状态筛选，列含：开始时间、提交时间、证据哈希/签名、**查看报告(QA)**、操作。
3. 点 **查看 QA** 看学生与 AI 的完整实验对话（空对话显示"无对话记录"）。
4. 点 **PDF**（若学生上传过）下载报告；点 **验证** 校验签名有效性。

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

# 教师查询 / 验证 / 下载（需密码）
curl -s -u teacher:老师密码 http://127.0.0.1:8000/runs/<run_id>
curl -s -u teacher:老师密码 http://127.0.0.1:8000/runs/<run_id>/verify
curl -s -u teacher:老师密码 http://127.0.0.1:8000/runs/<run_id>/pdf -o report.pdf
```

## 测试

```bash
.venv/bin/pytest -q
```
