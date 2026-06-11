import { mkdir, readdir, readFile, stat, writeFile } from "fs/promises"
import { createHash } from "crypto"
import { join, relative } from "path"
import type { SelectedLesson } from "./use-lesson"
import { getLessonDir } from "./lab-init"

export interface StudentInfo {
  name: string
  id: string
}

export interface EvidenceMeta {
  runId: string
  serverStartedAt: string
  student: StudentInfo
  exerciseID: string
  evidenceServer: string
}

export interface EvidenceFileInfo {
  path: string
  sha256: string
  size: number
}

export interface EvidencePackage {
  report_markdown: string
  timeline: { time: string; event: string }[]
  files: EvidenceFileInfo[]
}

export interface SubmitEvidenceResult {
  run_id: string
  server_submitted_at: string
  evidence_hash: string
  signature: string
}

export function evidenceServerURL() {
  return process.env.NSS_EVIDENCE_SERVER || "http://127.0.0.1:8000"
}

export function parseStudentInfo(value: string): StudentInfo | null {
  const trimmed = value.trim()
  const match = trimmed.match(/^(.+?)[,，\s]+([A-Za-z0-9_-]+)$/)
  if (!match) return null
  return { name: match[1].trim(), id: match[2].trim() }
}

export async function collectComputerInfo() {
  return {
    platform: process.platform,
    arch: process.arch,
    node: process.version,
    userAgent: typeof navigator !== "undefined" ? navigator.userAgent : undefined,
  }
}

export async function startEvidenceRun(cwd: string, lesson: SelectedLesson, student: StudentInfo): Promise<EvidenceMeta> {
  const server = evidenceServerURL()
  const response = await fetch(`${server}/runs/start`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      student_name: student.name,
      student_id: student.id,
      exercise_id: lesson.exerciseID,
      computer: await collectComputerInfo(),
    }),
  })
  if (!response.ok) throw new Error(`证据后端启动失败：${response.status} ${await response.text()}`)
  const body = (await response.json()) as { run_id: string; server_started_at: string }
  const meta = {
    runId: body.run_id,
    serverStartedAt: body.server_started_at,
    student,
    exerciseID: lesson.exerciseID,
    evidenceServer: server,
  }
  await saveEvidenceMeta(cwd, lesson, meta)
  return meta
}

export async function saveEvidenceMeta(cwd: string, lesson: SelectedLesson, meta: EvidenceMeta) {
  const dir = getLessonDir(cwd, lesson)
  const nssDir = join(dir, ".nss")
  await mkdir(nssDir, { recursive: true })
  await writeFile(join(nssDir, "evidence.json"), JSON.stringify(meta, null, 2), "utf-8")
}

export async function loadEvidenceMeta(cwd: string, lesson: SelectedLesson): Promise<EvidenceMeta | null> {
  try {
    const content = await readFile(join(getLessonDir(cwd, lesson), ".nss", "evidence.json"), "utf-8")
    return JSON.parse(content) as EvidenceMeta
  } catch {
    return null
  }
}

async function walkFiles(root: string, current = root): Promise<string[]> {
  const entries = await readdir(current, { withFileTypes: true })
  const files: string[] = []
  for (const entry of entries) {
    if (entry.name === ".nss") continue
    const full = join(current, entry.name)
    if (entry.isDirectory()) files.push(...(await walkFiles(root, full)))
    if (entry.isFile()) files.push(full)
  }
  return files
}

export async function collectFileEvidence(dir: string): Promise<EvidenceFileInfo[]> {
  const files = await walkFiles(dir)
  const result: EvidenceFileInfo[] = []
  for (const file of files.sort()) {
    const content = await readFile(file)
    const info = await stat(file)
    result.push({
      path: relative(dir, file),
      sha256: createHash("sha256").update(content).digest("hex"),
      size: info.size,
    })
  }
  return result
}

export async function submitEvidence(meta: EvidenceMeta, evidence: EvidencePackage): Promise<SubmitEvidenceResult> {
  const response = await fetch(`${meta.evidenceServer}/runs/${meta.runId}/submit`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(evidence),
  })
  if (!response.ok) throw new Error(`证据上传失败：${response.status} ${await response.text()}`)
  return (await response.json()) as SubmitEvidenceResult
}

export function evidenceAppendix(result: SubmitEvidenceResult) {
  return `\n\n## 服务器证据签名\n\n- 提交编号：${result.run_id}\n- 服务器提交时间：${result.server_submitted_at}\n- 证据哈希：${result.evidence_hash}\n- 服务端签名：${result.signature}\n`
}

export async function writeSignedReportDraft(input: {
  dir: string
  title: string
  meta: EvidenceMeta
  files: EvidenceFileInfo[]
  signature: SubmitEvidenceResult
}) {
  const fileLines = input.files.map((file) => `- ${file.path} (${file.size} bytes) SHA256: ${file.sha256}`).join("\n")
  const content = `# 实验报告：${input.title}

## 基本信息

- 姓名：${input.meta.student.name}
- 学号：${input.meta.student.id}
- 实验开始时间：${input.meta.serverStartedAt}
- 实验结束时间：${input.signature.server_submitted_at}
- 电脑配置：由 nsscli 自动采集并上传至证据服务器

## 实验目标

请根据 README.md 补充本实验目标。

## 操作时间线

- ${input.signature.server_submitted_at} 生成实验报告并上传证据包

## 代码文件清单

${fileLines || "- 暂无代码文件"}

## 实现要点（从抽象到代码的映射）

请根据你的实现补充关键思路、参数选择和代码映射。

## 遇到的问题与解决

请补充实验过程中遇到的问题和解决过程。

## 结论与反思

请补充实验结论和个人反思。
${evidenceAppendix(input.signature)}`
  await writeFile(join(input.dir, "report.md"), content, "utf-8")
  return content
}

export async function writeReportSkeleton(input: {
  dir: string
  title: string
  meta: EvidenceMeta
}) {
  const content = `# 实验报告：${input.title}

## 基本信息

- 姓名：${input.meta.student.name}
- 学号：${input.meta.student.id}
- 实验开始时间：${input.meta.serverStartedAt}
- 提交编号：${input.meta.runId}

## 实验目标

请根据 README.md 补充本实验目标。

## 操作时间线

请记录关键操作步骤和时间。

## 代码文件清单

完成实验后执行 submit 自动生成。

## 实现要点（从抽象到代码的映射）

请根据你的实现补充关键思路、参数选择和代码映射。

## 遇到的问题与解决

请补充实验过程中遇到的问题和解决过程。

## 结论与反思

请补充实验结论和个人反思。
`
  await writeFile(join(input.dir, "report.md"), content, "utf-8")
  return content
}

export interface FinalizeResult {
  run_id: string
  server_submitted_at: string
  evidence_hash: string
  signature: string
}

export async function finalizeEvidence(meta: EvidenceMeta, reportMarkdown: string, files: EvidenceFileInfo[]): Promise<FinalizeResult> {
  const response = await fetch(`${meta.evidenceServer}/runs/${meta.runId}/finalize`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ final_report_markdown: reportMarkdown, files }),
  })
  if (!response.ok) {
    const text = await response.text()
    throw new Error(`定版失败：${response.status} ${text}`)
  }
  return (await response.json()) as FinalizeResult
}
