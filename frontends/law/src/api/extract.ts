import api from './client'
import type { ApiResponse, UniversalExtraction } from '@/types'

export const extractDocument = (document_id: string) =>
  api.post<ApiResponse<UniversalExtraction>>('/extract', { document_id })

export const extractFromUpload = (file: File) => {
  const form = new FormData()
  form.append('file', file)
  return api.post<ApiResponse<UniversalExtraction>>('/extract/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export const chatWithDocument = (
  document_id: string,
  messages: Array<{ role: 'user' | 'assistant'; content: string }>
) =>
  api.post<ApiResponse<{ answer: string; confidence: number; sources: unknown[] }>>('/extract/chat', {
    document_id,
    messages,
  })
