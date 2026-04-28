import api from './client'
import type { UnifiedSearchResponse } from '@/types'

export const unifiedSearch = (query: string, outcome_filter?: string) =>
  api.post<UnifiedSearchResponse>('/search/unified', { query, outcome_filter })

export const searchSuggest = (q: string) =>
  api.get<ApiResponse<string[]>>('/search/suggest', { params: { q } })
