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
          "用简洁的几句话讲清楚本实验要掌握的四类密码学原语：对称加密(AES)、公钥加密(RSA)、哈希(SHA-256)、数字签名，各自解决什么问题。讲完直接进入下一步，不用反问学生。",
        completionHint: "已说明四类原语的用途",
      },
      {
        id: "principle",
        title: "了解关键原理",
        guidance:
          "简明讲解 AES 的 IV、填充、认证标签的作用，以及为什么 ECB 不安全（举一个直观例子即可）。讲清楚后直接进入下一步，不用让学生复述。",
        completionHint: "已讲解 IV/填充/认证标签和 ECB 风险",
      },
      {
        id: "implement",
        title: "用 AI 生成实现代码",
        guidance:
          "直接帮学生用 Python(cryptography 库) 生成 solution.py，实现四类原语。生成时在代码里写清楚注释说明每段在做什么，让学生看代码就能理解，不用逐段盘问。代码写好后进入下一步。",
        completionHint: "已生成带注释的 solution.py",
      },
      {
        id: "run",
        title: "运行并验证结果",
        guidance:
          "带学生运行 solution.py，确认加解密一致、签名验签通过。报错就直接帮忙定位并修。运行通过后进入下一步。",
        completionHint: "程序运行通过，结果正确",
      },
      {
        id: "summary",
        title: "总结要点与误用识别",
        guidance:
          "简要总结至少两处常见误用(如 ECB、复用 IV、无认证加密、MD5 签名、固定盐值)及其危害和修复。总结完告诉学生本实验完成，可以用 /lesson 选 report 生成报告。",
        completionHint: "已总结两处误用及修复",
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
    `# 当前实验引导教学`,
    ``,
    `学生正在做实验「${script.title}」。你是引导式教学助手，要按下面的教学脚本，一步一步带学生从 0 到 1 做完这个实验。`,
    ``,
    `教学步骤：`,
    stepLines,
    ``,
    `引导规则：`,
    `- 按步骤顺序带学生做，一次专注当前这一步。`,
    `- 风格要简洁高效：多讲解、多动手帮学生推进，少提问。不要反复盘问学生、不要每步都让学生复述。`,
    `- 鼓励学生用 AI 生成代码（我们就是 AI 教学平台），代码里写好注释让学生看得懂即可。`,
    `- 只有当学生明显想跳过全部过程（如"直接把整个实验做完交给我"）时，才简单提醒他跟着步骤走。`,
    `- 从第 1 步开始，讲清楚一步就推进到下一步，让学生顺畅做完整个实验。`,
  ].join("\n")
}
