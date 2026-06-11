import { useState, useEffect, useRef, useCallback } from 'react'
import { useMutation } from '@tanstack/react-query'
import DropZone from '@/components/ui/DropZone'
import Button from '@/components/ui/Button'
import MarkdownText, { renderInline } from '@/components/ui/MarkdownText'
import { streamExtractUpload, chatWithDocument } from '@/api/extract'
import { toast } from '@/store/toastStore'
import type {
  UniversalExtraction,
  ExtractionCaseNarrative,
  ExtractionIdentityField,
  ExtractionStakeholder,
  ExtractionDeadline,
  ExtractionConstraint,
  ExtractionActionItem,
  ExtractionCitation,
} from '@/types'

interface ChatMsg { role: 'user' | 'assistant'; content: string }

// ── History ──────────────────────────────────────────────────────────────────

const HISTORY_KEY = 'nikhar_extraction_history'
const MAX_HISTORY = 8

interface HistoryEntry {
  id: string
  filename: string
  sub_type: string
  category: string
  timestamp: string
  extraction: UniversalExtraction
}

function loadHistory(): HistoryEntry[] {
  try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]') } catch { return [] }
}

function saveToHistory(filename: string, extraction: UniversalExtraction) {
  const entry: HistoryEntry = {
    id: `${Date.now()}`,
    filename,
    sub_type: extraction.document_type?.sub_type || '',
    category: extraction.document_type?.category || '',
    timestamp: new Date().toISOString(),
    extraction,
  }
  const prev = loadHistory().filter(h => h.filename !== filename)
  const next = [entry, ...prev].slice(0, MAX_HISTORY)
  try { localStorage.setItem(HISTORY_KEY, JSON.stringify(next)) } catch {}
}

function removeFromHistory(id: string) {
  const next = loadHistory().filter(h => h.id !== id)
  try { localStorage.setItem(HISTORY_KEY, JSON.stringify(next)) } catch {}
}

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime()
  const m = Math.floor(diff / 60000)
  const h = Math.floor(m / 60)
  const d = Math.floor(h / 24)
  if (d > 0) return `${d}d ago`
  if (h > 0) return `${h}h ago`
  if (m > 0) return `${m}m ago`
  return 'just now'
}

// ── Helpers ──────────────────────────────────────────────────────────────────

const AMBER = 75

function toLabel(key: string) {
  return key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function isAmber(confidence: number) { return confidence > 0 && confidence < AMBER }

// Convert summary.value (string[] from new backend, legacy string from history)
// into a bullet array — no regex splitting needed.
function toSummaryBullets(value: string[] | string | null | undefined): string[] {
  if (!value) return []
  if (Array.isArray(value)) return value.filter(s => s?.length > 0)
  // Legacy: single string from old localStorage history — treat as one bullet
  return value.trim() ? [value.trim()] : []
}

function isLegalDocument(extraction: UniversalExtraction) {
  return extraction.document_type?.category === 'Legal'
}

// Keys that have special treatment or are shown in the Case Story — skip in Key Details
const LEGAL_NARRATIVE_KEYS = new Set([
  'key_issue', 'outcome', 'key_legal_question',
])

// Court decisions are flagged by the LLM — no string matching needed
function isCourtDecision(item: ExtractionActionItem): boolean {
  return item.is_court_decision === true
}

// Future deadlines are flagged by the LLM — no date math needed
function isFutureDeadline(item: ExtractionDeadline): boolean {
  return item.is_future === true
}

// ── Primitive renderers ───────────────────────────────────────────────────────

// Only show badge when amber — green fields have no badge
function AmberBadge({ confidence }: { confidence: number }) {
  if (!isAmber(confidence)) return null
  return (
    <span className="text-[9px] font-bold px-[5px] py-[1px] rounded-[4px] ml-[6px] flex-shrink-0 bg-amber-bg text-amber">
      {confidence}% ⚠
    </span>
  )
}

// Visible section header — same weight as ChatGPT's "Background", "Key Legal Issue"
function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <div className="text-[12px] font-bold text-text-1 mb-[10px]">
      {children}
    </div>
  )
}

