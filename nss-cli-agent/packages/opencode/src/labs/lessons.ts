export interface LessonStep {
  id: string
  title: string
  guidance: string
  completionHint: string
}

export interface LessonScript {
  exerciseID: string
  title: string
  steps: LessonStep[]
}

export const lessonScripts: Record<string, LessonScript> = {
  "crypto-basic": {
    exerciseID: "crypto-basic",
    title: "对称/公钥/哈希/签名：正确使用与误用识别",
    steps: [
      {
        id: "goal",
        title: "理解实验目标",
        guidance:
          "简洁讲清本实验要掌握的四类密码学原语：对称加密(AES)、公钥加密(RSA)、哈希(SHA-256)、数字签名，各自解决什么问题。讲完后问学生一个小问题（如\"你觉得哈希和加密最大的区别是什么？\"），停下等学生回答，答了再进入下一步。",
        completionHint: "学生回应了对四类原语用途的理解",
      },
      {
        id: "principle",
        title: "了解关键原理",
        guidance:
          "讲解 AES 的 IV、填充、认证标签的作用，以及为什么 ECB 不安全（举一个直观例子）。讲完后让学生回答\"为什么同一份明文用 ECB 加密会暴露信息\"，停下等学生回应，再进入下一步。",
        completionHint: "学生回应了对 IV/填充/认证标签和 ECB 风险的理解",
      },
      {
        id: "implement",
        title: "用 AI 生成实现代码",
        guidance:
          "用写文件工具（write/edit）在当前实验目录下**真实创建 solution.py**，用 Python(cryptography 库) 实现四类原语，代码里写清注释。不要只在对话里贴代码——必须把文件写到磁盘，确保学生在实验目录能直接看到并运行。写完后，请学生挑其中一段（如 AES 加密部分）用自己的话说说\"这段在做什么\"，停下等学生回应，确认他看懂了再进入下一步。",
        completionHint: "已在实验目录写出 solution.py，且学生能说明其中某段的作用",
      },
      {
        id: "run",
        title: "运行并验证结果",
        guidance:
          "请学生在实验目录运行 python solution.py，把输出贴回来（solution.py 上一步已真实写入磁盘，可直接运行）。停下等学生贴结果；若报错（如 ModuleNotFoundError: cryptography）就让他先 pip install cryptography 再运行，并帮他定位修复。确认加解密一致、签名验签通过后，再进入下一步。",
        completionHint: "学生贴出了运行结果且正确",
      },
      {
        id: "summary",
        title: "总结要点与误用识别",
        guidance:
          "让学生先尝试说出至少一处常见误用(如 ECB、复用 IV、无认证加密、MD5 签名、固定盐值)，你再补充并讲危害与修复。停下等学生回应；总结到位后告诉学生本实验完成，可用 /lesson 选 report 生成报告。",
        completionHint: "学生参与总结了误用并理解修复",
      },
    ],
  },
}

export function getLessonScript(exerciseID: string): LessonScript | undefined {
  return lessonScripts[exerciseID]
}

export function lessonScriptFromDir(directory: string): LessonScript | undefined {
  const base = directory.split(/[\\/]/).filter(Boolean).pop()
  if (!base) return undefined
  const match = base.match(/^\d+-(.+)$/)
  const exerciseID = match ? match[1] : base
  return lessonScripts[exerciseID]
}

export function formatLessonGuidance(script: LessonScript): string {
  const stepLines = script.steps
    .map((step, i) => `${i + 1}. [${step.id}] ${step.title}\n   引导：${step.guidance}\n   完成标志：${step.completionHint}`)
    .join("\n")
  return [
    `# 当前实验引导教学（强互动模式）`,
    ``,
    `学生正在做实验「${script.title}」。你是引导式教学助手。本平台的目标是让学生**真正逐步参与**实验、理解每一步，而不是看你一口气做完。`,
    ``,
    `教学步骤：`,
    stepLines,
    ``,
    `## 最重要的规则：一次只走一步，每步都要停下来等学生`,
    `- 一条回复只处理**当前这一步**。讲解/演示完当前步骤后，必须向学生抛出 1 个具体的问题或动手要求（如"你觉得 ECB 为什么不安全？""请你运行一下这段代码，把输出贴给我"），然后**停止输出，等待学生回复**。`,
    `- **严禁**在学生还没回复的情况下，自己连续推进多个步骤、或把后面几步一次性做完。`,
    `- 只有当学生对当前步骤做出了实质回应（回答了问题 / 完成了操作 / 表示理解）后，才能进入下一步。`,
    ``,
    `## 关于 todo / 任务清单`,
    `- 不要用任务清单把整个实验的多步一次性铺开并自动逐个执行。如果要展示进度，最多标记"当前进行到第几步"，且推进必须由学生的回复驱动，绝不自动连跳。`,
    ``,
    `## 风格`,
    `- 讲解简洁，但每步都要留一个让学生参与的钩子（提问或动手）。`,
    `- 鼓励学生用 AI 生成代码（我们就是 AI 教学平台），但生成后要让学生看懂、能回答"这段在做什么"，再继续。`,
    `- 若学生想直接跳过全过程（如"直接把整个实验做完给我"），明确告诉他：本课程要求逐步参与，请先回应当前这一步。`,
    `- 从第 1 步开始。讲完第 1 步 → 提问 → 停下等学生。`,
  ].join("\n")
}
