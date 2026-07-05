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
    { title: "初始化实验", value: "init" as const, description: "① 创建实验文件夹和 README，然后和 AI 一起做实验" },
    { title: "生成实验报告", value: "report" as const, description: "② 实验做完后，采集代码与实验过程对话，签名定版" },
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
