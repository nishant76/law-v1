import api from './client'

export interface EcourtsUpcoming {
  cnr: string
  case_name: string
  court: string | null
  next_hearing_date: string // YYYY-MM-DD
}

export interface EcourtsSyncResult {
  success: boolean
  fetched: number
  updated: number
  created: number
  upcoming: EcourtsUpcoming[]
}

export interface EcourtsCase {
  cnr: string
  petitioner: string | null
  respondent: string | null
  court: string | null
  next_hearing_date: string | null
  case_status: string | null
  case_type: string | null
  case_number: string | null
}

export const getEcourtsStatus = () =>
  api.get<{ success: boolean; configured: boolean; advocate_name: string | null }>('/ecourts/status')

export const setEcourtsAdvocateName = (advocate_name: string) =>
  api.put<{ success: boolean; advocate_name: string }>('/ecourts/advocate-name', { advocate_name })

export const syncEcourtsHearings = () =>
  api.post<EcourtsSyncResult>('/ecourts/sync', {}, { timeout: 90000 })

/** Look up a single case by CNR number. Used for auto-fill on the Add Matter form. */
export const getCnrCase = (cnr: string) =>
  api.get<{ success: boolean; cnr: string; case: EcourtsCase }>(`/ecourts/case/${cnr.trim().toUpperCase()}`)

/** One-time CNR discovery via ecourtsindia.com API (~₹1). Call once at signup. */
export const discoverCnrs = (state?: string) =>
  api.post<{ success: boolean; cnrs: string[]; total: number; advocate_name: string }>(
    '/ecourts/discover',
    { state },
    { timeout: 30000 },
  )
