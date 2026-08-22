import api from './client'
import type { CaseDetail } from './ecourts'

export interface MatterFeeSummary {
  agreed: number
  paid: number
  due: number
}

export interface Matter {
  id: string
  case_name: string
  cnr_number: string | null
  matter_number: string | null
  court: string | null
  petitioner: string | null
  respondent: string | null
  case_status: string | null
  next_hearing_date: string | null
  is_active: boolean
  ecourts_tracked: boolean
  agreed_fee: number | null
  created_at: string
  client_name: string | null
  /** Present on the list endpoint; totals computed in SQL so list and detail agree. */
  fees?: MatterFeeSummary
}

export interface MatterDetail extends Matter {
  judge_name: string | null
  matter_type: string | null
  description: string | null
  filing_date: string | null
  limitation_date: string | null
  client_name: string | null
  client_phone: string | null
  whatsapp_reminders_enabled: boolean
}

export interface FeeInstallment {
  id: string
  label: string | null
  amount: number
  due_date: string | null
  is_paid: boolean
  paid_date: string | null
}

export interface FeesSummary {
  total: number
  paid: number
  due: number
  installments: FeeInstallment[]
}

export interface MatterDetailResponse {
  success: boolean
  matter: MatterDetail
  fees: FeesSummary
  ecourts_case: CaseDetail | null
  ecourts_error: string | null
}

export interface CreateMatterRequest {
  case_name: string
  court?: string
  matter_type?: string
  client_name?: string
  next_hearing_date?: string
  agreed_fee?: number
}

export const createMatter = (body: CreateMatterRequest) =>
  api.post<{ success: boolean; matter: MatterDetail }>('/matters', body)

export const listMatters = () =>
  api.get<{ success: boolean; matters: Matter[]; total: number }>('/matters')

export const getMatter = (id: string) =>
  api.get<MatterDetailResponse>(`/matters/${encodeURIComponent(id)}`)

export interface UpdateMatterRequest {
  case_name?: string
  court?: string
  matter_type?: string
  description?: string
  client_name?: string
  client_phone?: string
  is_active?: boolean
  whatsapp_reminders_enabled?: boolean
  next_hearing_date?: string
  case_status?: string
  agreed_fee?: number | null
}

export const updateMatter = (id: string, body: UpdateMatterRequest) =>
  api.patch<{ success: boolean; matter: MatterDetail }>(`/matters/${encodeURIComponent(id)}`, body)

export interface FeeInstallmentRequest {
  label?: string
  amount: number
  due_date?: string
  is_paid?: boolean
  paid_date?: string
}

export const addFeeInstallment = (matterId: string, body: FeeInstallmentRequest) =>
  api.post<{ success: boolean; fee: FeeInstallment }>(`/matters/${encodeURIComponent(matterId)}/fees`, body)

export const updateFeeInstallment = (
  matterId: string,
  feeId: string,
  body: Partial<FeeInstallmentRequest>
) =>
  api.patch<{ success: boolean; fee: FeeInstallment }>(
    `/matters/${encodeURIComponent(matterId)}/fees/${encodeURIComponent(feeId)}`,
    body
  )

export const deleteFeeInstallment = (matterId: string, feeId: string) =>
  api.delete<{ success: boolean }>(`/matters/${encodeURIComponent(matterId)}/fees/${encodeURIComponent(feeId)}`)
