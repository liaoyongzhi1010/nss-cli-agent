# nss-cli-agent（CLI 包）

`nss-cli-agent` 的 CLI 实现，基于 opencode 二次开发。发布到 npm 后学生用 `nss-cli` 命令做《计算机安全导论》课程实验。项目总览见[根 README](../../README.md)。

## 开发

```bash
bun install
bun dev        # 启动交互式 TUI（勿作阻塞式前台命令，需要时用 tmux，见 AGENTS.md）
```

## 测试

```bash
bun test test/labs/lessons.test.ts    # 实验脚本 + 报告生成测试
```

## 关键目录

| 路径 | 说明 |
|------|------|
| `src/labs/manifest.json` | 24 个实验定义（8 模块 × 3 难度） |
| `src/labs/lessons.ts` | 每个实验的强互动教学脚本 |
| `src/cli/cmd/tui/component/lab-evidence.ts` | 证据采集、QA 上报、report 生成（md + tex） |
| `src/cli/cmd/tui/app.tsx` | `/lesson` 命令、QA 提取、report 流程 |
| `script/build.ts` | 交叉编译 12 个平台子包 |
| `script/publish.ts` | 生成主包 + 发布到 npm |
| `script/postinstall.mjs` | 学生安装时按平台选装对应子包 |

## 构建与发布

```bash
# 交叉编译全部 12 个平台子包（版本用环境变量指定）
OPENCODE_VERSION=0.1.0 bun run script/build.ts

# --single 只编当前平台；--skip-embed-web-ui 跳过 web UI 嵌入
```

产物为主包 `nss-cli-agent`（含 postinstall + optionalDependencies 指向所有子包）+ 平台子包 `nss-cli-agent-<platform>-<arch>`。学生 `npm i -g nss-cli-agent` 后 postinstall 按平台自动选装二进制，命令为 `nss-cli`。
