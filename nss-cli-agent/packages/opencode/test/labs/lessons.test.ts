import { describe, expect, test } from "bun:test"
import { readFile } from "fs/promises"
import { join } from "path"
import manifest from "../../src/labs/manifest.json"
import { lessonScripts, getLessonScript } from "../../src/labs/lessons"
import { writeReportWithFiles, appendTexSignature, type EvidenceMeta } from "../../src/cli/cmd/tui/component/lab-evidence"
import { tmpdir } from "../fixture/fixture"

describe("labs.lessons", () => {
  const manifestIDs = manifest.modules.flatMap((m) => m.exercises.map((e) => e.id))

  test("covers every exercise in manifest", () => {
    for (const id of manifestIDs) {
      expect(getLessonScript(id), `missing lesson script for ${id}`).toBeDefined()
    }
  })

  test("every lesson script is well-formed", () => {
    for (const [key, script] of Object.entries(lessonScripts)) {
      expect(script.exerciseID).toBe(key)
      expect(script.title.length).toBeGreaterThan(0)
      expect(script.steps.length).toBeGreaterThanOrEqual(3)
      for (const step of script.steps) {
        expect(step.id.length).toBeGreaterThan(0)
        expect(step.title.length).toBeGreaterThan(0)
        expect(step.guidance.length).toBeGreaterThan(0)
        expect(step.completionHint.length).toBeGreaterThan(0)
      }
    }
  })

  test("guidance enforces step-gated interaction and report at the end", () => {
    for (const script of Object.values(lessonScripts)) {
      const lastStep = script.steps[script.steps.length - 1]
      expect(lastStep.guidance).toContain("report")
    }
  })
})

describe("lab-evidence report generation", () => {
  const meta: EvidenceMeta = {
    runId: "run_test123",
    student: { name: "张三", id: "20240001" },
    serverStartedAt: "2026-06-22T10:00:00Z",
    exerciseID: "crypto-basic",
    evidenceServer: "http://127.0.0.1:8000",
  }

  test("writes report/ folder with both report.md and report.tex", async () => {
    await using tmp = await tmpdir()
    const result = await writeReportWithFiles({
      dir: tmp.path,
      title: "对称/公钥/哈希/签名",
      meta,
      files: [{ path: "solution.py", sha256: "abc123", size: 2048 }],
    })

    expect(result.dir).toBe(join(tmp.path, "report"))
    const md = await readFile(result.markdownPath, "utf-8")
    const tex = await readFile(result.texPath, "utf-8")

    expect(md).toContain("# 实验报告")
    expect(md).toContain("20240001")
    expect(md).toContain("solution.py")
    expect(md).not.toContain("submit")

    expect(tex).toContain("\\documentclass[11pt,a4paper]{ctexart}")
    expect(tex).toContain("xelatex")
    expect(tex).toContain("20240001")
    expect(tex).toContain("solution.py")
  })

  test("appendTexSignature inserts a signature section before end of document and is idempotent", () => {
    const base = "\\documentclass{ctexart}\n\\begin{document}\nhello\n\\end{document}\n"
    const sig = { run_id: "run_x", server_submitted_at: "t1", evidence_hash: "h1", signature: "s1" }
    const once = appendTexSignature(base, sig)
    expect(once).toContain("服务器证据签名")
    expect(once).toContain("run\\_x")
    expect(once.indexOf("\\end{document}")).toBeGreaterThan(once.indexOf("服务器证据签名"))

    const sig2 = { run_id: "run_y", server_submitted_at: "t2", evidence_hash: "h2", signature: "s2" }
    const twice = appendTexSignature(once, sig2)
    expect((twice.match(/服务器证据签名/g) || []).length).toBe(1)
    expect(twice).toContain("run\\_y")
    expect(twice).not.toContain("run\\_x")
  })
})
