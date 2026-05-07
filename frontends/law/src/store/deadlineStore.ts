import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type DeadlineType = 'hearing' | 'filing' | 'limitation'

export interface Deadline {
  id: string
  matter_title: string
  court: string
  case_number?: string
  deadline_type: DeadlineType
  due_date: string        // YYYY-MM-DD
  notes?: string
  client_phone?: string   // E.164 or local Indian format
  whatsapp_enabled: boolean
  created_at: string
}

interface DeadlineState {
  deadlines: Deadline[]
  addDeadline: (d: Deadline) => void
  removeDeadline: (id: string) => void
}

export const useDeadlineStore = create<DeadlineState>()(
  persist(
    (set) => ({
      deadlines: [],

      addDeadline: (d) =>
        set((s) => ({
          deadlines: [...s.deadlines, d].sort((a, b) =>
            a.due_date.localeCompare(b.due_date)
          ),
        })),

      removeDeadline: (id) =>
        set((s) => ({ deadlines: s.deadlines.filter((d) => d.id !== id) })),
    }),
    { name: 'nikhar-deadlines' }
  )
)
