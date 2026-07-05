import { mkdir, writeFile, access } from "fs/promises"
import { join } from "path"
import type { SelectedLesson } from "./use-lesson"
import { labReadmes } from "@/labs/content"
import manifest from "@/labs/manifest.json"

async function exists(path: string) {
  try {
    await access(path)
    return true
  } catch {
    return false
  }
}

function getOrder(exerciseID: string): number {
  let idx = 1
  for (const mod of manifest.modules) {
    for (const ex of mod.exercises) {
      if (ex.id === exerciseID) return idx
      idx++
    }
  }
  return idx
}

function dirName(lesson: SelectedLesson): string {
  const order = getOrder(lesson.exerciseID)
  return `${String(order).padStart(2, "0")}-${lesson.exerciseID}`
}

function fallbackReadme(lesson: SelectedLesson): string {
  const tierLabel =
    lesson.tier === "basic" ? "基础" : lesson.tier === "intermediate" ? "进阶" : "挑战"
  return `# ${lesson.moduleName} · [${tierLabel}] ${lesson.title}

## 实验目标

> 待补充。

## 实验要求

> 待补充。

## 验收标准

- **可复现实物**：代码 / 脚本 / 配置，可在本机重复运行。
- **验证证据**：程序运行输出正确。
- **理解性说明**：威胁模型、关键参数选择依据、现象解释。

## 提示

- 运行 /verify 让智能体检查你的实现是否满足验收标准。
- 运行 /report 生成实验报告草稿。
`
}

export function getLessonDir(cwd: string, lesson: SelectedLesson): string {
  const name = dirName(lesson)
  const base = cwd.split(/[\\/]/).filter(Boolean).pop()
  if (base === name) return cwd
  return join(cwd, name)
}

export function shortenHome(p: string): string {
  const home = process.env.HOME
  if (home && p.startsWith(home)) return "~" + p.slice(home.length)
  return p
}

export interface InitResult {
  dir: string
  created: boolean
}

export async function initLesson(cwd: string, lesson: SelectedLesson): Promise<InitResult> {
  const dir = getLessonDir(cwd, lesson)
  const readmePath = join(dir, "README.md")

  if (await exists(readmePath)) {
    return { dir, created: false }
  }

  await mkdir(dir, { recursive: true })
  const content = labReadmes[lesson.exerciseID] ?? fallbackReadme(lesson)
  await writeFile(readmePath, content, "utf-8")
  const nssDir = join(dir, ".nss")
  await mkdir(nssDir, { recursive: true })
  await writeFile(join(nssDir, "started.json"), JSON.stringify({ startedAt: new Date().toISOString() }, null, 2), "utf-8")
  return { dir, created: true }
}

export async function loadLessonStartedAt(cwd: string, lesson: SelectedLesson): Promise<string | undefined> {
  try {
    const { readFile } = await import("fs/promises")
    const raw = await readFile(join(getLessonDir(cwd, lesson), ".nss", "started.json"), "utf-8")
    const parsed = JSON.parse(raw) as { startedAt?: string }
    return parsed.startedAt
  } catch {
    return undefined
  }
}
