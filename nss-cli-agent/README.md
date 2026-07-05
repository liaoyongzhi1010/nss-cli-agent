# NSS CLI Agent

基于 [opencode](https://github.com/anomalyco/opencode) 二次开发的 CLI Agent，面向**《计算机安全导论》课程实验教学 + 防作弊**场景。学生用命令行做实验，AI 逐步引导教学；实验过程（师生 QA 对话）自动上报证据后端并签名定版，教师在控制台查验。

产品定位：**鼓励学生用 AI 做实验，但要求真正逐步参与**。防的是"一句话甩给 AI 做完"，不是防用 AI。

## 组成

| 组件 | 说明 | 目录 |
|------|------|------|
| **CLI（nss-cli）** | 学生用的命令行工具，已发布到 npm | `packages/opencode` |
| **证据后端** | 记录实验证据、QA 签名、教师/学生双端 | [`../nss-evidence-server`](../nss-evidence-server) |

## 快速开始（学生）

```bash
# 1. 安装（跨平台：Windows / macOS / Linux）
npm install -g nss-cli-agent

# 2. 首次配置学生信息（自动记住，之后无需再设）
export NSS_STUDENT_NAME="张三"
export NSS_STUDENT_ID="20240001"
export NSS_EVIDENCE_SERVER="http://8.152.219.229"   # 证据后端地址

# 3. 启动
nss-cli
```

> 命令是 `nss-cli`（不是 `nsscli`）。需要 Node.js 18+。

## 端到端流程

### 学生侧：做实验 → 生成报告

1. 启动 `nss-cli`，输入 `/lesson` 打开实验菜单
2. **init**：选择实验（如 `crypto-basic`），系统创建实验目录
3. `cd` 进实验目录，重新启动 `nss-cli`，直接和 AI 对话做实验
   - AI 一次只走一步，每步抛出问题或动手要求后**停下等你回应**
   - 第 3 步 AI 会在实验目录**真实写出 `solution.py`** 等代码文件
4. 做完后 `/lesson` → **report**：自动采集代码 → 提取 QA 对话 → 上报后端签名 → 生成 `report/` 文件夹（`report.md` + `report.tex`）
5. （可选）`report.tex` 上传 [Overleaf](https://www.overleaf.com)（编译器选 **XeLaTeX**）渲染 PDF，再到 `http://<后端>/student` 按学号上传

### 教师侧：查验证据

1. 浏览器打开后端地址（如 `http://8.152.219.229/`）→ 登录（默认 `admin` / `nsscli2026`）
2. 表格按姓名/学号/实验/状态筛选，**签名自动校验**（✅ 已验证 / ⚠️ 签名无效）
3. 点「查看 QA」看学生与 AI 的完整实验对话，判断是否认真参与
4. 点「查看 PDF」下载学生上传的报告

## 验证模型（两层）

1. **技术层（哈希 + 签名）**：`evidence_hash = SHA256(qa_transcript)`，`signature = HMAC-SHA256(密钥, "run_id:evidence_hash:提交时间")`
   - 只锁 **QA 对话**，不锁代码文件（允许用 AI 生成代码，重点是过程）
   - 保证 QA 提交后不可篡改
2. **人工层（教师看 QA）**：技术层无法判断 QA 是认真做还是水的——这要教师在面板看对话内容判断

> PDF 报告仅供教师阅读，**不参与任何验证逻辑**。

## 实验清单

8 个模块 × 3 难度（基础 / 进阶 / 挑战）= 24 个实验，定义见 [`src/labs/manifest.json`](packages/opencode/src/labs/manifest.json)，每个实验的强互动教学脚本见 [`src/labs/lessons.ts`](packages/opencode/src/labs/lessons.ts)。

| 模块 | 基础 | 进阶 | 挑战 |
|------|------|------|------|
| 密码学（含 PKI/TLS） | crypto-basic | crypto-inter | crypto-adv |
| Web 安全 | web-sec-basic | web-sec-inter | web-sec-adv |
| 操作系统安全 | os-sec-basic | os-sec-inter | os-sec-adv |
| 数据库安全 | db-sec-basic | db-sec-inter | db-sec-adv |
| 软件安全 | sw-sec-basic | sw-sec-inter | sw-sec-adv |
| 网络安全 | net-sec-basic | net-sec-inter | net-sec-adv |
| 可信计算（TPM/TCM） | tpm-basic | tpm-inter | tpm-adv |
| 机密计算（TEE：OP-TEE on QEMU） | tee-basic | tee-inter | tee-adv |

## 环境变量

| 变量 | 说明 | 默认 |
|------|------|------|
| `NSS_STUDENT_NAME` | 学生姓名 | 无（首次必设） |
| `NSS_STUDENT_ID` | 学生学号 | 无（首次必设） |
| `NSS_EVIDENCE_SERVER` | 证据后端地址（可覆盖默认线上后端） | `http://8.152.219.229` |

首次设置后会存入 `~/.config/nss-cli/student.json`，之后无需再设。

## 开发

```bash
cd packages/opencode
bun install
bun dev                              # 本地启动交互式 TUI

# 测试
bun test test/labs/lessons.test.ts   # 实验脚本测试
```

构建与发布见 [`packages/opencode/script/build.ts`](packages/opencode/script/build.ts) 和 `publish.ts`。构建产物是主包 `nss-cli-agent` + 12 个平台子包（macOS/Linux/Windows × arm64/x64 及 baseline/musl 变体），学生 `npm i -g nss-cli-agent` 后 postinstall 按平台自动选装对应子包。

## 与 opencode 的关系

- **底座**：复用 opencode 的 LLM 调度、TUI 交互、文件操作、bash 执行等核心能力
- **定制**：面向课程实验的引导式教学（`src/labs/lessons.ts`）+ 证据采集签名（`src/cli/cmd/tui/component/lab-evidence.ts`）
- **品牌**：命令为 `nss-cli`，包名为 `nss-cli-agent`

## 项目背景

西安电子科技大学"基于玄知大模型的《计算机安全导论》实验教学智能体与工具链建设"教改项目（AI 赋能课程改革，重点项目，2026）交付物之一。
