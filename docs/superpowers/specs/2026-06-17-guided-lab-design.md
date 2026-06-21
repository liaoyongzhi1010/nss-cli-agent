# 引导式实验（Guided Lab）设计文档

日期：2026-06-17
范围：nss-cli-agent（教学脚本 + 步骤推进工具 + 轨迹）+ nss-evidence-server（轨迹签名 + 面板展示）
状态：待用户评审
MVP：先做 01-crypto-basic 一个实验跑通完整闭环

## 一、产品目标

我们是 AI 教学平台，**鼓励学生用 AI**。但要求学生跟着引导**逐步走完实验、看过每个细节**，而不是一句"帮我做完"就交差。

引导式实验 = **AI 按教学脚本，一步步带学生从 0 到 1 做完实验**。步骤推进轨迹作为"真在平台学习"的过程证据，纳入签名。

引导步骤不是额外打卡，就是**实验本身的教学流程**。

## 二、整体形态

学生进入实验后，AI 不丢一篇静态文档，而是按脚本逐步带做：
```
第1步【理解目标】AI 讲本实验要搞懂什么 → 学生回应 → 标记 goal 完成
第2步【讲原理】  AI 讲关键原理 → 学生回应 → 标记 principle 完成
第3步【引导生成】AI 引导用 AI 生成实现代码 → 学生确认 → 标记 implement 完成
第4步【运行验证】AI 引导运行并看结果 → 学生回应 → 标记 run 完成
第5步【总结】    AI 引导总结要点/误用 → 学生回应 → 标记 summary 完成
```
走完全部步骤 = 真学了这个实验。轨迹（guidance_progress）= 过程证据。

## 三、教学脚本（lessons.ts）

新建 `src/labs/lessons.ts`，结构化定义每个实验的步骤：
```typescript
export interface LessonStep {
  id: string
  title: string
  guidance: string
  completionHint: string
}

export interface LessonScript {
  exerciseID: string
  steps: LessonStep[]
}

export const lessonScripts: Record<string, LessonScript> = {
  "crypto-basic": {
    exerciseID: "crypto-basic",
    steps: [
      { id: "goal", title: "理解实验目标", guidance: "...", completionHint: "学生能复述本实验要掌握的4类密码学原语" },
      { id: "principle", title: "了解加密原理", guidance: "...", completionHint: "学生理解 AES 的 IV/填充/认证标签作用" },
      { id: "implement", title: "引导用 AI 生成实现代码", guidance: "...", completionHint: "已生成 solution.py 框架并理解各部分" },
      { id: "run", title: "运行并验证结果", guidance: "...", completionHint: "程序运行加解密/验签结果一致" },
      { id: "summary", title: "总结要点与误用识别", guidance: "...", completionHint: "学生能说出至少两处误用" },
    ],
  },
}
```
MVP 只填 crypto-basic，其余 23 个后续批量补。

## 四、AI 驱动机制

### 系统提示注入
学生进入实验目录后，把当前实验的 steps 列表 + "当前步骤"注入系统提示（动态上下文）。AI 按当前步的 guidance 带做，不提前透露后续步骤的完整答案。

### 步骤推进工具：lab_step_complete
新增 tool。AI 判断学生完成当前步后调用：
```
lab_step_complete({ exerciseID, stepID, studentInputDigest })
```
工具职责：
- 校验 stepID 是当前应完成的步骤（不能跳步、不能逆序）
- 校验距上一步标记之间存在学生真实输入（见防跳步）
- 记录一条轨迹：`{ stepID, completedAt, studentInputDigest }`
- 推进"当前步"到下一步
- 返回下一步信息供 AI 继续带做

轨迹存本地 `.nss/progress.json`，submit 时上传。

## 五、防跳步（核心防护）

风险：AI 不等学生真做就连续标记完成 → 甩手掌柜照样跳完。

工具层强制规则：
1. **每次只推进一步**：一次 lab_step_complete 只标记一个 stepID
2. **同消息不可连标多步**：工具记录上次调用所属的对话轮次，同一轮不能再次调用
3. **必须有学生真实输入**：两次标记之间必须存在学生的真实消息输入；工具记录 `studentInputDigest`（学生输入哈希）作证
4. **顺序校验**：stepID 必须等于"当前应完成步"，不能跳过

效果：甩手掌柜（不参与、让 AI 一路跳）→ 无真实输入 → 工具拒绝推进 → 步骤完成度停在 0/低 → 教师面板暴露。

## 六、证据签名升级

finalize 请求体增加 `guidance_progress`：
```json
{
  "final_report_markdown": "...",
  "files": [...],
  "guidance_progress": [
    { "stepID": "goal", "completedAt": "...", "studentInputDigest": "..." },
    ...
  ]
}
```
`evidence_hash` 输入扩展为 `{report, files, guidance_progress}`，整包签名。过程轨迹被改即检出。

## 七、教师面板

每个提交新增展示：
- **步骤完成度**：5/6 进度条
- **各步耗时**：从 timeline 计算每步间隔
- **总耗时**：vs 实验预期
- 风险提示（P1）：完成度低 + 耗时短 → 🔴 疑似甩手掌柜

## 八、与现有流程的衔接

- **init**：不变（建文件夹 + README）
- **report**：start 拿 run_id + 写骨架（不变）；新增初始化 `.nss/progress.json`（当前步=第1步）
- **实验过程**：学生与 AI 对话，AI 按脚本带做，lab_step_complete 记录轨迹
- **submit**：采集文件 + 读取 progress.json → finalize（含 guidance_progress）→ 签名

## 九、MVP 范围（首期）

1. `lessons.ts` 写 crypto-basic 的 5 步教学脚本
2. 系统提示注入当前实验 steps + 当前步
3. 新增 `lab_step_complete` 工具（含防跳步规则）
4. 本地 `.nss/progress.json` 轨迹记录
5. finalize 接收 guidance_progress 并纳入签名（后端）
6. 教师面板展示步骤完成度 + 耗时
7. 端到端跑通 crypto-basic

## 十、不做（YAGNI）
- 不做强制逐步问答评分（本期只记完成，不判断答得对不对）
- 不做风险评分引擎（P1）
- 不做其余 23 个脚本（跑通后批量补）
- 不做"防止用 AI 生成代码"（违背定位）

## 十一、一句话总结
把每个实验从"静态 README"升级为"AI 按脚本逐步带做"。学生跟着走完 = 真学了；步骤推进轨迹（需真实学生输入才能推进）= 防甩手掌柜的过程证据。先做 1 个实验跑通闭环。
