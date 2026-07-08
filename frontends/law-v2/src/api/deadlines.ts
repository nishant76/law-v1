import api from './client'
import type { ApiResponse, Deadline } from '@/types'

export const listDeadlines = () =>
  api.get<ApiResponse<Deadline[]>>('/deadlines')

export const createDeadline = (payload: Omit<Deadline, 'id' | 'status'>) =>
  api.post<ApiResponse<Deadline>>('/deadlines', payload)

export const deleteDeadline = (id: string) =>
  api.delete<ApiResponse>(`/deadlines/${id}`)

export const generateCondonation = (id: string) =>
  api.post<ApiResponse<{ draft_id: string }>>(`/deadlines/${id}/condonation`)
