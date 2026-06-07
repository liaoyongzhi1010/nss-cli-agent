import { createMemo, createSignal } from "solid-js"
import { DialogSelect } from "@tui/ui/dialog-select"
import { useDialog } from "@tui/ui/dialog"
import manifest from "@/labs/manifest.json"
import { useLesson, type SelectedLesson } from "./use-lesson"

const TIER_LABELS: Record<string, string> = {
  basic: "基础",
  intermediate: "进阶",
  challenge: "挑战",
}

export function DialogLesson(props: { onSelect?: (lesson: SelectedLesson) => void }) {
  const dialog = useDialog()
  const lesson = useLesson()
  const [query, setQuery] = createSignal("")

  const options = createMemo(() => {
    return manifest.modules.flatMap((mod) =>
      mod.exercises.map((ex) => ({
        title: `[${TIER_LABELS[ex.tier] ?? ex.tier}] ${ex.title}`,
        value: { moduleID: mod.id, moduleName: mod.name, exerciseID: ex.id, tier: ex.tier, title: ex.title },
        category: mod.name,
      })),
    )
  })

  return (
    <DialogSelect
      title="选择实验"
      options={options()}
      onFilter={setQuery}
      onSelect={(opt) => {
        lesson.setSelected(opt.value)
        dialog.clear()
        props.onSelect?.(opt.value)
      }}
    />
  )
}
