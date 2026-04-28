import api from './client'
import type { ApiResponse, Draft } from '@/types'

export interface FilingInput {
  filing_type: string
  objective: string
  petitioner: string
  respondent: string
  court: string
  sections?: string
  facts: string
  relief?: string
}

export const generateFiling = (input: FilingInput) =>
  api.post<ApiResponse<Draft>>('/filing/generate', input, { timeout: 60000 })

export const getFiling = (id: string) =>
  api.get<ApiResponse<Draft>>(`/filing/${id}`)

export const exportFiling = (id: string) =>
  api.get(`/filing/${id}/export`, { responseType: 'blob' })
