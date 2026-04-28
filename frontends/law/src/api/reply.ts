import api from './client'
import type { ApiResponse } from '@/types'

export interface Allegation {
  point_number: number
  allegation: string
  legal_basis_claimed: string | null
  stance?: 'admit' | 'deny' | 'partial'
}

export interface NoticeExtraction {
  sender: string
  recipient: string
  notice_date: string | null
  notice_type: string
  allegations: Allegation[]
}

export const extractAllegations = (document_id: string) =>
  api.post<ApiResponse<NoticeExtraction>>('/reply/extract-allegations', { document_id })

export const getLegalGrounds = (allegation: string, matter_type: string) =>
  api.post<ApiResponse<{ suggested_grounds: unknown[]; recommended_stance: string }>>('/reply/legal-grounds', {
    allegation, matter_type,
  })

export const generateReply = (document_id: string, allegations: Allegation[]) =>
  api.post<ApiResponse<{ draft_id: string; draft_text: string }>>('/reply/generate', {
    document_id, allegations,
  })
