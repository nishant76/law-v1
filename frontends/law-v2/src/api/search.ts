import api from './client'
import { useAuthStore } from '@/store/authStore'
import type { ApiResponse, UnifiedSearchResponse } from '@/types'

export const unifiedSearch = (query: string, limit = 50) =>
  api.post<UnifiedSearchResponse>('/search/unified', { query, limit })

export const searchSuggest = (q: string) =>
  api.get<ApiResponse<string[]>>('/search/suggest', { params: { q } })

export const getCitationSummary = (id: string) =>
  api.get<{ summary: string | null }>(`/citations/${id}/summary`)

export const openJudgmentPdf = async (judgmentUrl: string): Promise<boolean> => {
  const base = import.meta.env.VITE_API_URL || ''
  const token = useAuthStore.getState().accessToken
  try {
    const resp = await fetch(`${base}${judgmentUrl}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!resp.ok) return false
    const blob = await resp.blob()
    const url = URL.createObjectURL(blob)
    window.open(url, '_blank', 'noopener,noreferrer')
    setTimeout(() => URL.revokeObjectURL(url), 60_000)
    return true
  } catch {
    return false
  }
}

export const downloadJudgmentPdf = async (judgmentUrl: string, filename: string): Promise<boolean> => {
  const base = import.meta.env.VITE_API_URL || ''
  const token = useAuthStore.getState().accessToken
  try {
    const resp = await fetch(`${base}${judgmentUrl}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!resp.ok) return false
    const blob = await resp.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    setTimeout(() => URL.revokeObjectURL(url), 10_000)
    return true
  } catch {
    return false
  }
}
