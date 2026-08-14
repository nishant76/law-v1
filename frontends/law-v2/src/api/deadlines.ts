import api from './client'
import type { ApiResponse, Deadline } from '@/types'

export const listDeadlines = (daysAhead = 30) =>
  api.get<ApiResponse<Deadline[]>>('/deadlines', { params: { days_ahead: daysAhead } })

export interface CreateDeadlinePayload {
  matter_id: string
  deadline_type: Deadline['deadline_type']
  deadline_date: string
  description: string
  client_phone?: string
}

/**
 * Creates the 30/7/1-day reminder set for one deadline — the response carries
 * every reminder row that was armed (offsets already in the past are skipped).
 */
export const createDeadline = (payload: CreateDeadlinePayload) =>
  api.post<
    ApiResponse<{
      key_date: string
      reminders: { id: string; reminder_date: string; status: string }[]
    }>
  >('/deadlines', null, { params: payload })

export const deleteDeadline = (id: string) =>
  api.delete<ApiResponse>(`/deadlines/${id}`)

export const markDeadlineMissed = (id: string) =>
  api.put<ApiResponse>(`/deadlines/${id}/missed`)

export const generateCondonation = (id: string, reasonForDelay: string) =>
  api.post<ApiResponse<{ draft_id: string }>>(
    `/deadlines/${id}/condonation`,
    null,
    { params: { reason_for_delay: reasonForDelay } },
  )
