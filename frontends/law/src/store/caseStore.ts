import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { LegalCase, CasePayment, CaseHearing } from '@/types'

interface CaseState {
  cases: LegalCase[]
  addCase: (c: LegalCase) => void
  updateCase: (id: string, updates: Partial<LegalCase>) => void
  removeCase: (id: string) => void
  getCase: (id: string) => LegalCase | undefined
  addHearing: (id: string, hearing: CaseHearing) => void
  addPayment: (id: string, payment: CasePayment) => void
  togglePaymentPaid: (caseId: string, paymentId: string) => void
}

export const useCaseStore = create<CaseState>()(
  persist(
    (set, get) => ({
      cases: [],

      addCase: (c) =>
        set((s) => ({ cases: [c, ...s.cases] })),

      updateCase: (id, updates) =>
        set((s) => ({
          cases: s.cases.map((c) =>
            c.id === id
              ? { ...c, ...updates, updated_at: new Date().toISOString() }
              : c
          ),
        })),

      removeCase: (id) =>
        set((s) => ({ cases: s.cases.filter((c) => c.id !== id) })),

      getCase: (id) => get().cases.find((c) => c.id === id),

      addHearing: (id, hearing) =>
        set((s) => ({
          cases: s.cases.map((c) => {
            if (c.id !== id) return c
            const hearings = [...c.hearings, hearing].sort((a, b) =>
              a.date.localeCompare(b.date)
            )
            const upcoming = hearings.find((h) => h.date >= new Date().toISOString().slice(0, 10))
            return {
              ...c,
              hearings,
              next_hearing: upcoming?.date,
              updated_at: new Date().toISOString(),
            }
          }),
        })),

      addPayment: (id, payment) =>
        set((s) => ({
          cases: s.cases.map((c) =>
            c.id === id
              ? {
                  ...c,
                  payments: [...c.payments, payment],
                  updated_at: new Date().toISOString(),
                }
              : c
          ),
        })),

      togglePaymentPaid: (caseId, paymentId) =>
        set((s) => ({
          cases: s.cases.map((c) => {
            if (c.id !== caseId) return c
            return {
              ...c,
              payments: c.payments.map((p) =>
                p.id === paymentId
                  ? {
                      ...p,
                      paid: !p.paid,
                      paid_date: !p.paid ? new Date().toISOString().slice(0, 10) : undefined,
                    }
                  : p
              ),
              updated_at: new Date().toISOString(),
            }
          }),
        })),
    }),
    { name: 'nikhar-cases' }
  )
)
