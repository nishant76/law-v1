import api from './client'
import type { ApiResponse } from '@/types'

export interface Synopsis {
  id: string
  case_name: string
  petitioner: string
  respondent: string
  court: string
  judgment_date: string | null
  facts: string
  issues: string[]
  held: string
  citations_used: string[]
  confidence: number
}

export const generateSynopsis = (document_id: string) =>
  api.post<ApiResponse<Synopsis>>('/synopsis/generate', { document_id })

export const getSynopsis = (id: string) =>
  api.get<ApiResponse<Synopsis>>(`/synopsis/${id}`)

export const exportSynopsis = (id: string) =>
  api.get(`/synopsis/${id}/export`, { responseType: 'blob' })
