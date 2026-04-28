import { useState, useEffect, useRef } from 'react'
import { useMutation } from '@tanstack/react-query'
import DropZone from '@/components/ui/DropZone'
import Button from '@/components/ui/Button'
import { extractFromUpload, chatWithDocument } from '@/api/extract'
import { toast } from '@/store/toastStore'
import type {
  UniversalExtraction,
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
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]')
  } catch {
    return []
  }
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

function isAmber(confidence: number) {
  return confidence > 0 && confidence < AMBER
}

// ── Sub-components ───────────────────────────────────────────────────────────

function ConfBadge({ confidence }: { confidence: number }) {
  if (!confidence) return null
  const amber = isAmber(confidence)
  return (
    <span className={[
      'text-[9px] font-bold px-[5px] py-[1px] rounded-[4px] ml-[6px] flex-shrink-0',
      amber ? 'bg-amber-bg text-amber' : 'bg-green-bg text-green',
    ].join(' ')}>
      {confidence}%{amber ? ' ⚠' : ''}
    </span>
  )
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <div className="text-[9.5px] font-bold tracking-[0.6px] uppercase text-text-3 mb-[10px]">
      {children}
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="px-4 py-3 border-b border-border-1 last:border-b-0">
      <SectionTitle>{title}</SectionTitle>
      {children}
    </div>
  )
}

function SeverityBadge({ severity }: { severity: string }) {
  const cls =
    severity === 'High' ? 'bg-red-50 text-red-600' :
    severity === 'Medium' ? 'bg-amber-bg text-amber' :
    'bg-green-bg text-green'
  return (
    <span className={`text-[9px] font-bold px-[5px] py-[1px] rounded-[4px] ${cls}`}>
      {severity}
    </span>
  )
}

function PriorityBadge({ priority }: { priority: string }) {
  const cls =
    priority === 'Urgent' ? 'bg-red-50 text-red-600' :
    priority === 'High' ? 'bg-amber-bg text-amber' :
    'bg-surface-3 text-text-3'
  return (
    <span className={`text-[9px] font-bold px-[5px] py-[1px] rounded-[4px] ${cls}`}>
      {priority}
    </span>
  )
}

// ── Section renderers ────────────────────────────────────────────────────────

function IdentityFieldsSection({ fields }: { fields: Record<string, ExtractionIdentityField> }) {
  const entries = Object.entries(fields).filter(([, f]) => f?.value != null)
  if (!entries.length) return null
  return (
    <Section title="Key Details">
      <div className="space-y-[8px]">
        {entries.map(([key, field]) => (
          <div key={key}>
            <div className="flex items-center mb-[2px]">
              <span className="text-[10.5px] font-semibold text-text-2">{toLabel(key)}</span>
              <ConfBadge confidence={field.confidence} />
            </div>
            <div className="text-[12px] text-text-1 leading-[1.5]">
              {Array.isArray(field.value)
                ? <ul className="space-y-[2px]">{(field.value as string[]).map((v, i) => <li key={i} className="flex gap-[6px]"><span className="text-text-3 flex-shrink-0">•</span>{v}</li>)}</ul>
                : field.value as string}
            </div>
          </div>
        ))}
      </div>
    </Section>
  )
}

function SummarySection({ summary, objective }: {
  summary: UniversalExtraction['summary']
  objective: UniversalExtraction['primary_objective']
}) {
  const hasSummary = summary?.value
  const hasObj = objective?.value
  if (!hasSummary && !hasObj) return null
  return (
    <Section title="Summary">
      <div className="space-y-[10px]">
        {hasSummary && (
          <div>
            <div className="flex items-center mb-[3px]">
              <span className="text-[10.5px] font-semibold text-text-2">What happened</span>
              <ConfBadge confidence={summary.confidence} />
            </div>
            <p className="text-[12px] text-text-1 leading-[1.6]">{summary.value}</p>
          </div>
        )}
        {hasObj && (
          <div>
            <div className="flex items-center mb-[3px]">
              <span className="text-[10.5px] font-semibold text-text-2">Primary objective</span>
              <ConfBadge confidence={objective.confidence} />
            </div>
            <p className="text-[12px] text-text-1 leading-[1.6]">{objective.value}</p>
          </div>
        )}
      </div>
    </Section>
  )
}

