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

// ── Fill-in-the-blanks template flow ──────────────────────────────────────────

export interface KeyField {
  key: string
  label: string
  example?: string
  value?: string
}

export interface FilingTemplateResponse {
  success: boolean
  title: string
  template_markdown: string
  key_fields: KeyField[]
  citations_used: string[]
  strategy_notes: string
}

export interface TemplateInput {
  court?: string
  input_text: string
  selected_citations?: { case_name: string; citation: string | null }[]
}

export const generateFilingTemplate = (input: TemplateInput) =>
  api.post<FilingTemplateResponse>('/filing/template', input, { timeout: 120000 })

export const generateFilingTemplateFromFile = (file: File, meta: { court?: string }) => {
  const form = new FormData()
  form.append('file', file)
  form.append('court', meta.court ?? '')
  return api.post<FilingTemplateResponse>('/filing/template/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 150000,
  })
}

export const exportFilingTemplate = (body: {
  title: string
  filled_markdown: string
  court?: string
}) => api.post('/filing/template/export', body, { responseType: 'blob', timeout: 30000 })
