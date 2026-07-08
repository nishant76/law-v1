import api from './client'

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
  created_at: string
}

export const listMatters = () =>
  api.get<{ success: boolean; matters: Matter[]; total: number }>('/matters')
