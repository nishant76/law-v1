import api from './client'
import type { ApiResponse } from '@/types'

export interface Allegation {
  point_number: number
  allegation: string
  legal_basis_claimed: string | null
}

export interface NoticeExtraction {
  document_id: string
  sender: string | null
  recipient: string | null
  notice_date: string | null
  notice_type: string
  allegations: Allegation[]
}

export interface AllegationResponse {
  point_number: number
  allegation: string
  stance: 'admit' | 'deny' | 'partial'
  grounds: string
  legal_basis_claimed: string | null
}

export const uploadAndExtractAllegations = (file: File) => {
  const form = new FormData()
  form.append('file', file)
  return api.post<ApiResponse<NoticeExtraction>>('/reply/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export const generateReply = (
  document_id: string,
  allegation_responses: AllegationResponse[]
) =>
  api.post<ApiResponse<{ draft_id: string; reply_text: string }>>('/reply/generate', {
    document_id,
    allegation_responses,
  })

export const exportReplyDocx = (draft_id: string) =>
  api.get(`/reply/${draft_id}/export`, { responseType: 'blob' })

export const rewriteGrounds = (allegation: string, stance: string, facts: string) =>
  api.post<ApiResponse<{ rewritten_grounds: string }>>('/reply/rewrite-grounds', {
    allegation,
    stance,
    facts,
  })
