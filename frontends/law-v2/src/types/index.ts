export interface ApiResponse<T = unknown> {
  success: boolean
  data: T
  error?: { code: string; message: string; action?: string }
  meta?: { request_id: string; version: string }
}

export interface User {
  id: string
  email: string
  full_name: string
  role: 'super_admin' | 'firm_admin' | 'lawyer' | 'staff' | 'trial'
  firm_id: string
  firm_name: string
  plan: string
  initials: string
}

export interface AuthTokens {
  access_token: string
  token_type: string
}

export interface Document {
  id: string
  filename: string
  status: 'pending' | 'processing' | 'indexed' | 'failed'
  error_reason?: string
  created_at: string
}

export interface SearchResult {
  id: string
  case_name: string
  court: string
  year: number
  citation?: string
  source_url?: string
  excerpt: string
  score: number
  source: 'public_judgment' | 'own_file'
  verified: boolean
}

export interface PublicJudgmentResult {
  id: string
  case_name: string
  petitioner?: string
  respondent?: string
  court: string
  year: number
  citation_key: string
  primary_citation?: string
  summary?: string
  judgment_url?: string
  official_source_url?: string
  link_status?: string
  source_url?: string
  official_source?: string
  matter_type?: string
  outcome?: string
  relevance_score: number
  result_type: string
  enrichment?: {
    facts?: string
    issue?: string
    reasoning?: string
    ratio?: string
    relevance?: string
  } | null
}

export interface OwnFileResult {
  document_id: string
  document_name: string
  page?: number
  excerpt: string
  relevance_score: number
  confidence: number
  result_type: string
}

export interface SearchAnalysis {
  trend?: string
  winning_factors: string[]
  risk_factors: string[]
  strongest_case?: string
  practical_advice?: string
  relevance_per_case?: Record<string, string>
}

export interface UnifiedSearchResponse {
  success: boolean
  query: string
  from_your_files: OwnFileResult[]
  from_public_judgments: PublicJudgmentResult[]
  overall_analysis?: SearchAnalysis | null
  total_results: number
  duration_ms: number
}

export interface Deadline {
  id: string
  matter_id: string
  matter_title: string
  court: string | null
  case_number: string | null
  /** Matches law.ReminderType on the backend. */
  deadline_type: 'hearing' | 'filing_deadline' | 'limitation_period' | 'urgent'
  title: string
  description: string | null
  /** The key date (ISO, UTC). */
  due_date: string
  reminder_date: string
  days_remaining: number
  /** Derived from the key date — what the UI groups and colours by. */
  urgency: 'upcoming' | 'urgent' | 'missed'
  /** Reminder delivery state, NOT urgency. */
  delivery_status: 'pending' | 'sent' | 'missed'
  whatsapp_enabled: boolean
}

export interface Draft {
  id: string
  filing_type: string
  objective: string
  petitioner: string
  respondent: string
  court: string
  sections: Record<string, string>
  citations_used: string[]
  quality_score: number
  created_at: string
}

export type CaseStatus = 'active' | 'disposed' | 'stayed' | 'settled'

export type MatterType =
  | 'bail'
  | 'writ'
  | 'civil'
  | 'criminal'
  | 'cheque_bounce'
  | 'matrimonial'
  | 'consumer'
  | 'property'
  | 'other'

export interface CasePerson {
  id: string
  role: 'client' | 'opponent' | 'opp_counsel' | 'judge' | 'witness' | 'other'
  name: string
  phone?: string
  notes?: string
}

export interface CaseHearing {
  id: string
  date: string
  notes?: string
  outcome?: string
}

export interface CasePayment {
  id: string
  label: string
  amount: number
  due_date?: string
  paid: boolean
  paid_date?: string
}

export interface LegalCase {
  id: string
  case_number?: string
  title: string
  court: string
  matter_type: MatterType
  status: CaseStatus
  filing_date?: string
  next_hearing?: string
  total_fees?: number
  persons: CasePerson[]
  hearings: CaseHearing[]
  payments: CasePayment[]
  notes?: string
  created_at: string
  updated_at: string
}
