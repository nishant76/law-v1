import { useState, useRef, useCallback } from 'react'
import { useMutation } from '@tanstack/react-query'
import Chip from '@/components/ui/Chip'
import Button from '@/components/ui/Button'
import VerifiedBadge from '@/components/ui/VerifiedBadge'
import { Input, Textarea } from '@/components/ui/FormField'
import {
  generateFiling,
  exportFiling,
  type FilingInput,
  type ExportFilingInput,
  type SelectedCitation,
} from '@/api/filing'
import { unifiedSearch } from '@/api/search'
import { toast } from '@/store/toastStore'
import { downloadBlob } from '@/lib/utils'
import type { Draft, PublicJudgmentResult, SearchAnalysis } from '@/types'

// ── Constants ─────────────────────────────────────────────────────────────────

const FILING_TYPES = [
  'Bail Application',
  'Writ Petition',
  'Civil Suit',
  'Notice Reply',
  'Criminal',
  'Other',
]

const OBJECTIVES = [
  'Win on merits',
  'Delay',
  'Challenge',
  'Settle',
  'Preserve appeal',
]

const PROG_MSGS = [
  'Analysing case facts…',
  'Determining document format…',
  'Drafting petition clauses…',
  'Weaving in selected citations…',
  'Formatting for P&H HC…',
  'Finalising draft…',
]

type Step = 'search' | 'brief' | 'draft'

// ── Step indicator ─────────────────────────────────────────────────────────────

function StepBar({ step }: { step: Step }) {
  const steps: { id: Step; label: string }[] = [
    { id: 'search', label: 'Find Citations' },
    { id: 'brief',  label: 'Case Brief' },
    { id: 'draft',  label: 'Draft' },
  ]
  const idx = steps.findIndex(s => s.id === step)
  return (
    <div className="flex items-center gap-0 mb-6">
      {steps.map((s, i) => (
        <div key={s.id} className="flex items-center">
          <div className="flex items-center gap-[6px]">
            <div className={[
              'w-[20px] h-[20px] rounded-full flex items-center justify-center text-[10px] font-bold flex-shrink-0 border',
              i < idx  ? 'bg-ink text-white border-ink'
              : i === idx ? 'bg-white text-ink border-ink'
              : 'bg-white text-text-3 border-border-1',
            ].join(' ')}>
              {i < idx ? '✓' : i + 1}
            </div>
            <span className={[
              'text-[11px] font-semibold',
              i === idx ? 'text-text-1' : i < idx ? 'text-text-2' : 'text-text-3',
            ].join(' ')}>
              {s.label}
            </span>
          </div>
          {i < steps.length - 1 && (
            <div className={[
              'w-[32px] h-[1px] mx-[6px]',
              i < idx ? 'bg-ink' : 'bg-border-1',
            ].join(' ')} />
          )}
        </div>
      ))}
    </div>
  )
}

// ── Step 1: Search & Select ───────────────────────────────────────────────────

// ── Analysis banner — shown when backend returns overall_analysis ─────────────

