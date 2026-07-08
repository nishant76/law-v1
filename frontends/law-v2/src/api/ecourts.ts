import api from './client'

export interface EcourtsUpcoming {
  cnr: string
  case_name: string
  court: string | null
  next_hearing_date: string
}

export interface EcourtsSyncResult {
  success: boolean
  fetched: number
  updated: number
  created: number
  upcoming: EcourtsUpcoming[]
}

export interface LawyerProfile {
  display_name: string
  court: string
  slug: string
  profile_url: string
}

export interface DiscoveredCase {
  cnr: string
  case_name: string
  petitioner: string
  respondent: string
  pet_adv: string
  res_adv: string
  court: string
  case_type: string
  status: string
  next_hearing_date?: string | null
  filing_date?: string | null
  court_code?: string
}

export const getEcourtsStatus = () =>
  api.get<{ success: boolean; bar_council_number: string | null; advocate_name: string | null; ready_to_sync: boolean; matters_with_cnr: number }>('/ecourts/status')

export const setEcourtsProfile = (data: { advocate_name?: string; bar_council_number?: string; ecourts_state_code?: string }) =>
  api.put<{ success: boolean }>('/ecourts/profile', data)

/** @deprecated use setEcourtsProfile */
export const setEcourtsAdvocateName = (advocate_name: string) =>
  api.put<{ success: boolean; advocate_name: string }>('/ecourts/advocate-name', { advocate_name })

export const syncEcourtsHearings = () =>
  api.post<EcourtsSyncResult>('/ecourts/sync', {}, { timeout: 90000 })

export const refreshCnrHearings = () =>
  api.post<{ success: boolean; refreshed: number; failed: number }>('/ecourts/refresh-cnr', {}, { timeout: 120000 })

// ── First-login onboarding ─────────────────────────────────────────────────

/** Step 1: search ecourtsindia.com for matching lawyer profiles */
export const searchLawyerProfiles = (q: string) =>
  api.get<{ success: boolean; profiles: LawyerProfile[]; total: number }>(
    `/ecourts/search-lawyers?q=${encodeURIComponent(q)}`,
    { timeout: 45000 }
  )

/** Step 2: get all cases for a specific profile slug, filtered by city when provided */
export const getLawyerCases = (slug: string, city?: string) => {
  const params = city ? `?city=${encodeURIComponent(city)}` : ''
  return api.get<{ success: boolean; cases: DiscoveredCase[]; total: number; pages_fetched: number; courts_searched?: string[]; district_prefix?: string | null }>(
    `/ecourts/lawyer-cases/${encodeURIComponent(slug)}${params}`,
    { timeout: 300000 }
  )
}

/**
 * Preview the logged-in lawyer's pending cases using their stored advocate name.
 * No manual input needed — the backend reads the name from the user's profile.
 * Pass `city` to filter results to a specific district (e.g. "Panchkula").
 */
export const previewMyCases = (city?: string) => {
  const params = city ? `?city=${encodeURIComponent(city)}` : ''
  return api.get<{ success: boolean; advocate_name: string; cases: DiscoveredCase[]; total: number; city?: string; district_prefix?: string | null }>(
    `/ecourts/preview-my-cases${params}`,
    { timeout: 300000 }
  )
}

/** Step 3: import confirmed cases as Matters (sends full scraped data so names/courts are correct) */
export const importCnrs = (cases: DiscoveredCase[]) =>
  api.post<{ success: boolean; imported: number; skipped: number; refreshed: number; failed: { cnr: string; error: string }[] }>(
    '/ecourts/import-cnrs',
    {
      cases: cases.map((c) => ({
        cnr: c.cnr,
        case_name: c.case_name,
        petitioner: c.petitioner,
        respondent: c.respondent,
        court: c.court,
        case_type: c.case_type,
        status: c.status,
      })),
    },
    { timeout: 120000 }
  )
