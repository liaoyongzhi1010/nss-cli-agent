# NSS Evidence Server

《计算机安全导论》课程实验的证据后端：记录学生实验的"开始/提交时间 + 实验过程 QA 对话"，并用 HMAC 签名定版，供教师查验。

产品定位：**鼓励学生用 AI 做实验，但要求真正逐步参与**。防的是"一句话甩给 AI 做完"，不是防用 AI。

## 验证模型（两层）

1. **技术层（哈希 + 签名）**：`evidence_hash = SHA256({qa_transcript})`，`signature = HMAC-SHA256(密钥, "run_id:evidence_hash:提交时间")`。
   - 只锁 **QA 对话**，不锁代码文件（允许用 AI 生成代码，重点是过程）。
   - 保证 QA 提交后不可篡改、确实由本平台本人本次产生。
2. **人工层（教师看 QA）**：技术层无法判断 QA 是认真做还是水的——这要教师在面板看对话内容判断。

> PDF 报告仅供教师阅读，**不参与任何验证逻辑**。

## 实验与引导教学

实验清单见 `nss-cli-agent/packages/opencode/src/labs/manifest.json`，覆盖 8 个模块 × 3 难度共 24 个实验（密码学/Web/操作系统/数据库/软件/网络/可信计算/机密计算）。每个实验在 `src/labs/lessons.ts` 都有一份**强互动教学脚本**：AI 一次只走一步、每步抛问题或动手要求后停下等学生回应，学生回应后才推进，避免"一句话让 AI 做完"。

## 双端

| 端 | 路径 | 鉴权 | 用途 |
|----|------|------|------|
| 教师端 | `/`、`/api/runs`、`/runs/{id}`、`/runs/{id}/verify`、`/runs/{id}/pdf`(下载)、`DELETE /runs/{id}` | **需登录**（见下） | 看表格、查 QA、验证签名、下载 PDF、删除 |
| 学生端 | `/student`、`GET /api/student/runs`、`POST /student/pdf`、`GET /student/pdf`、`POST /runs/start`、`POST /runs/{id}/finalize` | 无需登录 | nsscli 自动上报；学生按学号查/预览/上传 PDF（以最新提交为准） |

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
2. 表格按姓名/学号/实验/状态筛选，列含：开始时间、提交时间、证据哈希/签名、**报告(PDF)**、操作。
3. **报告(PDF)** 列：学生上传过则显示"查看 PDF"，否则显示"未上传"。
4. **操作** 列：**验证**（校验签名）、**查看 QA**（弹窗显示学生与 AI 的完整实验对话，空对话显示"无对话记录"）。
5. 右上角 **退出登录** 清除会话。

## 学生使用

- 做实验：在终端用 `nsscli`，`/lesson` → init 开始、report 生成并签名上传（自动采集 QA）。可反复重做，**每次以最新一次提交为准**，历史版本在教师端保留。
- report 会在实验目录生成 `report/` 文件夹，内含 `report.md` 和 `report.tex`（ctexart 模板，上传 Overleaf 后将 Compiler 设为 **XeLaTeX** 即可渲染中文 PDF）。
- 交 / 看 PDF（可选）：浏览器打开 `http://<host>:8000/student`，输入**学号**点"查询我的实验"，列出做过的每个实验（以最新提交为准），可**预览当前 PDF** 或选文件**上传/替换**。无需填 run_id、无需登录。

## 端到端流程（本地联调 / 演示）

```bash
# 1. 启动后端（空库）
NSS_EVIDENCE_SECRET=demo NSS_EVIDENCE_DB=data/evidence.db NSS_EVIDENCE_PDF_DIR=data/pdf \
  .venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000

# 2. 学生侧：设学生信息后用 nsscli 做实验（在另一个终端）
export NSS_STUDENT_NAME="张三" NSS_STUDENT_ID="20240001"
export NSS_EVIDENCE_SERVER="http://127.0.0.1:8000"   # nsscli 连哪个后端，默认即此值
nsscli      # /lesson → init → 与 AI 逐步做实验 → /lesson → report

# 3. 教师侧：浏览器 http://127.0.0.1:8000/ 登录 admin/nsscli2026，看记录/QA/PDF

# 4. 重置数据库回空库（清掉所有记录与 PDF）
#    先停后端，再删库与 PDF 目录，然后重新启动
rm -f data/evidence.db && rm -rf data/pdf
```

**测试账号速查**

| 项 | 值 |
|----|----|
| 教师端登录 | `admin` / `nsscli2026`（可用 `NSS_TEACHER_USER`/`NSS_TEACHER_PASSWORD` 覆盖） |
| 学生信息 | 环境变量 `NSS_STUDENT_NAME` / `NSS_STUDENT_ID`（首次后存入 `~/.config/nss-cli/student.json`） |
| nsscli 连后端 | 环境变量 `NSS_EVIDENCE_SERVER`，默认 `http://127.0.0.1:8000` |

## 部署清单（正式给学生用前必做）

1. **换生产密钥/密码**（demo 值泄露=可伪造证据 / 可登教师端）：
   ```bash
   NSS_EVIDENCE_SECRET=$(openssl rand -hex 32)   # 随机长字符串
   NSS_TEACHER_PASSWORD=<你的强密码>
   ```
2. **套 HTTPS**：公网部署用 nginx/caddy 反代加证书，否则登录密码与 Cookie 明文暴露。
3. **学生端指向真实后端**：让学生设置 `NSS_EVIDENCE_SERVER=https://<你的域名>`（否则默认连本地 127.0.0.1，连不上你的服务器）。
4. **持久化数据**：确保 `NSS_EVIDENCE_DB` 与 `NSS_EVIDENCE_PDF_DIR` 指向持久磁盘并做备份。

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

# 学生上传 PDF（无需登录，按学号+实验挂到最新提交）
curl -s -X POST http://127.0.0.1:8000/student/pdf \
  -F "student_id=20240001" -F "exercise_id=crypto-basic" \
  -F "file=@report.pdf;type=application/pdf"

# 学生查询自己的实验 / 预览自己的 PDF（无需登录）
curl -s "http://127.0.0.1:8000/api/student/runs?student_id=20240001"
curl -s "http://127.0.0.1:8000/student/pdf?student_id=20240001&exercise_id=crypto-basic" -o my.pdf

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
