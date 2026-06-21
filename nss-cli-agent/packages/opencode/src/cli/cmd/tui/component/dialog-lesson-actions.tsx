import { DialogSelect } from "@tui/ui/dialog-select"
import { useDialog } from "@tui/ui/dialog"
import { useLesson, type SelectedLesson } from "./use-lesson"

interface Props {
  onInit: (sel: SelectedLesson) => void
  onReport: (sel: SelectedLesson) => void
  onSubmit: (sel: SelectedLesson) => void
}

export function DialogLessonActions(props: Props) {
  const dialog = useDialog()
  const lesson = useLesson()
  const sel = lesson.selected()!

  const options = [
    { title: "init", value: "init" as const, description: "① 初始化实验：创建实验文件夹和 README，然后和 AI 一起做实验" },
    { title: "report", value: "report" as const, description: "② 生成报告：实验做完后，采集代码并生成实验报告" },
    { title: "submit", value: "submit" as const, description: "③ 提交定版：上传报告并签名，教师可查验" },
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
          case "submit":
            props.onSubmit(sel)
            break
        }
      }}
    />
  )
}