// Sub-header inside Case Story (Background, Petitioner's Arguments, etc.)
function SubHeader({ children }: { children: React.ReactNode }) {
  return (
    <div className="text-[11px] font-bold text-text-2 mb-[6px]">
      {children}
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="px-4 py-[14px] border-b border-border-1 last:border-b-0">
      <SectionTitle>{title}</SectionTitle>
      {children}
    </div>
  )
}

function SeverityBadge({ severity }: { severity: string }) {
  const cls = severity === 'High' ? 'bg-red-50 text-red-600'
    : severity === 'Medium' ? 'bg-amber-bg text-amber'
    : 'bg-green-bg text-green'
  return <span className={`text-[9px] font-bold px-[5px] py-[1px] rounded-[4px] ${cls}`}>{severity}</span>
}

function BulletList({ items }: { items: string[] | null | undefined }) {
  if (!items?.length) return null
  return (
    <ul className="space-y-[6px]">
      {items.map((item, i) => (
        <li key={i} className="flex gap-[10px] text-[12.5px] text-text-1 leading-[1.55]">
          <span className="text-text-3 flex-shrink-0 mt-[2px] text-[10px]">●</span>
          <span>{renderInline(item)}</span>
        </li>
      ))}
    </ul>
  )
}

// Renders any field value: string, string[], object, number
function renderFieldValue(value: ExtractionIdentityField['value']): React.ReactNode {
  if (value == null) return null
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return <span className="text-[12.5px] text-text-1 leading-[1.55]">{String(value)}</span>
  }
  if (Array.isArray(value)) {
    return (
      <ul className="space-y-[3px] mt-[1px]">
        {value.map((item, i) => (
          <li key={i} className="flex gap-[8px] text-[12.5px] text-text-1 leading-[1.55]">
            <span className="text-text-3 flex-shrink-0 text-[10px] mt-[2px]">●</span>
            {typeof item === 'object' && item !== null
              ? renderFieldValue(item as Record<string, unknown>)
              : String(item)}
          </li>
        ))}
      </ul>
    )
  }
  if (typeof value === 'object') {
    const subEntries = Object.entries(value).filter(([, v]) => v != null)
    return (
      <div className="space-y-[5px] mt-[2px]">
        {subEntries.map(([k, v]) => (
          <div key={k} className="flex gap-[8px]">
            <span className="text-[11px] text-text-3 flex-shrink-0 min-w-[90px]">{toLabel(k)}</span>
            <span className="text-[12.5px] text-text-1 leading-[1.5]">
              {Array.isArray(v) ? (v as unknown[]).join(', ')
                : typeof v === 'object' && v !== null ? JSON.stringify(v)
                : String(v)}
            </span>
          </div>
        ))}
      </div>
    )
  }
  return null
}

// ── Case Story — shown for legal docs (narrative-first layout) ────────────────

function KeyLegalQuestionBox({ question }: { question: string }) {
  return (
    <div className="border border-border-2 rounded-sm px-[14px] py-[10px] bg-white">
      <div className="text-[11px] font-bold text-text-2 mb-[5px]">
        🔍 Key Legal Issue
      </div>
      <p className="text-[13px] font-medium text-text-1 leading-[1.55]">{question}</p>
    </div>
  )
}

function KeyTakeawayBox({ text }: { text: string }) {
  return (
    <div className="bg-green-bg border border-green rounded-sm px-[14px] py-[10px]">
      <div className="text-[11px] font-bold text-green mb-[4px]">
        ⚖ Key Takeaway
      </div>
      <p className="text-[12.5px] text-green leading-[1.55] font-medium">{renderInline(text)}</p>
    </div>
  )
}

// Helper: background can be string[] (new prompt) or legacy string
function BackgroundBullets({ background }: { background: string[] | string | null }) {
  if (!background) return null
  if (Array.isArray(background)) return <BulletList items={background} />
  // Legacy string — render as paragraph with inline markdown
  return <p className="text-[12.5px] text-text-1 leading-[1.6]">{renderInline(background)}</p>
}

