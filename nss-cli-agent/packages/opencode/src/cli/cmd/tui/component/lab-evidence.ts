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
