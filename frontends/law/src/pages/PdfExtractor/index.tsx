import { useState, useEffect, useRef, useCallback } from 'react'
import DropZone from '@/components/ui/DropZone'
import Button from '@/components/ui/Button'
import MarkdownText from '@/components/ui/MarkdownText'
import { streamExtractUpload, chatWithDocument, streamChatWithDocument } from '@/api/extract'
import { toast } from '@/store/toastStore'

interface ChatMsg { role: 'user' | 'assistant'; content: string }

// ── History ──────────────────────────────────────────────────────────────────

const HISTORY_KEY = 'nikhar_extraction_history'
const MAX_HISTORY = 8

interface HistoryEntry {
  id: string
  filename: string
  timestamp: string
  markdown: string   // the streamed analysis text
}

function loadHistory(): HistoryEntry[] {
  try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]') } catch { return [] }
}

function saveToHistory(filename: string, markdown: string) {
  const entry: HistoryEntry = {
    id: `${Date.now()}`,
    filename,
    timestamp: new Date().toISOString(),
    markdown,
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

// ── Incremental JSON parser ───────────────────────────────────────────────────
// Attempts to parse a partial/incomplete JSON string by repairing truncated
// content. Returns whatever top-level fields are complete enough to render.



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

// ── Case Snapshot card ────────────────────────────────────────────────────────
// Populated from the SNAPSHOT: line the model emits as the very first line of
// the stream — appears within 1-2 seconds, long before streaming completes.

interface SnapshotData {
  document_type?: string | null
  outcome?: string | null
  court?: string | null
  judge?: string | null
  date?: string | null
  case_no?: string | null
  appellant?: string | null
  respondent?: string | null
}

function formatSnapshotDate(d: string): string {
  if (!d) return d
  try {
    // YYYY-MM-DD
    const iso = d.match(/^(\d{4})-(\d{2})-(\d{2})$/)
    if (iso) {
      const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
      return `${parseInt(iso[3])} ${months[parseInt(iso[2]) - 1]} ${iso[1]}`
    }
    // DD.MM.YYYY
    const dmy = d.match(/^(\d{1,2})\.(\d{2})\.(\d{4})$/)
    if (dmy) {
      const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
      return `${parseInt(dmy[1])} ${months[parseInt(dmy[2]) - 1]} ${dmy[3]}`
    }
  } catch {}
  return d
}

function CaseSnapshotCard({ snapshot }: { snapshot: SnapshotData }) {
  const outcome = snapshot.outcome
  const outcomeLabel =
    outcome === 'allowed'   ? 'Appeal Allowed' :
    outcome === 'dismissed' ? 'Dismissed'       :
    outcome === 'pending'   ? 'Pending'         : null
  const outcomeColor =
    outcome === 'allowed'   ? 'text-green'   :
    outcome === 'dismissed' ? 'text-red-600' : 'text-text-2'
  const outcomeIcon =
    outcome === 'allowed'   ? '✓' :
    outcome === 'dismissed' ? '✗' : '○'

  // Strip title prefixes (Sh., Shri, Hon., Dr.) and designation suffixes
  const judgeDisplay = snapshot.judge
    ?.replace(/^(sh\.|shri\.?|hon\.?|dr\.?)\s*/i, '')
    ?.replace(/,\s*(district\s+judge|additional\s+district\s+judge|senior\s+civil\s+judge|civil\s+judge|sessions\s+judge|additional\s+sessions|chief\s+judicial|judicial\s+magistrate)[^,]*/i, '')
    ?.trim() || null

  const metaParts = [
    snapshot.date   && `Decision: ${formatSnapshotDate(snapshot.date)}`,
    judgeDisplay    && `Judge: ${judgeDisplay}`,
    snapshot.case_no && `Case No: ${snapshot.case_no}`,
  ].filter(Boolean)

  const docType = snapshot.document_type

  // Don't render an empty card — only show what the document actually supports.
  if (!docType && !outcomeLabel && !snapshot.court && !snapshot.appellant && !snapshot.respondent) return null

  return (
    <div className="border border-border-1 rounded-sm mb-[16px] overflow-hidden">
      {/* Document type + outcome + court + meta */}
      <div className="px-[14px] pt-[11px] pb-[10px] bg-surface-2 border-b border-border-1">
        {docType && (
          <div className="text-[9.5px] font-bold uppercase tracking-[0.5px] text-text-3 mb-[5px]">
            {docType}
          </div>
        )}
        {outcomeLabel && (
          <div className={`text-[13px] font-bold mb-[3px] ${outcomeColor}`}>
            {outcomeIcon} {outcomeLabel}
          </div>
        )}
        {snapshot.court && <div className="text-[12px] text-text-2 leading-[1.4]">{snapshot.court}</div>}
        {metaParts.length > 0 && (
          <div className="text-[11px] text-text-3 mt-[4px] leading-[1.5]">
            {metaParts.join(' · ')}
          </div>
        )}
      </div>

      {/* Parties */}
      {(snapshot.appellant || snapshot.respondent) && (
        <div className="flex divide-x divide-border-1">
          {snapshot.appellant && (
            <div className="flex-1 px-[14px] py-[9px] min-w-0">
              <div className="text-[9.5px] font-bold uppercase tracking-[0.5px] text-text-3 mb-[2px]">Appellant</div>
              <div className="text-[12px] font-semibold text-text-1 leading-[1.35] truncate">{snapshot.appellant}</div>
            </div>
          )}
          {snapshot.respondent && (
            <div className="flex-1 px-[14px] py-[9px] min-w-0">
              <div className="text-[9.5px] font-bold uppercase tracking-[0.5px] text-text-3 mb-[2px]">Respondent</div>
              <div className="text-[12px] font-semibold text-text-1 leading-[1.35] truncate">{snapshot.respondent}</div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

// Loading stage labels shown to the user
export default function PdfExtractorPage() {
  const [filename, setFilename] = useState('')
  const [streamText, setStreamText] = useState('')   // the rendered result — stays forever
  const [isExtracting, setIsExtracting] = useState(false)
  const [loadingStage, setLoadingStage] = useState<string>('reading')
  const [documentId, setDocumentId] = useState<string | null>(null)
  const [chatMsgs, setChatMsgs] = useState<ChatMsg[]>([])
  const [question, setQuestion] = useState('')
  const [history, setHistory] = useState<HistoryEntry[]>(loadHistory)
  const [rightTab, setRightTab] = useState<'pdf' | 'chat'>('pdf')
  const [fileUrl, setFileUrl] = useState<string | null>(null)

  const tokenBufRef = useRef('')
  const flushTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const snapshotParsedRef = useRef(false)
  const snapshotBufRef = useRef('')
  const streamScrollRef = useRef<HTMLDivElement>(null)
  const chatBottomRef = useRef<HTMLDivElement>(null)

  const hasContent = streamText.length > 0

  // No auto-scroll — content grows downward, user reads from the top.

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMsgs])

  useEffect(() => { setChatMsgs([]) }, [documentId])

  const [isChatPending, setIsChatPending] = useState(false)
  const [snapshot, setSnapshot] = useState<SnapshotData | null>(null)

  const handleFile = useCallback(async (file: File) => {
    if (file.size > 50 * 1024 * 1024) { toast('File too large — max 50MB'); return }

    tokenBufRef.current = ''
    snapshotParsedRef.current = false
    snapshotBufRef.current = ''
    setFilename(file.name)
    setStreamText('')
    setDocumentId(null)
    setChatMsgs([])
    setSnapshot(null)
    setIsExtracting(true)
    setLoadingStage('reading')
    setRightTab('pdf')
    setFileUrl(prev => { if (prev) URL.revokeObjectURL(prev); return URL.createObjectURL(file) })
    // Ensure the document panel starts at the top when a new file is loaded
    if (streamScrollRef.current) streamScrollRef.current.scrollTop = 0

    flushTimerRef.current = setInterval(() => {
      if (tokenBufRef.current) {
        const chunk = tokenBufRef.current
        tokenBufRef.current = ''
        setStreamText(prev => prev + chunk)
      }
    }, 50)

    const cleanup = () => {
      clearInterval(flushTimerRef.current!)
      flushTimerRef.current = null
      // Flush any unprocessed snapshot buffer as plain text
      if (!snapshotParsedRef.current) {
        snapshotParsedRef.current = true
        tokenBufRef.current += snapshotBufRef.current
        snapshotBufRef.current = ''
      }
      if (tokenBufRef.current) {
        const chunk = tokenBufRef.current
        tokenBufRef.current = ''
        setStreamText(prev => prev + chunk)
      }
    }

    // Token handler — intercepts the first line to extract SNAPSHOT: data.
    // The model outputs SNAPSHOT:{...json...} as the very first line of the
    // stream. We parse it immediately (within 1-2s) to populate the card,
    // then discard that line so it never appears in the rendered markdown.
    const handleToken = (text: string) => {
      if (!snapshotParsedRef.current) {
        snapshotBufRef.current += text
        const newlineIdx = snapshotBufRef.current.indexOf('\n')
        if (newlineIdx !== -1) {
          snapshotParsedRef.current = true
          const firstLine = snapshotBufRef.current.slice(0, newlineIdx)
          const rest = snapshotBufRef.current.slice(newlineIdx + 1)
          snapshotBufRef.current = ''
          if (firstLine.startsWith('SNAPSHOT:')) {
            try { setSnapshot(JSON.parse(firstLine.slice(9))) } catch {}
            tokenBufRef.current += rest   // skip the SNAPSHOT line itself
          } else {
            tokenBufRef.current += firstLine + '\n' + rest   // not a snapshot — keep it
          }
        }
        return
      }
      tokenBufRef.current += text
    }

    try {
      await streamExtractUpload(
        file,
        handleToken,
        (stage) => setLoadingStage(stage),
        ({ document_id }) => {
          cleanup()
          setDocumentId(document_id)
          setIsExtracting(false)
          setStreamText(prev => {
            saveToHistory(file.name, prev)
            setHistory(loadHistory())
            return prev
          })
        },
        (_code, message) => {
          cleanup()
          toast(message || 'Extraction failed. Check file format and try again.')
          setFilename('')
          setStreamText('')
          setIsExtracting(false)
        },
        // document_ready fires when text is saved to DB, before LLM tokens start.
        // Set documentId here so chat is available during streaming (not just after).
        (document_id) => { setDocumentId(document_id) },
      )
    } catch {
      cleanup()
      toast('Extraction failed. Check file format and try again.')
      setFilename('')
      setStreamText('')
      setIsExtracting(false)
    }
  }, [])

  const handleLoadHistory = (entry: HistoryEntry) => {
    setFilename(entry.filename)
    setStreamText(entry.markdown)
    setDocumentId(null)
    setChatMsgs([])
    setIsExtracting(false)
  }

  const handleDeleteHistory = (e: React.MouseEvent, id: string) => {
    e.stopPropagation()
    removeFromHistory(id)
    setHistory(loadHistory())
  }

  const handleAsk = async () => {
    if (!question.trim() || !documentId || isChatPending) return
    const updatedMsgs: ChatMsg[] = [...chatMsgs, { role: 'user', content: question }]
    setChatMsgs(updatedMsgs)
    setQuestion('')
    setIsChatPending(true)
    try {
      const { data } = await chatWithDocument(documentId, updatedMsgs)
      setChatMsgs([...updatedMsgs, { role: 'assistant', content: (data.data as any).answer as string }])
    } catch {
      toast('Could not get an answer. Try again.')
    } finally {
      setIsChatPending(false)
    }
  }

  const handleQuickPrompt = async (prompt: string) => {
    if (!documentId || isChatPending) return
    // The answer streams into the chat panel — surface it so the user sees it arrive.
    setRightTab('chat')
    const userMsgs: ChatMsg[] = [...chatMsgs, { role: 'user', content: prompt }]
    const allMsgs: ChatMsg[] = [...userMsgs, { role: 'assistant', content: '' }]
    setChatMsgs(allMsgs)
    setIsChatPending(true)
    setTimeout(() => chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' }), 50)
    await streamChatWithDocument(
      documentId,
      userMsgs,
      (chunk) => {
        setChatMsgs(prev => {
          const next = [...prev]
          next[next.length - 1] = { role: 'assistant', content: next[next.length - 1].content + chunk }
          return next
        })
        chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' })
      },
      () => setIsChatPending(false),
      (msg) => { toast(msg || 'Could not get an answer. Try again.'); setIsChatPending(false) },
    )
  }

  const handleReset = () => {
    clearInterval(flushTimerRef.current!)
    flushTimerRef.current = null
    tokenBufRef.current = ''
    snapshotParsedRef.current = false
    snapshotBufRef.current = ''
    setFilename('')
    setStreamText('')
    setDocumentId(null)
    setChatMsgs([])
    setSnapshot(null)
    setIsExtracting(false)
    setFileUrl(prev => { if (prev) URL.revokeObjectURL(prev); return null })
    setRightTab('pdf')
  }

  // ── Landing screen ────────────────────────────────────────────────────────

  if (!filename) {
    return (
      <div className="max-w-[520px] mx-auto mt-9 px-2">
        <DropZone onFile={handleFile} />

        {history.length > 0 && (
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
                    <span className="text-[10px] text-text-3">{timeAgo(h.timestamp)}</span>
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

  // ── Document view ─────────────────────────────────────────────────────────

  return (
    <div
      className="h-[calc(100vh-50px-44px)] md:h-[calc(100vh-50px)] grid border border-border-1 rounded-DEFAULT overflow-hidden shadow-[0_1px_4px_rgba(0,0,0,0.05)]"
      style={{ gridTemplateColumns: '1fr 1fr' }}
    >
      {/* LEFT: Document analysis */}
      <div className="flex flex-col bg-white overflow-x-hidden">
        <div className="h-11 flex-shrink-0 px-[14px] border-b border-border-1 flex items-center justify-between gap-2">
          <span className="text-[12px] font-bold text-text-1 truncate min-w-0">📄 {filename}</span>
          {isExtracting && (
            <span className="text-[10px] text-text-3 flex items-center gap-[6px] flex-shrink-0">
              <svg className="animate-spin h-[11px] w-[11px]" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2.5"/>
                <path className="opacity-80" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
              </svg>
              {loadingStage === 'reading' ? 'Reading…' : 'Analysing…'}
            </span>
          )}
          <Button size="sm" onClick={handleReset} className="flex-shrink-0">← Back</Button>
        </div>

        <div ref={streamScrollRef} className="flex-1 overflow-y-auto">
          {hasContent ? (
            <div className="px-[20px] py-[18px]">
              {snapshot && <CaseSnapshotCard snapshot={snapshot} />}
              {!isExtracting && streamText && (
                <div className="text-[10.5px] text-text-3 mb-[12px]">
                  ⏱ ~{Math.max(1, Math.round(streamText.trim().split(/\s+/).length / 200))} min read
                </div>
              )}
              <MarkdownText text={streamText} />
              {isExtracting && (
                <span className="inline-block w-[2px] h-[14px] bg-text-3 align-middle animate-pulseDot ml-[1px]" />
              )}
              {!isExtracting && documentId && (
                <div className="mt-[24px] pt-[16px] border-t border-border-1">
                  <div className="text-[10px] font-bold tracking-[0.6px] uppercase text-text-3 mb-[10px]">Generate More</div>
                  <div className="flex flex-wrap gap-[8px]">
                    <button
                      onClick={() => handleQuickPrompt('Please provide a detailed analysis of this document including all witnesses, exhibits, procedural history, issue-wise findings, and evidence relied upon by the court.')}
                      disabled={isChatPending}
                      className="px-[12px] py-[7px] text-[12px] font-medium border border-border-2 rounded-sm bg-white text-text-1 hover:bg-surface-2 hover:border-ink transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      Detailed Analysis
                    </button>
                    <button
                      onClick={() => handleQuickPrompt('Based on this judgment, identify the strongest grounds for appeal. For each ground state: the legal basis, the specific error in the judgment, relevant authorities, and realistic prospects of success.')}
                      disabled={isChatPending}
                      className="px-[12px] py-[7px] text-[12px] font-medium border border-border-2 rounded-sm bg-white text-text-1 hover:bg-surface-2 hover:border-ink transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      Appeal Grounds
                    </button>
                    <button
                      onClick={() => handleQuickPrompt('Create a chronological timeline of all key events in this case. For each event state the date and what happened. List events in date order from earliest to latest.')}
                      disabled={isChatPending}
                      className="px-[12px] py-[7px] text-[12px] font-medium border border-border-2 rounded-sm bg-white text-text-1 hover:bg-surface-2 hover:border-ink transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      Case Timeline
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full gap-[20px] px-[32px]">
              <svg className="animate-spin h-[22px] w-[22px] text-text-3" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2.5"/>
                <path className="opacity-80" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
              </svg>
              <div className="text-center">
                <div className="text-[13px] font-semibold text-text-1 mb-[4px]">Reading document…</div>
                <div className="text-[11px] text-text-3">Extracting text from file</div>
              </div>
              <div className="flex gap-[5px]">
                {[0,1,2].map(i => (
                  <span key={i} className="w-[6px] h-[6px] rounded-full bg-text-3 animate-pulseDot"
                    style={{ animationDelay: `${i * 0.3}s` }} />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* RIGHT: PDF viewer + Chat tabs */}
      <div className="flex flex-col bg-white border-l border-border-1 overflow-hidden">

        {/* Tab bar */}
        <div className="h-11 flex-shrink-0 border-b border-border-1 flex items-stretch">
          <button
            onClick={() => setRightTab('pdf')}
            className={`flex items-center gap-[6px] px-[16px] text-[12px] font-semibold border-b-[2px] transition-colors ${
              rightTab === 'pdf'
                ? 'border-gold text-text-1'
                : 'border-transparent text-text-3 hover:text-text-2'
            }`}
          >
            📄 Document
          </button>
          <button
            onClick={() => setRightTab('chat')}
            className={`flex items-center gap-[6px] px-[16px] text-[12px] font-semibold border-b-[2px] transition-colors ${
              rightTab === 'chat'
                ? 'border-gold text-text-1'
                : 'border-transparent text-text-3 hover:text-text-2'
            }`}
          >
            💬 Chat
            {chatMsgs.length > 0 && (
              <span className="text-[9px] font-bold bg-gold text-sidebar px-[5px] py-[1px] rounded-full">
                {chatMsgs.filter(m => m.role === 'user').length}
              </span>
            )}
          </button>
          {rightTab === 'chat' && chatMsgs.length > 0 && (
            <button
              onClick={() => setChatMsgs([])}
              className="ml-auto mr-[12px] text-[11px] text-text-3 hover:text-text-1 transition-colors self-center"
            >
              Clear
            </button>
          )}
        </div>

        {/* PDF tab — always mounted, hidden via CSS to prevent iframe reload on tab switch */}
        <div className={`flex-1 overflow-hidden bg-surface-2 ${rightTab === 'pdf' ? 'flex flex-col' : 'hidden'}`}>
          {fileUrl ? (
            <iframe
              src={fileUrl}
              className="w-full h-full border-0"
              title="Document preview"
            />
          ) : (
            <div className="flex items-center justify-center h-full text-[12px] text-text-3">
              No document loaded
            </div>
          )}
        </div>

        {/* Chat tab — always mounted, hidden via CSS */}
        {true && (
          <div className={`${rightTab === 'chat' ? 'flex flex-col flex-1 overflow-hidden' : 'hidden'}`}>
            <div className="flex-1 overflow-y-auto p-3">
              <div className="bg-surface-2 rounded-sm px-[11px] py-[9px] mb-2 text-[12.5px] text-text-2">
                {documentId
                  ? <><strong>{filename}</strong> is ready. Ask me anything.</>
                  : <span className="text-text-3 italic">{isExtracting ? 'Analysis in progress…' : 'Upload a document to start chatting.'}</span>
                }
              </div>
              {chatMsgs.map((m, i) => (
                m.role === 'user' ? (
                  <div key={i} className="bg-white border border-border-1 rounded-sm px-[11px] py-[9px] mb-[7px]">
                    <div className="text-[10px] font-bold text-text-3 mb-[3px] uppercase tracking-[0.4px]">You asked</div>
                    <div className="text-[12.5px] text-text-1">{m.content}</div>
                  </div>
                ) : (
                  <div key={i} className="bg-white border border-border-1 border-l-[3px] border-l-ink rounded-r-sm px-[11px] py-[9px] mb-2">
                    <MarkdownText text={m.content} />
                  </div>
                )
              ))}
              {isChatPending && <div className="text-[11px] text-text-3 italic px-1">Thinking…</div>}
              <div ref={chatBottomRef} />
            </div>

            <div className="border-t border-border-1 p-[11px] bg-surface-2 flex-shrink-0">
              <input
                className="w-full px-[11px] py-2 border border-border-1 rounded-sm bg-white text-text-1 font-sans text-[12.5px] outline-none focus:border-border-2 transition-colors disabled:opacity-50"
                placeholder={documentId ? 'Ask a question about this document…' : 'Chat available after analysis…'}
                disabled={!documentId || isChatPending}
                value={question}
                onChange={e => setQuestion(e.target.value)}
                onFocus={() => setRightTab('chat')}
                onKeyDown={e => e.key === 'Enter' && handleAsk()}
              />
            </div>
          </div>
        )}

      </div>
    </div>
  )
}