function AnalysisBanner({ analysis, resultCount }: { analysis: SearchAnalysis; resultCount: number }) {
  const hasWinning = (analysis.winning_factors?.length ?? 0) > 0
  const hasRisks   = (analysis.risk_factors?.length ?? 0) > 0

  return (
    <div className="mb-4 border border-border-2 rounded-sm overflow-hidden">
      {/* Header */}
      <div className="px-[13px] py-[9px] bg-surface-2 border-b border-border-1 flex items-center gap-[7px]">
        <span className="text-[11px] font-bold text-text-1">✦ AI Analysis</span>
        <span className="text-[10px] text-text-3">across {resultCount} results</span>
      </div>

      <div className="px-[13px] py-[11px] bg-white space-y-[10px]">
        {/* Strongest case */}
        {analysis.strongest_case && (
          <div>
            <div className="text-[10px] font-bold tracking-[0.4px] uppercase text-text-3 mb-[3px]">
              Best match for your search
            </div>
            <p className="text-[12px] text-text-1 leading-[1.5]">{analysis.strongest_case}</p>
          </div>
        )}

        {/* Practical advice */}
        {analysis.practical_advice && (
          <div className="bg-surface-2 rounded-[4px] px-[10px] py-[7px]">
            <p className="text-[11.5px] text-text-2 leading-[1.5] italic">{analysis.practical_advice}</p>
          </div>
        )}

        {/* Winning / risk factors side by side */}
        {(hasWinning || hasRisks) && (
          <div className="grid grid-cols-2 gap-[10px] pt-[2px]">
            {hasWinning && (
              <div>
                <div className="text-[10px] font-bold tracking-[0.4px] uppercase text-green mb-[4px]">
                  In your favour
                </div>
                <ul className="space-y-[3px]">
                  {analysis.winning_factors.map((f, i) => (
                    <li key={i} className="flex gap-[5px] text-[11px] text-text-1 leading-[1.4]">
                      <span className="text-green flex-shrink-0 text-[9px] mt-[2px]">✓</span>
                      {f}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {hasRisks && (
              <div>
                <div className="text-[10px] font-bold tracking-[0.4px] uppercase text-amber mb-[4px]">
                  Watch out for
                </div>
                <ul className="space-y-[3px]">
                  {analysis.risk_factors.map((f, i) => (
                    <li key={i} className="flex gap-[5px] text-[11px] text-text-1 leading-[1.4]">
                      <span className="text-amber flex-shrink-0 text-[9px] mt-[2px]">⚠</span>
                      {f}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

interface SearchStepProps {
  selected: PublicJudgmentResult[]
  onToggle: (r: PublicJudgmentResult) => void
  onContinue: () => void
  onSkip: () => void
}

function SearchStep({ selected, onToggle, onContinue, onSkip }: SearchStepProps) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<PublicJudgmentResult[]>([])
  const [analysis, setAnalysis] = useState<SearchAnalysis | null>(null)

  const searchMutation = useMutation({
    mutationFn: (q: string) => unifiedSearch(q),
    onSuccess: ({ data }) => {
      setResults(data.from_public_judgments ?? [])
      setAnalysis((data as any).overall_analysis ?? null)
    },
    onError: () => toast('Search failed. Please try again.'),
  })

  const handleSearch = () => {
    if (!query.trim()) return
    setAnalysis(null)
    searchMutation.mutate(query)  // pass at call time, never capture in closure
  }

  const selectedIds = new Set(selected.map(s => s.id))

  return (
    <div className="max-w-[680px] mx-auto">
      <StepBar step="search" />

      <h1 className="font-serif text-[20px] tracking-[-0.2px] text-text-1 mb-[4px]">
        Find Relevant Citations
      </h1>
      <p className="text-[12px] text-text-3 mb-5">
        Search for judgments that support your matter. Select the most relevant ones — they'll be woven into your draft.
      </p>

      {/* Search bar */}
      <div className="flex gap-[6px] mb-4">
        <input
          className="flex-1 px-[12px] py-[9px] border border-border-1 rounded-sm bg-white text-text-1 font-sans text-[13px] outline-none focus:border-border-2 transition-all placeholder:text-text-3"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSearch()}
          placeholder="e.g. S.437 bail NDPS first offender Punjab"
          autoFocus
        />
        <Button
          variant="primary"
          onClick={handleSearch}
          disabled={searchMutation.isPending || !query.trim()}
        >
          {searchMutation.isPending ? '…' : 'Search'}
        </Button>
      </div>

      {/* Selected citations pills */}
      {selected.length > 0 && (
        <div className="mb-4 p-[10px] bg-surface-2 border border-border-1 rounded-sm">
          <div className="text-[10px] font-bold tracking-[0.5px] uppercase text-text-3 mb-[7px]">
            Selected ({selected.length})
          </div>
          <div className="flex flex-wrap gap-[5px]">
            {selected.map(r => (
              <button
                key={r.id}
                onClick={() => onToggle(r)}
                className="flex items-center gap-[5px] text-[11px] font-medium bg-ink text-white px-[9px] py-[3px] rounded-full hover:bg-ink/80 transition-colors"
              >
                <span className="max-w-[220px] truncate">{r.case_name}</span>
                <span className="text-white/60 text-[10px]">✕</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Results */}
      {searchMutation.isPending && (
        <div className="text-center py-8 text-[12px] text-text-3 italic">Searching judgments…</div>
      )}

      {!searchMutation.isPending && results.length === 0 && !searchMutation.isIdle && (
        <div className="text-center py-8 text-[12px] text-text-3">No results found. Try different keywords.</div>
      )}

      {!searchMutation.isPending && results.length === 0 && searchMutation.isIdle && (
        <div className="text-center py-10 text-text-3">
          <div className="text-[28px] mb-2">⚖</div>
          <div className="text-[12px]">Search for judgments above — select up to 5 most relevant</div>
        </div>
      )}

      {/* AI analysis banner — shown when ≥ 3 results returned */}
      {!searchMutation.isPending && analysis && results.length >= 3 && (
        <AnalysisBanner analysis={analysis} resultCount={results.length} />
      )}

      <div className="space-y-[7px] mb-6">
        {results.map(r => {
          const isSelected = selectedIds.has(r.id)
          const maxed = selected.length >= 5 && !isSelected
          const enrichment = r.enrichment
          return (
            <button
              key={r.id}
              onClick={() => !maxed && onToggle(r)}
              disabled={maxed}
              className={[
                'w-full text-left px-[13px] py-[11px] border rounded-sm transition-all',
                isSelected
                  ? 'bg-ink/[0.04] border-ink/30'
                  : maxed
                  ? 'opacity-40 cursor-not-allowed border-border-1 bg-white'
                  : 'bg-white border-border-1 hover:border-border-2 cursor-pointer',
              ].join(' ')}
            >
              <div className="flex items-start gap-[10px]">
                {/* Checkbox */}
                <div className={[
                  'w-[16px] h-[16px] flex-shrink-0 mt-[2px] rounded-[3px] border flex items-center justify-center',
                  isSelected ? 'bg-ink border-ink' : 'border-border-2 bg-white',
                ].join(' ')}>
                  {isSelected && <span className="text-white text-[9px] font-bold">✓</span>}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="text-[12.5px] font-semibold text-text-1 mb-[2px] leading-snug">
                    {r.case_name}
                  </div>

                  {/* Meta row */}
                  <div className="flex flex-wrap gap-[6px] text-[10.5px] text-text-3 mb-[6px]">
                    <span>{r.court}</span>
                    <span>·</span>
                    <span>{r.year}</span>
                    {r.primary_citation && (
                      <>
                        <span>·</span>
                        <span className="font-mono text-[10px] text-text-2">{r.primary_citation}</span>
                      </>
                    )}
                    {r.outcome && (
                      <>
                        <span>·</span>
                        <span className={[
                          'font-medium capitalize',
                          r.outcome.toLowerCase().includes('allow') || r.outcome.toLowerCase().includes('grant')
                            ? 'text-green' : 'text-text-2',
                        ].join(' ')}>
                          {r.outcome}
                        </span>
                      </>
                    )}
                  </div>

                  {/* Legal issue decided — from per-citation enrichment */}
                  {enrichment?.issue && (
                    <div className="mb-[5px]">
                      <span className="text-[10px] font-semibold text-text-3 mr-[5px]">Issue:</span>
                      <span className="text-[11px] text-text-2 leading-[1.45]">{enrichment.issue}</span>
                    </div>
                  )}

                  {/* Why relevant to THIS query:
                      Priority 1 — relevance_per_case from live analysis (fresh, query-specific)
                      Priority 2 — enrichment.relevance from DB (cached, may be stale)
                      Priority 3 — editorial summary
                      Priority 4 — ratio as last resort */}
                  {(() => {
                    const liveRelevance = analysis?.relevance_per_case?.[r.id]
                    const cachedRelevance = enrichment?.relevance
                    const relevanceText = liveRelevance || cachedRelevance
                    if (relevanceText) {
                      return (
                        <div className="bg-surface-2 rounded-[3px] px-[8px] py-[5px] mb-[4px]">
                          <span className="text-[10px] font-semibold text-text-3 mr-[5px]">Why relevant:</span>
                          <span className="text-[11px] text-text-2 leading-[1.45]">{relevanceText}</span>
                        </div>
                      )
                    }
                    if (r.summary) {
                      return <div className="text-[11px] text-text-2 leading-[1.5] line-clamp-2">{r.summary}</div>
                    }
                    if (enrichment?.ratio) {
                      return <div className="text-[11px] text-text-2 leading-[1.5] line-clamp-2 italic">{enrichment.ratio}</div>
                    }
                    return null
                  })()}
                </div>

                {r.primary_citation && (
                  <VerifiedBadge status="verified" source="eSCR" />
                )}
              </div>
            </button>
          )
        })}
      </div>

      {/* Footer actions */}
      <div className="flex items-center gap-[10px]">
        <Button
          variant="primary"
          onClick={onContinue}
          disabled={selected.length === 0}
        >
          Continue with {selected.length} citation{selected.length !== 1 ? 's' : ''} →
        </Button>
        <button
          onClick={onSkip}
          className="text-[11.5px] text-text-3 hover:text-text-1 font-medium transition-colors"
        >
          Skip, proceed without citations
        </button>
      </div>
      {selected.length >= 5 && (
        <p className="mt-2 text-[11px] text-amber">Maximum 5 citations — deselect one to add another.</p>
      )}
    </div>
  )
}

// ── Step 2: Case Brief ────────────────────────────────────────────────────────

interface Brief {
  filingType: string
  objective: string
  petitioner: string
  respondent: string
  court: string
  sections: string
  facts: string
}

interface BriefStepProps {
  brief: Brief
  onChange: (b: Brief) => void
  selected: PublicJudgmentResult[]
  onBack: () => void
  onGenerate: () => void
  isPending: boolean
  progMsg: string
}

function BriefStep({
  brief, onChange, selected, onBack, onGenerate, isPending, progMsg,
}: BriefStepProps) {
  const set = useCallback(
    (key: keyof Brief) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
      onChange({ ...brief, [key]: e.target.value }),
    [brief, onChange]
  )

  const canGenerate = brief.petitioner.trim() && brief.facts.trim()

  return (
    <div className="max-w-[580px] mx-auto">
      <StepBar step="brief" />

      <div className="flex items-center justify-between mb-1">
        <h1 className="font-serif text-[20px] tracking-[-0.2px] text-text-1">Case Brief</h1>
        <button
          onClick={onBack}
          className="text-[11.5px] text-text-3 hover:text-text-1 font-medium transition-colors"
        >
          ← Change citations
        </button>
      </div>
      <p className="text-[12px] text-text-3 mb-5">
        Fill in the case details — the draft will be tailored to your objective.
      </p>

      {/* Selected citations summary */}
      {selected.length > 0 && (
        <div className="mb-5 p-[12px] bg-surface-2 border border-border-1 rounded-sm">
          <div className="text-[10px] font-bold tracking-[0.5px] uppercase text-text-3 mb-[7px]">
            Citations to include ({selected.length})
          </div>
          <div className="space-y-[4px]">
            {selected.map(r => (
              <div key={r.id} className="flex items-center gap-[7px] text-[11.5px]">
                <span className="text-green text-[10px]">✓</span>
                <span className="text-text-1 font-medium truncate">{r.case_name}</span>
                {r.primary_citation && (
                  <span className="text-text-3 font-mono text-[10px] flex-shrink-0">{r.primary_citation}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {selected.length === 0 && (
        <div className="mb-5 p-[10px] bg-amber-bg border border-amber/20 rounded-sm text-[11.5px] text-amber">
          No citations selected — draft will use AI-found citations from the database.
        </div>
      )}

      {/* Filing type */}
      <div className="mb-[13px]">
        <label className="block text-[10px] font-bold tracking-[0.5px] uppercase text-text-3 mb-[6px]">
          Filing type
        </label>
        <div className="flex flex-wrap gap-[5px]">
          {FILING_TYPES.map(t => (
            <Chip
              key={t}
              selected={brief.filingType === t}
              onClick={() => onChange({ ...brief, filingType: t })}
            >
              {t}
            </Chip>
          ))}
        </div>
      </div>

      {/* Objective */}
      <div className="mb-[13px]">
        <label className="block text-[10px] font-bold tracking-[0.5px] uppercase text-text-3 mb-[6px]">
          Objective
        </label>
        <div className="flex flex-wrap gap-[5px]">
          {OBJECTIVES.map(o => (
            <Chip
              key={o}
              selected={brief.objective === o}
              onClick={() => onChange({ ...brief, objective: o })}
            >
              {o}
            </Chip>
          ))}
        </div>
      </div>

      <Input
        label="Petitioner *"
        value={brief.petitioner}
        onChange={set('petitioner')}
        placeholder="e.g. Gurnam Singh"
      />
      <Input
        label="Respondent"
        value={brief.respondent}
        onChange={set('respondent')}
        placeholder="e.g. State of Punjab"
      />
      <Input
        label="Court"
        value={brief.court}
        onChange={set('court')}
      />
      <Input
        label="FIR / Sections"
        value={brief.sections}
        onChange={set('sections')}
        placeholder="e.g. FIR 234/2024 · NDPS Act S.21"
      />
      <Textarea
        label="Key facts *"
        value={brief.facts}
        onChange={set('facts')}
        minRows={4}
        placeholder="Describe the key facts of the case…"
      />

      {/* Progress */}
      {progMsg && (
        <div className="mb-[13px]">
          <div className="h-[2px] bg-surface-3 rounded-full overflow-hidden mb-[5px]">
            <div className="h-full bg-ink rounded-full animate-[progBar_3.5s_ease-out_forwards]" />
          </div>
          <div className="text-[10.5px] text-text-3 italic">{progMsg}</div>
        </div>
      )}

      <Button
        variant="primary"
        size="lg"
        onClick={onGenerate}
        disabled={isPending || !canGenerate}
      >
        {isPending ? '⏳ Generating…' : '✦ Generate Draft'}
      </Button>
      {!canGenerate && !isPending && (
        <p className="mt-2 text-[11px] text-text-3">* Petitioner and Key facts are required</p>
      )}
    </div>
  )
}

// ── Step 3: Draft Output ──────────────────────────────────────────────────────

interface DraftStepProps {
  draft: Draft
  selected: PublicJudgmentResult[]
  onNew: () => void
  onExport: () => void
  isExporting: boolean
}

function DraftStep({ draft, selected, onNew, onExport, isExporting }: DraftStepProps) {
  const sections = draft.sections ?? {}

  const handleCopy = () => {
    const text = Object.values(sections).join('\n\n')
    navigator.clipboard.writeText(text).then(() => toast('Copied to clipboard'))
  }

  return (
    <div className="max-w-[760px]">
      <StepBar step="draft" />

      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-5">
        <div>
          <h1 className="font-serif text-[20px] tracking-[-0.2px] text-text-1 mb-[3px]">
            Generated Draft
          </h1>
          <p className="text-[12px] text-text-3">
            Review carefully — verify all citations and facts before filing.
          </p>
        </div>
        <div className="flex gap-[6px] flex-shrink-0">
          <Button size="sm" onClick={onNew}>← New</Button>
          <Button size="sm" onClick={handleCopy}>Copy</Button>
          {draft.id && (
            <Button
              size="sm"
              variant="primary"
              onClick={onExport}
              disabled={isExporting}
            >
              {isExporting ? 'Exporting…' : '↓ .docx'}
            </Button>
          )}
        </div>
      </div>

      {/* Quality score */}
      {draft.quality_score !== undefined && (
        <div className="flex items-center gap-[8px] mb-4">
          <span className={[
            'text-[11px] font-bold',
            draft.quality_score >= 70 ? 'text-green'
            : draft.quality_score >= 50 ? 'text-amber'
            : 'text-red-500',
          ].join(' ')}>
            Quality score: {draft.quality_score}/100
          </span>
          {draft.quality_score < 50 && (
            <span className="text-[10.5px] text-amber bg-amber-bg border border-amber/20 px-[8px] py-[2px] rounded-full">
              Low quality — consider adding more facts
            </span>
          )}
        </div>
      )}

      {/* Citations used */}
      {(draft.citations_used?.length > 0 || selected.length > 0) && (
        <div className="mb-4 p-[11px] bg-surface-2 border border-border-1 rounded-sm">
          <div className="text-[10px] font-bold tracking-[0.5px] uppercase text-text-3 mb-[7px]">
            Citations in draft
          </div>
          <div className="flex flex-wrap gap-[5px]">
            {draft.citations_used?.map(c => (
              <span
                key={c}
                className="text-[10.5px] font-medium bg-green-bg text-green border border-green/20 px-[8px] py-[2px] rounded-[4px]"
              >
                {c} ✓
              </span>
            ))}
            {selected
              .filter(r => r.primary_citation && !draft.citations_used?.includes(r.primary_citation))
              .map(r => (
                <span
                  key={r.id}
                  className="text-[10.5px] font-medium bg-surface-3 text-text-2 border border-border-1 px-[8px] py-[2px] rounded-[4px]"
                >
                  {r.primary_citation}
                </span>
              ))}
          </div>
        </div>
      )}

      {/* Draft content */}
      <div className="bg-white border border-border-1 rounded-DEFAULT px-[28px] py-[24px] font-serif text-[13px] leading-[1.9] text-text-1">
        {sections.court_heading && (
          <h3 className="text-[12.5px] font-normal text-center mb-[10px] underline underline-offset-[3px] tracking-[0.3px] whitespace-pre-line">
            {sections.court_heading}
          </h3>
        )}
        {sections.parties_section && (
          <p className="text-center text-[11.5px] mb-4 font-sans whitespace-pre-line">
            {sections.parties_section}
          </p>
        )}
        {sections.facts_section && (
          <div className="mb-[12px]">
            <p className="text-[10px] font-bold tracking-[0.5px] uppercase text-text-3 font-sans mb-[4px]">
              Facts
            </p>
            <p className="text-justify border-l-2 border-border-2 pl-[10px] bg-black/[0.015] py-[4px]">
              {sections.facts_section}
            </p>
          </div>
        )}
        {sections.grounds_section && (
          <div className="mb-[12px]">
            <p className="text-[10px] font-bold tracking-[0.5px] uppercase text-text-3 font-sans mb-[4px]">
              Grounds
            </p>
            <p className="text-justify">{sections.grounds_section}</p>
          </div>
        )}
        {sections.prayer_section && (
          <div className="mt-[16px]">
            <p className="text-[10px] font-bold tracking-[0.5px] uppercase text-text-3 font-sans mb-[4px]">
              Prayer
            </p>
            <p className="text-justify">{sections.prayer_section}</p>
          </div>
        )}
        {sections.verification && (
          <p className="mt-[16px] text-[11.5px] font-sans text-text-2 border-t border-border-1 pt-[12px]">
            {sections.verification}
          </p>
        )}
      </div>

      {/* Footer warning */}
      <p className="mt-3 text-[11px] text-text-3">
        ⚠️ Review before filing — verify citations, case numbers, and all facts against source documents.
      </p>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function DraftPage() {
  const [step, setStep] = useState<Step>('search')
  const [selected, setSelected] = useState<PublicJudgmentResult[]>([])
  const [brief, setBrief] = useState<Brief>({
    filingType: 'Bail Application',
    objective: 'Win on merits',
    petitioner: '',
    respondent: '',
    court: 'P&H High Court, Chandigarh',
    sections: '',
    facts: '',
  })
  const [draft, setDraft] = useState<Draft | null>(null)
  const [progMsg, setProgMsg] = useState('')
  const progRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const toggleCitation = (r: PublicJudgmentResult) => {
    setSelected(prev =>
      prev.find(s => s.id === r.id)
        ? prev.filter(s => s.id !== r.id)
        : prev.length < 5 ? [...prev, r] : prev
    )
  }

  const generateMutation = useMutation({
    mutationFn: (input: FilingInput) => generateFiling(input),
    onMutate: () => {
      setProgMsg(PROG_MSGS[0])
      let i = 1
      progRef.current = setInterval(() => {
        if (i < PROG_MSGS.length) setProgMsg(PROG_MSGS[i++])
        else { clearInterval(progRef.current!); setProgMsg('') }
      }, 600)
    },
    onSuccess: ({ data }) => {
      clearInterval(progRef.current!)
      setProgMsg('')
      // API returns: { success, draft_id, draft: { draft_sections, citations_used, ... }, quality_scores: { overall_score } }
      const raw = data as unknown as {
        success?: boolean
        draft_id?: string
        draft?: { draft_sections?: Record<string, string>; citations_used?: string[] }
        quality_scores?: { overall_score?: number }
      }
      if (!raw?.draft?.draft_sections) {
        toast('Draft generation failed — please try again.')
        return
      }
      const normalised: Draft = {
        id: raw.draft_id ?? '',
        filing_type: brief.filingType,
        objective: brief.objective,
        petitioner: brief.petitioner,
        respondent: brief.respondent,
        court: brief.court,
        sections: raw.draft.draft_sections,
        citations_used: raw.draft.citations_used ?? [],
        quality_score: raw.quality_scores?.overall_score ?? 0,
        created_at: new Date().toISOString(),
      }
      setDraft(normalised)
      setStep('draft')
      toast('Draft generated — verify citations before filing')
    },
    onError: () => {
      clearInterval(progRef.current!)
      setProgMsg('')
      toast('Draft generation failed. Please try again.')
    },
  })

  const exportMutation = useMutation({
    mutationFn: (id: string) => exportFiling(id),
    onSuccess: res => downloadBlob(res.data as Blob, 'draft.docx'),
    onError: () => toast('Export failed.'),
  })

  const handleGenerate = () => {
    if (!brief.petitioner.trim() || !brief.facts.trim()) {
      toast('Please fill Petitioner and Key facts')
      return
    }
    const selectedCitations: SelectedCitation[] = selected.map(r => ({
      case_name: r.case_name,
      citation: r.primary_citation ?? null,
      court: r.court,
      year: r.year,
      source_url: r.source_url,
    }))
    generateMutation.mutate({
      filing_type: brief.filingType,
      objective: brief.objective,
      petitioner: brief.petitioner,
      respondent: brief.respondent,
      court: brief.court,
      sections: brief.sections,
      facts: brief.facts,
      selected_citations: selectedCitations.length > 0 ? selectedCitations : undefined,
    })
  }

  const handleNew = () => {
    setStep('search')
    setSelected([])
    setBrief({
      filingType: 'Bail Application',
      objective: 'Win on merits',
      petitioner: '',
      respondent: '',
      court: 'P&H High Court, Chandigarh',
      sections: '',
      facts: '',
    })
    setDraft(null)
    generateMutation.reset()
  }

  return (
    <div className="py-6 px-4 md:px-6 max-w-[900px]">
      {step === 'search' && (
        <SearchStep
          selected={selected}
          onToggle={toggleCitation}
          onContinue={() => setStep('brief')}
          onSkip={() => setStep('brief')}
        />
      )}

      {step === 'brief' && (
        <BriefStep
          brief={brief}
          onChange={setBrief}
          selected={selected}
          onBack={() => setStep('search')}
          onGenerate={handleGenerate}
          isPending={generateMutation.isPending}
          progMsg={progMsg}
        />
      )}

      {step === 'draft' && draft && (
        <DraftStep
          draft={draft}
          selected={selected}
          onNew={handleNew}
          onExport={() => draft.id && exportMutation.mutate(draft.id)}
          isExporting={exportMutation.isPending}
        />
      )}
    </div>
  )
}
