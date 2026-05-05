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

export interface UnifiedSearchResponse {
  success: boolean
  query: string
  from_your_files: OwnFileResult[]
  from_public_judgments: PublicJudgmentResult[]
  total_results: number
  duration_ms: number
}

export interface Deadline {
  id: string
  matter_title: string
  court: string
  case_number?: string
  deadline_type: 'hearing' | 'filing' | 'limitation'
  due_date: string
  status: 'upcoming' | 'urgent' | 'missed'
  whatsapp_enabled: boolean
  client_phone?: string
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

export interface ExtractionIdentityField {
  value: string | string[] | Record<string, unknown> | null
  confidence: number
}

export interface ExtractionStakeholder {
  name: string
  role: string
  obligations: string | null
  confidence: number
}

export interface ExtractionDeadline {
  label: string
  date: string
  consequence: string | null
  confidence: number
}

export interface ExtractionConstraint {
  type: string
  description: string
  severity: 'High' | 'Medium' | 'Low'
  confidence: number
}

export interface ExtractionActionItem {
  action: string
  by_whom: string | null
  by_when: string | null
  priority: 'Urgent' | 'High' | 'Normal'
}

export interface ExtractionCitation {
  case_name: string
  citation_string: string
  relied_upon: boolean
  confidence: number
}

export interface ExtractionCaseNarrative {
  background: string | null
  petitioner_arguments: string[]
  respondent_arguments: string[]
  key_legal_question: string | null
  court_reasoning: string[]
  key_takeaway: string | null
}

export interface UniversalExtraction {
  document_id: string
  document_type: {
    category: string
    sub_type: string
    confidence: number
  }
  identity_fields: Record<string, ExtractionIdentityField>
  summary: { value: string | null; confidence: number }
  primary_objective: { value: string | null; confidence: number }
  case_narrative?: ExtractionCaseNarrative | null
  key_stakeholders: ExtractionStakeholder[]
  critical_deadlines: ExtractionDeadline[]
  constraints_and_risks: ExtractionConstraint[]
  action_items: ExtractionActionItem[]
  citations: ExtractionCitation[]
}
