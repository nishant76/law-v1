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

export interface KeyField {
  key: string
  label: string
  example?: string
  value?: string
}

export interface FilingTemplateResponse {
  success: boolean
  title: string
  detected_document_type: string
  template_markdown: string
  key_fields: KeyField[]
  citations_used: string[]
  /** Facts the draft needs but the brief did not supply — must be shown, never swallowed. */
  missing_facts: string[]
  strategy_notes: string
}

export interface TemplateInput {
  court?: string
  input_text: string
  selected_citations?: { case_name: string; citation: string | null }[]
}

export interface BriefDimension {
  key: string
  label: string
  present: boolean
  note: string
}

export interface BriefQuestion {
  id: string
  question: string
  why: string
}

export interface BriefCheckResponse {
  success: boolean
  detected_filing_type: string
  completeness_score: number
  score_band: string
  dimensions: BriefDimension[]
  questions: BriefQuestion[]
}

export const generateFiling = (input: FilingInput) =>
  api.post<ApiResponse<Draft>>('/filing/generate', input, { timeout: 60000 })

export const getFiling = (id: string) =>
  api.get<ApiResponse<Draft>>(`/filing/${id}`)

export const exportFiling = (id: string, body: Record<string, unknown>) =>
  api.post(`/filing/${id}/export`, body, { responseType: 'blob', timeout: 30000 })

export const generateFilingTemplate = (input: TemplateInput) =>
  api.post<FilingTemplateResponse>('/filing/template', input, { timeout: 120000 })

export const checkBrief = (input: { brief: string; court?: string; type_hint?: string }) =>
  api.post<BriefCheckResponse>('/filing/brief-check', input, { timeout: 30000, skipAuthRedirect: true })

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
