import api from './client'
import type { ApiResponse } from '@/types'

export interface ProcedureResult {
  steps: { step_number: number; action: string; details: string; source: string }[]
  documents_required: string[]
  court_fees: string
  limitation_period: string
  limitation_calculation: string
  typical_timeline: string
  confidence: number
  verify_at_registry: boolean
}

export const getMatterTypes = () =>
  api.get<ApiResponse<string[]>>('/legal-process/matter-types')

export const getProcedure = (matter_type: string, court: string, facts: string) =>
  api.post<ApiResponse<ProcedureResult>>('/legal-process/procedure', { matter_type, court, facts })
