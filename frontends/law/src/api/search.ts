import api from './client'
import type { ApiResponse, UnifiedSearchResponse } from '@/types'

export const unifiedSearch = (query: string, outcome_filter?: string) =>
  api.post<UnifiedSearchResponse>('/search/unified', {
    query,
    filters: outcome_filter ? { outcome: outcome_filter } : undefined,
  })

export const searchSuggest = (q: string) =>
  api.get<ApiResponse<string[]>>('/search/suggest', { params: { q } })
