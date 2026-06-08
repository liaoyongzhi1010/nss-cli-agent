import { DialogSelect } from "@tui/ui/dialog-select"
import { useDialog } from "@tui/ui/dialog"
import { useLesson, type SelectedLesson } from "./use-lesson"

interface Props {
  onInit: (sel: SelectedLesson) => void
  onReport: (sel: SelectedLesson) => void
}

export function DialogLessonActions(props: Props) {
  const dialog = useDialog()
  const lesson = useLesson()
  const sel = lesson.selected()!

  const options = [
    { title: "init", value: "init" as const, description: "初始化实验：创建实验文件夹和 README" },
    { title: "report", value: "report" as const, description: "生成报告：上传证据并写入服务端签名" },
  ]

  return (
    <DialogSelect
      title={`${sel.title}`}
      options={options}
      onSelect={(opt) => {
        dialog.clear()
        switch (opt.value) {
          case "init":
            props.onInit(sel)
            break
          case "report":
            props.onReport(sel)
            break
        }
      }}
    />
  )
}
