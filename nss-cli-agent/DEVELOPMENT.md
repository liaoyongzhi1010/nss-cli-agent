# NSS CLI Agent 开发记录

## 项目定位

基于 opencode 二次开发的垂直领域 CLI Agent，面向：
1. **可信执行环境（TEE）开发与部署**
2. **《计算机安全导论》课程实验教学**

通过 `npm install -g nss-cli-agent` 发布，学生/开发者运行 `nsscli` 直接使用。

---

## 交互设计决策

### 任务1：TEE 部署开发

**模式：Repo-local skill（泛化的可信执行环境部署）**

ref/opencode-tee 是用 Codex 跑出来的一个成功案例（VisionFive 2 + Keystone），验证了 repo-local skill 模式的可行性。nss-cli-agent 要做的不是只支持这一个场景，而是**泛化为"可信执行环境部署开发"的通用工具**。

核心原则（来自 ref/opencode-tee 验证的经验）：
- skill 不是万能 prompt，是**工作流路由器**（什么时候用什么脚本，出错怎么排查）
- 真正的工作由 `scripts/` shell 脚本做
- 状态全部落盘（manifest.json + docs/status.md），不靠对话记忆
- 证据驱动：每次验证必须有日志证据，不靠假设

nss-cli-agent 在此场景的作用：
- 提供 opencode 底座能力（LLM + TUI + bash + 文件操作）
- 系统 prompt 让 agent 天然理解 TEE/安全概念
- 内置 `env-doctor` skill 做宿主机环境自检
- 用户在任意 TEE 项目目录下启动 nsscli，通过 repo-local skill 驱动工作流

### 任务2：课程实验

**模式：TUI 命令驱动（/lesson 选择实验 → /init 初始化 → 对话完成 → /verify 验收）**

交互流程：
```
学生运行 nsscli
  → /lesson                          # 弹出实验列表（类似 /model 的选择界面）
  → 选择一个实验，如 "密码学基础 - RSA 实现与验证"
  → /init                            # 在当前目录初始化该实验
     生成：
     - README.md（实验描述、目标、验收要求）
     - data/（实验数据、测试向量等）
     - scripts/（验证脚本）
     - docker-compose.yml（如需容器环境）
  → 学生继续在 nsscli 中对话完成实验
     "帮我理解 RSA 的密钥生成过程"
     "这段代码中 mod_exp 函数为什么这么写"
  → /verify                          # 运行验收（测试 + 证据采集）
  → /report                          # 生成结构化报告草稿
```

关键设计：
- `/lesson` 类似 `/model`，弹出 TUI 选择列表，按模块分组
- `/init` 在**当前目录**生成实验所需的所有文件，学生可以看到、修改、理解
- 初始化后学生继续在 nsscli 对话，agent 基于当前目录的 README.md 和实验上下文引导
- `/verify` 和 `/report` 是硬命令，保证验收一致性

八类实验模块（来自课程文档）：
1. 密码学基础（含 PKI/TLS）
2. Web 安全（SQLi/XSS/CSRF）
3. 操作系统安全（Set-UID/环境变量注入/TOCTOU）
4. 数据库安全（注入/权限/审计）
5. 软件安全（缓冲区溢出/格式化字符串/ASLR/Canary/NX）
6. 网络安全（嗅探/伪造/DNS/TCP/防火墙/VPN）
7. 可信计算（TPM/TCM：PCR/度量/密封解封/远程证明）
8. 机密计算（TEE：OP-TEE on QEMU/CA-TA 链路/共享内存）

每类模块按**基础—进阶—挑战**三层递进。

### 实验包载体

**内置在 npm 包中**

- 装了就有，离线可用
- 学生不需要额外网络/配置
- 更新通过 `npm update nss-cli-agent` 完成
- 结构：`packages/opencode/src/labs/<module>/<exercise>/` 下按模块组织
- 每个 exercise 包含：模板文件、数据、验证脚本、报告模板

---

## 已完成改动

| 领域 | 内容 |
|------|------|
| 品牌 | CLI 命令 `nsscli`，包名 `nss-cli-agent` |
| 系统 Prompt | 面向 TEE + 安全课程的专用 prompt |
| Provider 白名单 | 玄知/Qwen/OpenAI/GitHub Copilot/Anthropic/Google |
| 玄知 | UI 展示 + 点击提示"暂不支持" |
| 默认模型 | 优先选 alibaba-cn (Qwen) |
| opencode 免费模型 | 完全禁用 |
| /connect | 支持断开已连接 provider |
| npm 发布 | 构建脚本 + darwin-arm64 已发布到 npm |
| 代码清理 | 移除 console/desktop/web/docs/enterprise 等无关包 |
| 命令提示 | `nsscli -s ses_xxx`（非 nss-cli） |

---

## 待实现

### 高优先级

| 任务 | 说明 |
|------|------|
| Qwen API Key 方案 | 学生开箱即用 → 硬编码共享 key 或引导首次配置 |
| 默认模型引导 | Qwen 未连接时显示"未配置"引导，而非 Big Pickle |
| 第一个内置 skill | `env-doctor`：环境自检（OS/CPU/Docker/QEMU 等） |
| /verify 命令 | TUI 内硬命令，触发验收流程 |
| /report 命令 | TUI 内硬命令，生成结构化报告 |

### 中优先级

| 任务 | 说明 |
|------|------|
| lab-crypto skill | 密码学基础实验引导 |
| lab-tee skill | OP-TEE on QEMU 实验引导 |
| tee-deploy skill 模板 | 提供 repo 脚手架，用户 clone 后开箱用 |
| 多平台 npm 发布 | linux-x64, linux-arm64 构建 |
| TODO_NSS_DOMAIN 清理 | 24 处占位符 |

### 低优先级

| 任务 | 说明 |
|------|------|
| 其他 lab-* skills | web-sec, os-sec, db-sec, software-sec, network-sec, tpm |
| 实验变体生成 | 参数/拓扑/对抗者模型变体，防答案复用 |
| 数据闭环 | 采集学生实验数据用于教学反馈 |

---

## 技术架构

```
nss-cli-agent (npm package)
├── opencode core（LLM 调度、TUI、bash 工具、MCP 底座）
├── 定制 System Prompt（TEE + 安全课程专家）
├── 内置 Skills/
│   ├── env-doctor（环境诊断）
│   ├── lab-crypto（密码学实验）
│   ├── lab-tee（机密计算实验）
│   └── ...
├── 内置 Labs/（实验包：脚本 + 验证器 + Docker Compose）
│   ├── crypto-basic/
│   ├── tee-optee-qemu/
│   └── ...
├── TUI 硬命令（/verify, /report）
└── Provider 白名单（玄知/Qwen/OpenAI/Anthropic/GitHub/Google）
```

---

## 参考资料

- `ref/opencode-tee/` — VisionFive 2 Keystone 成功部署项目，验证了 repo-local skill 模式
- `ref/专项类教改项目申报书.pdf` — 教改项目申报书（AI 赋能课程改革）
- opencode 原仓库 — https://github.com/anomalyco/opencode

---

## 设计原则

1. **证据驱动**：每个验证步骤必须有可追溯的日志/输出
2. **状态落盘**：不靠对话记忆，状态写入文件（manifest.json/status.md 模式）
3. **脚本沉淀**：可复现的操作写成 scripts/，不是临时 shell 命令
4. **离线优先**：内置实验包，不依赖网络
5. **渐进式**：先跑通 MVP（env-doctor + 1 个 lab），再逐步扩展
