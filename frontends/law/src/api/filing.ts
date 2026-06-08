import api from './client'
import type { ApiResponse, Draft } from '@/types'

export interface SelectedCitation {
  case_name: string
  citation: string | null
  court: string
  year: number
  source_url?: string
}

export interface FilingInput {
  filing_type: string
  objective: string
  petitioner: string
  respondent: string
  court: string
  sections?: string
  facts: string
  relief?: string
  selected_citations?: SelectedCitation[]
}

export interface ExportFilingInput {
  draft_sections: Record<string, string>
  filing_type: string
  petitioner: string
  respondent: string
  court: string
  citations_used?: string[]
}

export const generateFiling = (input: FilingInput) =>
  api.post<ApiResponse<Draft>>('/filing/generate', input, { timeout: 60000 })

export const getFiling = (id: string) =>
  api.get<ApiResponse<Draft>>(`/filing/${id}`)

export const exportFiling = (id: string, body: ExportFilingInput) =>
  api.post(`/filing/${id}/export`, body, { responseType: 'blob', timeout: 30000 })