// Full case_narrative layout (used when backend returns the new field)
function CaseNarrativeSection({ narrative, summaryValue }: {
  narrative: ExtractionCaseNarrative
  summaryValue?: string[] | string | null
}) {
  const hasBackground = Array.isArray(narrative.background)
    ? (narrative.background?.length ?? 0) > 0
    : !!narrative.background
  const hasPetArgs = (narrative.petitioner_arguments?.length ?? 0) > 0
  const hasRespArgs = (narrative.respondent_arguments?.length ?? 0) > 0
  const hasQuestion = !!narrative.key_legal_question
  const hasReasoning = (narrative.court_reasoning?.length ?? 0) > 0
  const hasTakeaway = !!narrative.key_takeaway

  if (!hasBackground && !hasPetArgs && !hasReasoning && !hasTakeaway && !hasQuestion) return null

  return (
    <div className="px-4 py-[14px] border-b border-border-1">
      <SectionTitle>Case Story</SectionTitle>
      <div className="space-y-[16px]">

        {/* Background */}
        {hasBackground && (
          <div>
            <SubHeader>Background</SubHeader>
            <BackgroundBullets background={narrative.background} />
          </div>
        )}

        {/* Petitioner's Arguments */}
        {hasPetArgs && (
          <div>
            <SubHeader>Petitioner's Argument</SubHeader>
            <BulletList items={narrative.petitioner_arguments} />
          </div>
        )}

        {/* Respondent's Arguments */}
        {hasRespArgs && (
          <div>
            <SubHeader>Respondent's Argument</SubHeader>
            <BulletList items={narrative.respondent_arguments} />
          </div>
        )}

        {/* Key Legal Issue */}
        {hasQuestion && <KeyLegalQuestionBox question={narrative.key_legal_question!} />}

        {/* Court's Findings */}
        {hasReasoning && (
          <div>
            <SubHeader>Court's Findings</SubHeader>
            <BulletList items={narrative.court_reasoning} />
          </div>
        )}

        {/* Decision */}
        {toSummaryBullets(summaryValue).length > 0 && (
          <div>
            <SubHeader>Decision</SubHeader>
            <BulletList items={toSummaryBullets(summaryValue)} />
          </div>
        )}

        {/* Key Takeaway */}
        {hasTakeaway && <KeyTakeawayBox text={narrative.key_takeaway!} />}

      </div>
    </div>
  )
}

// Fallback case story — built from identity_fields for current backend response
// Used when case_narrative is not yet returned by backend
function LegalSummarySection({ extraction }: { extraction: UniversalExtraction }) {
  const fields = extraction.identity_fields ?? {}
  const keyIssue = (fields.key_issue?.value || fields.key_legal_question?.value) as string | null
  const outcome = fields.outcome?.value as string | null
  const summaryBullets = toSummaryBullets(extraction.summary?.value)

  if (!keyIssue && !outcome && !summaryBullets.length) return null

  return (
    <div className="px-4 py-[14px] border-b border-border-1">
      <SectionTitle>Case Story</SectionTitle>
      <div className="space-y-[14px]">

        {summaryBullets.length > 0 && (
          <div>
            <SubHeader>What Happened</SubHeader>
            <BulletList items={summaryBullets} />
          </div>
        )}

        {keyIssue && <KeyLegalQuestionBox question={keyIssue} />}

        {outcome && (
          <div>
            <SubHeader>Decision</SubHeader>
            <p className="text-[12.5px] font-medium text-text-1 leading-[1.55]">{String(outcome)}</p>
          </div>
        )}

      </div>
    </div>
  )
}

// ── Section renderers ─────────────────────────────────────────────────────────

// Skips keys rendered in Case Story or already shown in the Parties section
const LEGAL_SKIP_KEYS = new Set([
  'key_issue', 'key_legal_question', 'outcome',
  // Party fields — rendered in StakeholdersSection, not in Key Details
  'petitioner', 'respondent', 'respondents', 'appellant',
  'petitioner_description', 'respondent_description',
  'appellant_description', 'respondent_name', 'petitioner_name',
])

function IdentityFieldsSection({ fields, skipKeys }: {
  fields: Record<string, ExtractionIdentityField>
  skipKeys?: Set<string>
}) {
  const entries = Object.entries(fields ?? {})
    .filter(([k, f]) => f?.value != null && !(skipKeys?.has(k)))
  if (!entries.length) return null
  return (
    <Section title="Key Details">
      <div className="space-y-[12px]">
        {entries.map(([key, field]) => (
          <div key={key}>
            <div className="flex items-center mb-[3px]">
              <span className="text-[11px] font-semibold text-text-2">{toLabel(key)}</span>
              <AmberBadge confidence={field.confidence} />
            </div>
            {renderFieldValue(field.value)}
          </div>
        ))}
      </div>
    </Section>
  )
}

