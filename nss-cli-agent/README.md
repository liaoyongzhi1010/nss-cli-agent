# NSS CLI Agent

基于 [opencode](https://github.com/anomalyco/opencode) 二次开发的 CLI Agent 工具，面向**可信执行环境（TEE）开发部署**与**《计算机安全导论》课程实验教学**两大场景。

## 定位

`nss-cli-agent` 是一个发布到 npm 的独立 CLI 工具，学生或开发者通过 `npx nss-cli-agent` 或全局安装后直接使用。内置专用 skill 和 tool，开箱即用，无需额外配置。

## 两大核心场景

### 场景一：可信执行环境（TEE）开发与部署

面向 TEE/机密计算领域的开发者和研究人员，提供：

- **板卡部署辅助**：Keystone on VisionFive 2、OP-TEE on QEMU 等 TEE 环境的一键搭建与部署引导
- **环境自检与多路径构建**：识别宿主机 OS/CPU/权限/虚拟化能力，自动选择最优构建路径（容器优先，降级到源码/QEMU）
- **交叉编译工具链管理**：自动处理 RISC-V / ARM 交叉编译依赖
- **串口调试与验证**：集成串口连接、日志捕获、运行时验证脚本
- **多板卡抽象**：后续可扩展支持更多 TEE 硬件平台

### 场景二：《计算机安全导论》课程实验

面向西安电子科技大学《计算机安全导论》（CS205202）课程的本科生，提供：

- **实验环境一键搭建**：学生在自己的笔记本上运行 `nss lab init`，自动完成环境检测、依赖安装、容器/QEMU 拉起
- **分层实验任务**：每章实验按"基础—进阶—挑战"三层递进，学生按自身水平选择
- **八类实验模块**：
  1. 密码学基础（含 PKI/TLS）
  2. Web 安全
  3. 操作系统安全
  4. 数据库安全
  5. 软件安全
  6. 网络安全
  7. 可信计算（TPM/TCM）
  8. 机密计算（TEE：OP-TEE on QEMU）
- **自动验证与证据采集**：`nss lab verify` 执行测试用例、采集日志/抓包/验证输出
- **结构化报告生成**：`nss lab report` 生成报告草稿（证据索引 + 模板），学生补充理解性说明后提交
- **场景变体**：支持按参数/拓扑/对抗者模型生成实验变体，避免答案复用

## 内置能力

### 内置 Skills

| Skill | 用途 |
|-------|------|
| `tee-deploy` | TEE 环境部署（Keystone/OP-TEE/TrustZone），含环境自检、构建、刷写、验证全流程 |
| `lab-crypto` | 密码学基础实验引导（对称/公钥/哈希/PKI/TLS） |
| `lab-web-sec` | Web 安全实验（SQLi/XSS/CSRF 复现与防护） |
| `lab-os-sec` | 操作系统安全实验（Set-UID/环境变量注入/TOCTOU） |
| `lab-db-sec` | 数据库安全实验（注入/权限/审计） |
| `lab-software-sec` | 软件安全实验（缓冲区溢出/格式化字符串/ASLR/Canary/NX） |
| `lab-network-sec` | 网络安全实验（嗅探/伪造/DNS/TCP/防火墙/VPN） |
| `lab-tpm` | 可信计算实验（PCR/度量/密封解封/远程证明） |
| `lab-tee` | 机密计算实验（OP-TEE 环境/CA-TA 链路/共享内存/敏感数据生命周期） |
| `env-doctor` | 环境诊断与修复（失败原因分类 + 修复策略库） |

### 内置 Tools

| Tool | 用途 |
|------|------|
| `env-check` | 检测 OS/CPU/架构/权限/虚拟化/Docker/QEMU 等环境信息 |
| `lab-bundle` | 实验包管理（拉取/初始化/更新实验包） |
| `lab-verify` | 执行自动化验收（测试用例 + 证据采集 + 规则检查） |
| `lab-report` | 生成结构化实验报告草稿 |
| `serial-connect` | 串口连接管理（用于板卡调试） |
| `container-run` | 容器化实验拓扑启动（client/server/attacker 多节点） |
| `evidence-collect` | 证据归档（日志/抓包/截图/验证输出统一整理） |

## CLI 命令设计

```bash
# 通用
nss doctor              # 环境自检
nss init                # 初始化项目/实验工作目录

# TEE 部署场景
nss tee deploy          # 引导式 TEE 部署（交互选择板卡/平台）
nss tee build           # 构建 TEE 固件/镜像
nss tee flash           # 刷写到目标设备
nss tee verify          # 运行时验证（hello enclave 等）

# 课程实验场景
nss lab list            # 列出可用实验模块与任务
nss lab init <module>   # 初始化某个实验（拉取实验包、搭建环境）
nss lab run             # 运行当前实验
nss lab verify          # 执行验收（测试+证据采集）
nss lab report          # 生成报告草稿
nss lab variant         # 生成当前实验的变体配置

# 交互式 Agent 模式（继承 opencode 的 TUI）
nss                     # 进入交互式 Agent，可自然语言对话完成上述所有操作
```

## 技术架构

```
nss-cli-agent (npm package)
├── 定制 System Prompt（面向 TEE + 安全课程）
├── 内置 Skills（tee-deploy, lab-*, env-doctor）
├── 内置 Tools（env-check, lab-bundle, lab-verify, ...）
├── 实验包注册表（Bundle Registry，可本地/远程）
├── 验证器（Verifier，测试用例 + 规则 + 证据归档）
└── opencode core（LLM 调度、TUI、MCP、文件操作等底座能力）
```

## 与 opencode 的关系

- **底座**：复用 opencode 的 LLM 调度、TUI 交互、文件操作、bash 执行、MCP 协议等核心能力
- **定制**：替换 system prompt 为面向安全课程与 TEE 部署的专用 PE
- **扩展**：新增上述 skill 和 tool，打包进 npm 发布产物
- **品牌**：CLI 命令为 `nss`，包名为 `nss-cli-agent`

## 开发计划

| 阶段 | 时间 | 目标 |
|------|------|------|
| MVP | Q1 | CLI 骨架 + env-check + tee-deploy skill + 4 个基础实验模块 |
| v1.0 | Q2 | 8 类实验全覆盖基础层 + 验证器 + 报告生成 |
| v1.5 | Q3 | 进阶/挑战层任务 + 变体生成 + 课堂试点准备 |
| v2.0 | Q4 | TPM/OP-TEE 实验落地 + 数据闭环 + npm 正式发布 |

## 模型支持

继承 opencode 的多模型支持，同时内置推荐配置：
- 默认推荐：玄知密码学大模型（可信计算子领域）
- 备选：Claude / GPT-4 / DeepSeek 等通用模型

## 安装与使用

```bash
# 全局安装
npm install -g nss-cli-agent

# 或直接使用
npx nss-cli-agent

# 进入交互模式
nss

# 快速开始某个实验
nss lab init crypto-basic
```

## 项目背景

本工具是西安电子科技大学"基于玄知大模型的《计算机安全导论》实验教学智能体与工具链建设"教改项目（AI 赋能课程改革，重点项目，2026）的核心交付物之一。

团队：卢笛（主持）、郑乐乐（VS Code 插件）、穆旭彤（CLI 与工具链）、张涛（架构设计）、程珂（实验包与验证器）
