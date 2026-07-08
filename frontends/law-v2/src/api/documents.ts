import api from './client'
import type { ApiResponse, Document } from '@/types'

export const uploadDocument = (file: File, onProgress?: (pct: number) => void) => {
  const form = new FormData()
  form.append('file', file)
  return api.post<ApiResponse<Document>>('/documents/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => onProgress?.(Math.round((e.loaded * 100) / (e.total ?? 1))),
  })
}

export const getDocument = (id: string) =>
  api.get<ApiResponse<Document>>(`/documents/${id}`)

export const deleteDocument = (id: string) =>
  api.delete<ApiResponse>(`/documents/${id}`)
