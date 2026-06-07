import { createSignal } from "solid-js"

export interface SelectedLesson {
  moduleID: string
  moduleName: string
  exerciseID: string
  tier: string
  title: string
}

const [selected, setSelected] = createSignal<SelectedLesson | null>(null)

export function useLesson() {
  return { selected, setSelected }
}
