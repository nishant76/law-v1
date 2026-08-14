import api from './client'
import type { ApiResponse } from '@/types'

export type HearingEntryStatus =
  | 'scheduled'
  | 'held'
  | 'adjourned'
  | 'not_taken_up'
  | 'disposed'

export interface HearingEntry {
  id: string
  matter_id: string
  case_name: string
  matter_number: string | null
  cnr_number: string | null
  client_name: string | null
  /** UTC ISO timestamp. */
  hearing_date: string
  /** Same instant rendered in IST — use this for display. */
  hearing_date_local: string
  status: HearingEntryStatus
  court: string | null
  judge_name: string | null
  board_number: string | null
  purpose: string | null
  outcome: string | null
  adjournment_reason: string | null
  next_date: string | null
  action_required: string | null
  appeared_by: string | null
  from_ecourts: boolean
}

export interface DiaryDay {
  date: string
  days: number
  entries: HearingEntry[]
  count: number
}

/**
 * Cause list for one local (IST) date, or for a range starting at it.
 * `days` defaults to 1 (the day view); pass 7 for the week.
 */
export const getDiary = (day?: string, days = 1) =>
  api.get<ApiResponse<DiaryDay>>('/diary', { params: { day, days } })

/** Every recorded date for one matter, most recent first. */
export const getMatterDiary = (matterId: string) =>
  api.get<ApiResponse<{ entries: HearingEntry[]; count: number }>>(
    `/diary/matters/${matterId}`,
  )

export interface CreateDiaryEntryPayload {
  matter_id: string
  hearing_date: string
  court?: string
  judge_name?: string
  board_number?: string
  purpose?: string
  appeared_by?: string
}

export const createDiaryEntry = (payload: CreateDiaryEntryPayload) =>
  api.post<ApiResponse<{ id: string }>>('/diary', payload)

export interface RecordOutcomePayload {
  status: HearingEntryStatus
  outcome?: string
  /** Supplying this rolls the matter forward and re-arms 30/7/1 reminders. */
  next_date?: string
  adjournment_reason?: string
  action_required?: string
  appeared_by?: string
  board_number?: string
}

export const recordHearingOutcome = (entryId: string, payload: RecordOutcomePayload) =>
  api.patch<ApiResponse<HearingEntry>>(`/diary/${entryId}`, payload)