function StakeholdersSection({ items }: { items: ExtractionStakeholder[] }) {
  const filtered = (items ?? []).filter(s => s.name)
  if (!filtered.length) return null
  return (
    <Section title="Parties">
      <div className="space-y-[10px]">
        {filtered.map((s, i) => (
          <div key={i} className="border-b border-border-1 last:border-b-0 pb-[10px] last:pb-0">
            <div className="flex items-baseline gap-[8px] mb-[2px] flex-wrap">
              <span className="text-[12.5px] font-semibold text-text-1">{s.name}</span>
              <span className="text-[11px] text-text-3">{s.role}</span>
            </div>
            {s.obligations && (
              <p className="text-[12px] text-text-2 leading-[1.5]">{s.obligations}</p>
            )}
          </div>
        ))}
      </div>
    </Section>
  )
}

function DeadlinesSection({ items }: { items: ExtractionDeadline[] }) {
  // Only show future actionable deadlines
  const filtered = (items ?? []).filter(d => d.label && isFutureDeadline(d))
  if (!filtered.length) return null
  return (
    <Section title="Deadlines">
      <div className="space-y-[7px]">
        {filtered.map((d, i) => (
          <div key={i} className="flex gap-[10px] items-start">
            <div className="flex-shrink-0 mt-[1px] bg-surface-3 text-text-2 text-[10px] font-semibold px-[7px] py-[2px] rounded-[4px] whitespace-nowrap">
              {d.date || '—'}
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-[6px]">
                <span className="text-[12px] font-medium text-text-1">{d.label}</span>
                <AmberBadge confidence={d.confidence} />
              </div>
              {d.consequence && (
                <p className="text-[11px] text-text-3 leading-[1.4] mt-[1px]">{d.consequence}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </Section>
  )
}

function ConstraintsSection({ items }: { items: ExtractionConstraint[] }) {
  const filtered = (items ?? []).filter(c => c.description)
  if (!filtered.length) return null
  return (
    <Section title="Legal Conditions">
      <div className="space-y-[8px]">
        {filtered.map((c, i) => (
          <div key={i} className="flex gap-[10px] items-start">
            <SeverityBadge severity={c.severity} />
            <p className="text-[12.5px] text-text-1 leading-[1.55] min-w-0 flex-1">{c.description}</p>
          </div>
        ))}
      </div>
    </Section>
  )
}

function ActionItemsSection({ items }: { items: ExtractionActionItem[] }) {
  // Filter out court decisions — only show future tasks for lawyer or parties
  const filtered = (items ?? []).filter(a => a.action && !isCourtDecision(a))

  if (!filtered.length) return null
  return (
    <Section title="Action Items">
      <div className="space-y-[7px]">
        {filtered.map((a, i) => (
          <div key={i} className="flex gap-[8px] items-start">
            <span className={`text-[9px] font-bold px-[5px] py-[1px] rounded-[4px] flex-shrink-0 mt-[1px] ${
              a.priority === 'Urgent' ? 'bg-red-50 text-red-600' :
              a.priority === 'High' ? 'bg-amber-bg text-amber' :
              'bg-surface-3 text-text-3'
            }`}>{a.priority}</span>
            <div className="min-w-0 flex-1">
              <p className="text-[12px] text-text-1 leading-[1.5]">{a.action}</p>
              {(a.by_whom || a.by_when) && (
                <p className="text-[11px] text-text-3 leading-[1.4] mt-[1px]">
                  {[a.by_whom, a.by_when].filter(Boolean).join(' · ')}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
    </Section>
  )
}

function CitationsSection({ items }: { items: ExtractionCitation[] }) {
  const filtered = (items ?? []).filter(c => c.case_name)
  if (!filtered.length) return null
  return (
    <Section title="Citations Relied On">
      <div className="space-y-[8px]">
        {filtered.map((c, i) => (
          <div key={i} className="flex items-start gap-[10px]">
            <span className={`text-[9px] font-bold px-[5px] py-[1px] rounded-[4px] flex-shrink-0 mt-[3px] ${
              c.relied_upon ? 'bg-green-bg text-green' : 'bg-surface-3 text-text-3'
            }`}>
              {c.relied_upon ? 'Relied on' : 'Mentioned'}
            </span>
            <div className="min-w-0">
              <span className="text-[12.5px] text-text-1 font-medium">{c.case_name}</span>
              {c.citation_string && (
                <p className="text-[11.5px] text-text-3 mt-[1px]">{c.citation_string}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </Section>
  )
}

// ── Extraction content router ─────────────────────────────────────────────────

function ExtractionContent({ extraction }: { extraction: UniversalExtraction }) {
  const isLegal = isLegalDocument(extraction)
  const narrative = extraction.case_narrative

  if (isLegal) {
    // Legal document layout — narrative-first
    return (
      <div>
        {/* Case Story: use rich narrative if backend returned it, else build from existing fields */}
        {narrative
          ? <CaseNarrativeSection narrative={narrative} summaryValue={extraction.summary?.value} />
          : <LegalSummarySection extraction={extraction} />
        }

        {/* Key Details — skip fields already shown in Case Story */}
        <IdentityFieldsSection
          fields={extraction.identity_fields}
          skipKeys={LEGAL_SKIP_KEYS}
        />

        <StakeholdersSection items={extraction.key_stakeholders} />

        {/* Future deadlines only */}
        <DeadlinesSection items={extraction.critical_deadlines} />

        {/* Legal conditions from constraints */}
        <ConstraintsSection items={extraction.constraints_and_risks} />

        {/* Only non-court-decision action items */}
        <ActionItemsSection items={extraction.action_items} />

        <CitationsSection items={extraction.citations} />
      </div>
    )
  }

  // Non-legal: original structured layout
  return (
    <div>
      <Section title="Summary">
        <div className="space-y-[10px]">
          {toSummaryBullets(extraction.summary?.value).length > 0 && (
            <div>
              <div className="flex items-center mb-[5px]">
                <span className="text-[11px] font-bold text-text-2">What happened</span>
                <AmberBadge confidence={extraction.summary.confidence} />
              </div>
              <BulletList items={toSummaryBullets(extraction.summary.value)} />
            </div>
          )}
          {extraction.primary_objective?.value && (
            <div>
              <div className="flex items-center mb-[5px]">
                <span className="text-[11px] font-bold text-text-2">Primary objective</span>
                <AmberBadge confidence={extraction.primary_objective.confidence} />
              </div>
              <p className="text-[12.5px] text-text-1 leading-[1.6]">{extraction.primary_objective.value}</p>
            </div>
          )}
        </div>
      </Section>
      <IdentityFieldsSection fields={extraction.identity_fields} />
      <StakeholdersSection items={extraction.key_stakeholders} />
      <DeadlinesSection items={extraction.critical_deadlines} />
      <ConstraintsSection items={extraction.constraints_and_risks} />
      <ActionItemsSection items={extraction.action_items} />
      <CitationsSection items={extraction.citations} />
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

// Loading stage labels shown to the user
const STAGE_LABELS: Record<string, string> = {
  reading:   'Reading document…',
  analysing: 'Analysing with AI…',
  generating:'Extracting fields…',
}

export default function PdfExtractorPage() {
  const [filename, setFilename] = useState('')
  const [extraction, setExtraction] = useState<UniversalExtraction | null>(null)
  const [documentId, setDocumentId] = useState<string | null>(null)
  const [chatMsgs, setChatMsgs] = useState<ChatMsg[]>([])
  const [question, setQuestion] = useState('')
  const [history, setHistory] = useState<HistoryEntry[]>(loadHistory)
  const [loadingStage, setLoadingStage] = useState<string | null>(null)
  const [loadingPct, setLoadingPct] = useState(0)
  const [streamingText, setStreamingText] = useState('')

  // Token accumulation refs — avoid React batching eating our updates
  // Tokens land in the ref synchronously; a 50ms interval flushes them to state
  const pendingTokensRef = useRef('')
  const flushTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const streamBoxRef = useRef<HTMLDivElement>(null)
  const chatBottomRef = useRef<HTMLDivElement>(null)

  const isExtracting = loadingStage !== null

  // Auto-scroll the streaming text box as tokens arrive
  useEffect(() => {
    if (streamBoxRef.current) {
      streamBoxRef.current.scrollTop = streamBoxRef.current.scrollHeight
    }
  }, [streamingText])

  // Start 50ms flush interval — gives smooth ~20fps text updates
  const startFlushTimer = useCallback(() => {
    if (flushTimerRef.current) clearInterval(flushTimerRef.current)
    flushTimerRef.current = setInterval(() => {
      if (pendingTokensRef.current) {
        const chunk = pendingTokensRef.current
        pendingTokensRef.current = ''
        setStreamingText(prev => prev + chunk)
      }
    }, 50)
  }, [])

  const stopFlushTimer = useCallback(() => {
    if (flushTimerRef.current) {
      clearInterval(flushTimerRef.current)
      flushTimerRef.current = null
    }
    // Flush any remaining tokens that arrived after the last tick
    if (pendingTokensRef.current) {
      const chunk = pendingTokensRef.current
      pendingTokensRef.current = ''
      setStreamingText(prev => prev + chunk)
    }
  }, [])

  // Chat still uses React Query mutation

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMsgs])

  useEffect(() => { setChatMsgs([]) }, [documentId])

  const chatMutation = useMutation({
    mutationFn: ({ id, msgs }: { id: string; msgs: ChatMsg[] }) =>
      chatWithDocument(id, msgs),
    onSuccess: ({ data }, { msgs }) => {
      setChatMsgs([
        ...msgs,
        { role: 'assistant', content: (data.data as any).answer as string },
      ])
    },
    onError: () => toast('Could not get an answer. Try again.'),
  })

  const handleFile = useCallback(async (file: File) => {
    if (file.size > 50 * 1024 * 1024) { toast('File too large — max 50MB'); return }

    // Reset all state + refs
    pendingTokensRef.current = ''
    setFilename(file.name)
    setExtraction(null)
    setDocumentId(null)
    setChatMsgs([])
    setStreamingText('')
    setLoadingStage('reading')
    setLoadingPct(0)

    // Start the 50ms flush interval — React 18 batches synchronous state updates,
    // so we write tokens to a ref and flush to state on a timer instead.
    startFlushTimer()

    try {
      await streamExtractUpload(
        file,
        // onToken — write to ref only (no React re-render per token)
        // the 50ms interval flushes these to state → smooth visible streaming
        (text) => { pendingTokensRef.current += text },
        // onProgress — real stage/pct from SSE
        (stage, pct) => {
          setLoadingStage(stage)
          if (pct !== undefined) setLoadingPct(pct)
        },
        // onResult — flush last tokens, then show structured view
        (data) => {
          stopFlushTimer()
          setExtraction(data)
          saveToHistory(file.name, data)
          setHistory(loadHistory())
          setDocumentId(data.document_id ?? null)
          setLoadingStage(null)
          setLoadingPct(0)
          setStreamingText('')
        },
        // onError
        (_code, message) => {
          stopFlushTimer()
          toast(message || 'Extraction failed. Check file format and try again.')
          setFilename('')
          setLoadingStage(null)
          setStreamingText('')
        },
      )
    } catch {
      stopFlushTimer()
      toast('Extraction failed. Check file format and try again.')
      setFilename('')
      setLoadingStage(null)
      setStreamingText('')
    }
  }, [startFlushTimer, stopFlushTimer])

  const handleLoadHistory = (entry: HistoryEntry) => {
    setFilename(entry.filename)
    setExtraction(entry.extraction)
    setDocumentId(null)
    setChatMsgs([])
    setLoadingStage(null)
  }

  const handleDeleteHistory = (e: React.MouseEvent, id: string) => {
    e.stopPropagation()
    removeFromHistory(id)
    setHistory(loadHistory())
  }

  const handleAsk = () => {
    if (!question.trim() || !documentId) return
    const updatedMsgs: ChatMsg[] = [...chatMsgs, { role: 'user', content: question }]
    setChatMsgs(updatedMsgs)
    chatMutation.mutate({ id: documentId, msgs: updatedMsgs })
    setQuestion('')
  }

  const handleReset = () => {
    stopFlushTimer()
    pendingTokensRef.current = ''
    setFilename('')
    setExtraction(null)
    setDocumentId(null)
    setChatMsgs([])
    setLoadingStage(null)
    setLoadingPct(0)
    setStreamingText('')
  }

  // ── Landing screen ────────────────────────────────────────────────────────

  if (!filename || (!isExtracting && !extraction)) {
    return (
      <div className="max-w-[520px] mx-auto mt-9 px-2">
        <DropZone onFile={handleFile} />

        {isExtracting && (
          <div className="mt-5">
            <div className="flex items-center justify-center gap-2 text-[12px] text-text-2 mb-3">
              <svg className="animate-spin h-4 w-4 text-ink flex-shrink-0" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              {STAGE_LABELS[loadingStage!] ?? 'Processing…'}
            </div>
            {loadingStage === 'generating' && loadingPct > 0 && (
              <>
                <div className="w-full bg-surface-3 rounded-full h-[3px] overflow-hidden mb-3">
                  <div
                    className="bg-ink h-[3px] rounded-full transition-all duration-300"
                    style={{ width: `${loadingPct}%` }}
                  />
                </div>
                {/* Mini streaming preview on landing */}
                {streamingText && (
                  <div className="mt-2 max-h-[80px] overflow-hidden rounded-sm bg-surface-2 border border-border-1 px-[10px] py-[8px] font-mono text-[9.5px] text-text-3 leading-[1.6] whitespace-pre-wrap relative">
                    {streamingText.slice(-300)}
                    <div className="absolute bottom-0 left-0 right-0 h-[24px] bg-gradient-to-t from-surface-2 to-transparent" />
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {history.length > 0 && !isExtracting && (
          <div className="mt-6">
            <div className="text-[9.5px] font-bold tracking-[0.6px] uppercase text-text-3 mb-[8px]">
              Recently Extracted
            </div>
            <div className="space-y-[5px]">
              {history.map(h => (
                <div
                  key={h.id}
                  onClick={() => handleLoadHistory(h)}
                  className="group flex items-center gap-[10px] px-[12px] py-[9px] bg-white border border-border-1 rounded-sm cursor-pointer hover:border-border-2 hover:bg-surface-2 transition-colors"
                >
                  <span className="text-[14px] flex-shrink-0">📄</span>
                  <div className="flex-1 min-w-0">
                    <div className="text-[12px] font-medium text-text-1 truncate">{h.filename}</div>
                    <div className="flex items-center gap-[6px] mt-[1px]">
                      {h.sub_type && (
                        <span className="text-[9.5px] text-text-3 bg-surface-3 px-[5px] py-[1px] rounded-full">
                          {h.sub_type}
                        </span>
                      )}
                      <span className="text-[10px] text-text-3">{timeAgo(h.timestamp)}</span>
                    </div>
                  </div>
                  <button
                    onClick={e => handleDeleteHistory(e, h.id)}
                    className="opacity-0 group-hover:opacity-100 text-text-3 hover:text-text-1 text-[14px] leading-none transition-opacity flex-shrink-0"
                    title="Remove"
                  >×</button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    )
  }

  // ── Extraction view ───────────────────────────────────────────────────────

  const docType = extraction?.document_type

  return (
    <div
      className="h-[calc(100vh-50px-44px)] md:h-[calc(100vh-50px)] grid border border-border-1 rounded-DEFAULT overflow-hidden shadow-[0_1px_4px_rgba(0,0,0,0.05)]"
      style={{ gridTemplateColumns: '1fr 1fr' }}
    >
      {/* LEFT: Extracted intelligence */}
      <div className="flex flex-col bg-white overflow-x-hidden">
        <div className="h-11 flex-shrink-0 px-[14px] border-b border-border-1 flex items-center justify-between">
          <div className="flex items-center gap-[7px] min-w-0">
            <span className="text-[12px] font-bold text-text-1 truncate">📄 {filename}</span>
            {docType && (
              <span className="text-[9.5px] font-semibold px-[7px] py-[2px] bg-surface-3 text-text-2 rounded-full flex-shrink-0">
                {docType.sub_type || docType.category}
              </span>
            )}
          </div>
          <Button size="sm" onClick={handleReset} className="flex-shrink-0 ml-2">← Back</Button>
        </div>

        <div className="flex-1 overflow-y-auto flex flex-col min-h-0">
          {isExtracting ? (
            <div className="flex flex-col items-center justify-center h-full gap-[20px] px-[32px]">

              {/* Spinner */}
              <svg className="animate-spin h-[22px] w-[22px] text-text-3" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2.5" />
                <path className="opacity-80" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>

              {/* Stage label */}
              <div className="text-center">
                <div className="text-[13px] font-semibold text-text-1 mb-[4px]">
                  {STAGE_LABELS[loadingStage!] ?? 'Processing…'}
                </div>
                <div className="text-[11px] text-text-3">
                  {loadingStage === 'reading'   && 'Extracting text from document'}
                  {loadingStage === 'analysing' && 'AI is reading the document'}
                  {loadingStage === 'generating' && 'Building structured intelligence'}
                </div>
              </div>

              {/* Progress bar — only during generating stage */}
              {loadingStage === 'generating' && loadingPct > 0 && (
                <div className="w-full max-w-[240px]">
                  <div className="w-full bg-surface-3 rounded-full h-[4px] overflow-hidden">
                    <div
                      className="bg-ink h-full rounded-full transition-all duration-300"
                      style={{ width: `${loadingPct}%` }}
                    />
                  </div>
                  <div className="flex justify-between mt-[5px]">
                    <span className="text-[10px] text-text-3">Extracting fields…</span>
                    <span className="text-[10px] text-text-3 font-medium">{loadingPct}%</span>
                  </div>
                </div>
              )}

              {/* Animated dots showing activity during analysing */}
              {loadingStage === 'analysing' && (
                <div className="flex gap-[5px]">
                  {[0, 1, 2].map(i => (
                    <span
                      key={i}
                      className="w-[6px] h-[6px] rounded-full bg-text-3 animate-pulseDot"
                      style={{ animationDelay: `${i * 0.3}s` }}
                    />
                  ))}
                </div>
              )}

            </div>
          ) : extraction ? (
            <ExtractionContent extraction={extraction} />
          ) : null}
        </div>
      </div>

      {/* RIGHT: Chat */}
      <div className="flex flex-col bg-white border-l border-border-1 overflow-x-hidden">
        <div className="h-11 flex-shrink-0 px-[14px] border-b border-border-1 flex items-center justify-between">
          <span className="text-[12px] font-bold text-text-1">💬 Chat with Document</span>
          {chatMsgs.length > 0 && (
            <button
              onClick={() => setChatMsgs([])}
              className="text-[11px] text-text-3 hover:text-text-1 transition-colors"
            >Clear</button>
          )}
        </div>

        <div className="flex-1 overflow-y-auto p-3">
          <div className="bg-surface-2 rounded-sm px-[11px] py-[9px] mb-2 text-[12.5px] text-text-2">
            {documentId
              ? <><strong>{filename}</strong> is ready. Ask me anything.</>
              : <span className="text-text-3 italic">Indexing document for chat…</span>
            }
          </div>
          {chatMsgs.map((m, i) => (
            m.role === 'user' ? (
              <div key={i} className="bg-white border border-border-1 rounded-sm px-[11px] py-[9px] mb-[7px]">
                <div className="text-[10px] font-bold text-text-3 mb-[3px] uppercase tracking-[0.4px]">You asked</div>
                <div className="text-[12.5px] text-text-1">{m.content}</div>
              </div>
            ) : (
              <div key={i} className="bg-surface-2 border-l-[3px] border-ink rounded-r-sm px-[11px] py-[9px] mb-2">
                <MarkdownText text={m.content} />
              </div>
            )
          ))}
          {chatMutation.isPending && (
            <div className="text-[11px] text-text-3 italic px-1">Thinking…</div>
          )}
          <div ref={chatBottomRef} />
        </div>

        <div className="border-t border-border-1 p-[11px] bg-surface-2 flex-shrink-0">
          <input
            className="w-full px-[11px] py-2 border border-border-1 rounded-sm bg-white text-text-1 font-sans text-[12.5px] outline-none focus:border-border-2 transition-colors disabled:opacity-50"
            placeholder={documentId ? 'Ask a question about this document…' : 'Indexing for chat…'}
            disabled={!documentId || chatMutation.isPending}
            value={question}
            onChange={e => setQuestion(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleAsk()}
          />
        </div>
      </div>
    </div>
  )
}
