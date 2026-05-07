import api from './client'
import type { ApiResponse } from '@/types'

export interface Synopsis {
  id: string
  case_name: string | null
  petitioner: string | null
  respondent: string | null
  court: string | null
  judgment_date: string | null
  case_number: string | null
  facts: string | null
  issues: string[]
  held: string | null
  citations_used: string[]
  relief_granted: string | null
  confidence: number
}

export const generateSynopsisFromUpload = (file: File) => {
  const form = new FormData()
  form.append('file', file)
  return api.post<ApiResponse<Synopsis>>('/synopsis/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export const generateSynopsis = (document_id: string) =>
  api.post<ApiResponse<Synopsis>>('/synopsis/generate', { document_id })

export const getSynopsis = (id: string) =>
  api.get<ApiResponse<Synopsis>>(`/synopsis/${id}`)

export const exportSynopsis = (id: string) =>
  api.get(`/synopsis/${id}/export`, { responseType: 'blob' })
