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
    { title: "init", value: "init" as const, description: "初始化实验：创建实验文件夹和 README" },
    { title: "report", value: "report" as const, description: "开始报告：记录学生信息，生成报告骨架" },
    { title: "submit", value: "submit" as const, description: "提交定版：采集文件哈希，上传报告并签名" },
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