function StakeholdersSection({ items }: { items: ExtractionStakeholder[] }) {
  const filtered = items.filter(s => s.name)
  if (!filtered.length) return null
  return (
    <Section title="Key Stakeholders">
      <div className="space-y-[8px]">
        {filtered.map((s, i) => (
          <div key={i} className="bg-surface-2 rounded-sm px-[10px] py-[7px]">
            <div className="flex items-center gap-[7px] mb-[2px]">
              <span className="text-[12px] font-semibold text-text-1">{s.name}</span>
              <span className="text-[9.5px] text-text-3 bg-surface-3 px-[6px] py-[1px] rounded-full">{s.role}</span>
              <ConfBadge confidence={s.confidence} />
            </div>
            {s.obligations && (
              <p className="text-[11.5px] text-text-2 leading-[1.5]">{s.obligations}</p>
            )}
          </div>
        ))}
      </div>
    </Section>
  )
}

function DeadlinesSection({ items }: { items: ExtractionDeadline[] }) {
  const filtered = items.filter(d => d.label)
  if (!filtered.length) return null
  return (
    <Section title="Critical Deadlines">
      <div className="space-y-[7px]">
        {filtered.map((d, i) => (
          <div key={i} className="flex gap-[10px] items-start">
            <div className="flex-shrink-0 mt-[1px] bg-surface-3 text-text-2 text-[10px] font-semibold px-[7px] py-[2px] rounded-[4px] whitespace-nowrap">
              {d.date || '—'}
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-[6px]">
                <span className="text-[12px] font-medium text-text-1">{d.label}</span>
                <ConfBadge confidence={d.confidence} />
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
  const filtered = items.filter(c => c.description)
  if (!filtered.length) return null
  return (
    <Section title="Constraints & Risks">
      <div className="space-y-[7px]">
        {filtered.map((c, i) => (
          <div key={i} className="flex gap-[8px] items-start">
            <SeverityBadge severity={c.severity} />
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-[6px]">
                <span className="text-[10.5px] font-semibold text-text-2">{c.type}</span>
                <ConfBadge confidence={c.confidence} />
              </div>
              <p className="text-[12px] text-text-1 leading-[1.5]">{c.description}</p>
            </div>
          </div>
        ))}
      </div>
    </Section>
  )
}

function ActionItemsSection({ items }: { items: ExtractionActionItem[] }) {
  const filtered = items.filter(a => a.action)
  if (!filtered.length) return null
  return (
    <Section title="Action Items">
      <div className="space-y-[7px]">
        {filtered.map((a, i) => (
          <div key={i} className="flex gap-[8px] items-start">
            <PriorityBadge priority={a.priority} />
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
  const filtered = items.filter(c => c.case_name)
  if (!filtered.length) return null
  return (
    <Section title="Citations Relied On">
      <div className="space-y-[6px]">
        {filtered.map((c, i) => (
          <div key={i} className="flex items-start gap-[8px]">
            <span className={`text-[9px] font-bold px-[5px] py-[1px] rounded-[4px] flex-shrink-0 mt-[2px] ${c.relied_upon ? 'bg-green-bg text-green' : 'bg-surface-3 text-text-3'}`}>
              {c.relied_upon ? 'Relied on' : 'Mentioned'}
            </span>
            <div className="min-w-0">
              <div className="flex items-center gap-[6px]">
                <span className="text-[12px] text-text-1">{c.case_name}</span>
                <ConfBadge confidence={c.confidence} />
              </div>
              {c.citation_string && (
                <p className="text-[11px] text-text-3">{c.citation_string}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </Section>
  )
}

// ── Main page ────────────────────────────────────────────────────────────────

export default function PdfExtractorPage() {
  const [filename, setFilename] = useState('')
  const [extraction, setExtraction] = useState<UniversalExtraction | null>(null)
  const [documentId, setDocumentId] = useState<string | null>(null)
  const [chatMsgs, setChatMsgs] = useState<ChatMsg[]>([])
  const [question, setQuestion] = useState('')
  const [history, setHistory] = useState<HistoryEntry[]>(loadHistory)
  const chatBottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMsgs])

  // Clear chat history when document changes
  useEffect(() => {
    setChatMsgs([])
  }, [documentId])

  const extractMutation = useMutation({
    mutationFn: (file: File) => extractFromUpload(file),
    onSuccess: ({ data }, file) => {
      const result = data.data as UniversalExtraction
      setFilename(file.name)
      setExtraction(result)
      saveToHistory(file.name, result)
      setHistory(loadHistory())
      setDocumentId(result.document_id ?? null)
    },
    onError: () => toast('Extraction failed. Check file format and try again.'),
  })

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

  const handleFile = (file: File) => {
    if (file.size > 50 * 1024 * 1024) { toast('File too large — max 50MB'); return }
    setFilename(file.name)
    setExtraction(null)
    setDocumentId(null)
    setChatMsgs([])
    extractMutation.mutate(file)
  }

  const handleLoadHistory = (entry: HistoryEntry) => {
    setFilename(entry.filename)
    setExtraction(entry.extraction)
    setDocumentId(null)
    setChatMsgs([])
    extractMutation.reset()
  }

  const handleDeleteHistory = (e: React.MouseEvent, id: string) => {
    e.stopPropagation()
    removeFromHistory(id)
    setHistory(loadHistory())
  }

  const handleAsk = () => {
    if (!question.trim() || !documentId) return
    const updatedMsgs: ChatMsg[] = [
      ...chatMsgs,
      { role: 'user', content: question },
    ]
    setChatMsgs(updatedMsgs)
    chatMutation.mutate({ id: documentId, msgs: updatedMsgs })
    setQuestion('')
  }

  const handleReset = () => {
    setFilename('')
    setExtraction(null)
    setDocumentId(null)
    setChatMsgs([])
    extractMutation.reset()
  }

  // ── Landing screen ──────────────────────────────────────────────────────────

  if (!filename || (!extractMutation.isPending && !extraction)) {
    return (
      <div className="max-w-[520px] mx-auto mt-9 px-2">
        <DropZone onFile={handleFile} />

        {extractMutation.isPending && (
          <div className="mt-4 text-center">
            <div className="inline-flex items-center gap-2 text-[12px] text-text-2">
              <svg className="animate-spin h-4 w-4 text-ink" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              Analysing {filename}…
            </div>
          </div>
        )}

        {history.length > 0 && !extractMutation.isPending && (
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
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    )
  }

  // ── Extraction view ─────────────────────────────────────────────────────────

  const docType = extraction?.document_type

  return (
    <div
      className="h-[calc(100vh-50px-44px)] md:h-[calc(100vh-50px)] grid border border-border-1 rounded-DEFAULT overflow-hidden shadow-[0_1px_4px_rgba(0,0,0,0.05)]"
      style={{ gridTemplateColumns: '1fr 1fr' }}
    >
      {/* LEFT: Extracted intelligence */}
      <div className="flex flex-col bg-white overflow-x-scroll">
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

        <div className="flex-1 overflow-y-auto">
          {extractMutation.isPending ? (
            <div className="flex flex-col items-center justify-center h-full gap-3">
              <svg className="animate-spin h-5 w-5 text-text-3" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              <div className="text-[12px] text-text-3">Analysing document…</div>
            </div>
          ) : extraction ? (
            <div>
              <SummarySection summary={extraction.summary} objective={extraction.primary_objective} />
              <IdentityFieldsSection fields={extraction.identity_fields} />
              <StakeholdersSection items={extraction.key_stakeholders} />
              <DeadlinesSection items={extraction.critical_deadlines} />
              <ConstraintsSection items={extraction.constraints_and_risks} />
              <ActionItemsSection items={extraction.action_items} />
              <CitationsSection items={extraction.citations} />
            </div>
          ) : null}
        </div>
      </div>

      {/* RIGHT: Chat */}
      <div className="flex flex-col bg-white border-l border-border-1 overflow-x-scroll">
        <div className="h-11 flex-shrink-0 px-[14px] border-b border-border-1 flex items-center justify-between">
          <span className="text-[12px] font-bold text-text-1">💬 Chat with Document</span>
          {chatMsgs.length > 0 && (
            <button
              onClick={() => setChatMsgs([])}
              className="text-[11px] text-text-3 hover:text-text-1 transition-colors"
            >
              Clear
            </button>
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
              <div key={i} className="bg-surface-2 border-l-[3px] border-ink rounded-r-sm px-[11px] py-[9px] text-[12.5px] text-text-2 leading-[1.6] mb-2 whitespace-pre-wrap">
                {m.content}
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
