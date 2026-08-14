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
  court_code?: string
  case_type: string
  status: string
  next_hearing_date?: string | null
  last_hearing_date?: string | null
  first_hearing_date?: string | null
  filing_date?: string | null
  filing_number?: string
  registration_number?: string
  registration_date?: string | null
  decision_date?: string | null
  judges?: string[]
  acts_and_sections?: string[]
  case_category?: string
  bench_type?: string
  state_code?: string
  filing_year?: number | null
  has_orders?: boolean
  has_judgments?: boolean
  order_count?: number | null
  hearing_count?: number | null
}

export interface CaseHearingEvent {
  hearing_date: string | null
  business_on_date: string | null
  judge: string | null
  purpose: string | null
}

export interface CaseOrder {
  date: string | null
  description: string | null
  url: string | null
}

export interface CaseProcess {
  date: string | null
  title: string | null
}

export interface CaseDetail {
  cnr: string
  case_name: string
  petitioners: string[]
  respondents: string[]
  petitioner: string
  respondent: string
  petitioner_advocates: string[]
  respondent_advocates: string[]
  court_name: string
  court_code: string
  case_type: string
  case_type_raw: string
  case_type_sub: string
  case_status: string
  filing_date: string | null
  filing_number: string
  registration_date: string | null
  registration_number: string
  next_hearing_date: string | null
  last_hearing_date: string | null
  first_hearing_date: string | null
  decision_date: string | null
  stage_of_case: string
  purpose: string
  judges: string[]
  judge_codes: string[]
  hearing_history: CaseHearingEvent[]
  orders: CaseOrder[]
  judgment_orders: CaseOrder[]
  processes: CaseProcess[]
  has_order_documents: boolean
  order_count: number | null
  interim_order_count: number | null
  judgment_count: number | null
  hearing_count: number | null
  district: string
  state: string
}

export const getEcourtsStatus = () =>
  api.get<{
    success: boolean
    bar_council_number: string | null
    advocate_name: string | null
    ready_to_sync: boolean
    matters_with_cnr: number
    name_match_found: boolean | null
  }>('/ecourts/status')

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
  return api.get<{ success: boolean; advocate_name: string; cases: DiscoveredCase[]; total: number; city?: string; district_prefix?: string | null; name_match_found: boolean | null }>(
    `/ecourts/preview-my-cases${params}`,
    { timeout: 300000 }
  )
}

/**
 * Manual fallback: search PENDING cases by party/litigant name, typed by the lawyer.
 * Used when previewMyCases() finds nothing under their stored advocate name.
 */
export const searchCasesByName = (q: string) =>
  api.get<{ success: boolean; query: string; cases: DiscoveredCase[]; total: number }>(
    `/ecourts/search-cases?q=${encodeURIComponent(q)}`,
    { timeout: 30000 }
  )

/** Full case detail from eCourts (parties, judges, hearing history, orders) for the case-details view */
export const getCaseByCnr = (cnr: string) =>
  api.get<{ success: boolean; cnr: string; case: CaseDetail }>(
    `/ecourts/case/${encodeURIComponent(cnr)}`,
    { timeout: 30000 }
  )

/**
 * Fetch the signed order PDF as a blob (proxied through our backend — the
 * order's `url` field is a bare filename like "order-1.pdf", not a link the
 * browser can hit directly; the vendor API needs our server-side Bearer token).
 */
export const getCaseOrderPdf = (cnr: string, filename: string) =>
  api.get(
    `/ecourts/case/${encodeURIComponent(cnr)}/order/${encodeURIComponent(filename)}`,
    { responseType: 'blob', timeout: 30000 }
  )

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
