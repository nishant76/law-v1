import { useState, useRef } from 'react'
import { unifiedSearch } from '@/api/search'
import VerifiedBadge from '@/components/ui/VerifiedBadge'
import Button from '@/components/ui/Button'
import type { PublicJudgmentResult, OwnFileResult } from '@/types'

// ── Outcome grouping ──────────────────────────────────────────────────────────

const OUTCOME_GROUP_MAP: { label: string; values: string[] }[] = [
  { label: 'Petitioner won',  values: ['allowed', 'granted', 'accepted'] },
  { label: 'Respondent won',  values: ['dismissed', 'rejected'] },
  { label: 'Bail granted',    values: ['bail_granted'] },
  { label: 'Bail refused',    values: ['bail_refused'] },
]

function getOutcomeLabel(outcome: string): string {
  const o = outcome.toLowerCase()
  for (const g of OUTCOME_GROUP_MAP) {
    if (g.values.some(v => o.includes(v))) return g.label
  }
  // Fallback: capitalise and replace underscores
  return outcome.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

// ── Court normalisation ───────────────────────────────────────────────────────

function normaliseCourt(court: string): string {
  const c = court.toLowerCase()
  if (c.includes('supreme')) return 'Supreme Court'
  if (c.includes('p&h') || (c.includes('punjab') && c.includes('haryana')) || c.includes('phhc'))
    return 'P&H High Court'
  if (c.includes('high court')) return 'High Court'
  if (c.includes('district')) return 'District Court'
  return court
}

// ── Filter state & logic ──────────────────────────────────────────────────────

interface ActiveFilters {
  outcome: string   // '' = no filter
  court:   string
  type:    string
}

const NO_FILTERS: ActiveFilters = { outcome: '', court: '', type: '' }

function applyFilters(
  results: PublicJudgmentResult[],
  filters: ActiveFilters,
): PublicJudgmentResult[] {
  return results.filter(r => {
    if (filters.outcome) {
      const label = r.outcome ? getOutcomeLabel(r.outcome) : ''
      if (label !== filters.outcome) return false
    }
    if (filters.court) {
      const norm = r.court ? normaliseCourt(r.court) : ''
      if (norm !== filters.court) return false
    }
    if (filters.type) {
      const t = (r.matter_type ?? '').toLowerCase()
      if (t !== filters.type.toLowerCase()) return false
    }
    return true
  })
}

interface FilterOption { value: string; label: string; count: number }
interface FilterGroup  { dimension: keyof ActiveFilters; label: string; options: FilterOption[] }

// For each dimension, count results while ignoring that dimension's own filter.
// This gives correct counts: "if I pick this option, how many results will I see?"
function deriveFilterGroups(
  all: PublicJudgmentResult[],
  active: ActiveFilters,
): FilterGroup[] {
  const groups: FilterGroup[] = []

  // ── Outcome ─────────────────────────────────────────────────────────────────
  const outcomeBase = applyFilters(all, { ...active, outcome: '' })
  const outcomeMap = new Map<string, number>()
  for (const r of outcomeBase) {
    if (r.outcome) {
      const label = getOutcomeLabel(r.outcome)
      outcomeMap.set(label, (outcomeMap.get(label) ?? 0) + 1)
    }
  }
  if (outcomeMap.size >= 2) {
    groups.push({
      dimension: 'outcome',
      label: 'Outcome',
      options: [...outcomeMap.entries()]
        .map(([value, count]) => ({ value, label: value, count }))
        .sort((a, b) => b.count - a.count),
    })
  }

  // ── Court ────────────────────────────────────────────────────────────────────
  const courtBase = applyFilters(all, { ...active, court: '' })
  const courtMap = new Map<string, number>()
  for (const r of courtBase) {
    if (r.court) {
      const norm = normaliseCourt(r.court)
      courtMap.set(norm, (courtMap.get(norm) ?? 0) + 1)
    }
  }
  if (courtMap.size >= 2) {
    groups.push({
      dimension: 'court',
      label: 'Court',
      options: [...courtMap.entries()]
        .map(([value, count]) => ({ value, label: value, count }))
        .sort((a, b) => b.count - a.count),
    })
  }

  // ── Matter type ──────────────────────────────────────────────────────────────
  const typeBase = applyFilters(all, { ...active, type: '' })
  const typeMap = new Map<string, number>()
  for (const r of typeBase) {
    if (r.matter_type) {
      const t = r.matter_type.charAt(0).toUpperCase() + r.matter_type.slice(1).toLowerCase()
      typeMap.set(t, (typeMap.get(t) ?? 0) + 1)
    }
  }
  if (typeMap.size >= 2) {
    groups.push({
      dimension: 'type',
      label: 'Type',
      options: [...typeMap.entries()]
        .map(([value, count]) => ({ value, label: value, count }))
        .sort((a, b) => b.count - a.count),
    })
  }

  return groups
}

// ── Source URL helpers ────────────────────────────────────────────────────────

const VERIFIED_SOURCES = ['eSCR', 'P&H HC', 'escr', 'panhc']
const ESCR_HOME = 'https://digiscr.sci.gov.in/'

function resolveSourceUrl(url: string | undefined): string | null {
  if (!url) return null
  if (url.includes('main.sci.gov.in')) return ESCR_HOME
  return url
}

// ── Dynamic filter bar ────────────────────────────────────────────────────────

function FilterBar({
  groups,
  active,
  onToggle,
  onClearAll,
}: {
  groups: FilterGroup[]
  active: ActiveFilters
  onToggle: (dim: keyof ActiveFilters, value: string) => void
  onClearAll: () => void
}) {
  if (groups.length === 0) return null

  const anyActive = active.outcome || active.court || active.type

  return (
    <div className="mb-5 space-y-[7px]">
      {groups.map(group => (
        <div key={group.dimension} className="flex items-center gap-[7px] flex-wrap">
          {/* Dimension label */}
          <span className="text-[10px] font-bold tracking-[0.5px] uppercase text-text-3 w-[44px] flex-shrink-0">
            {group.label}
          </span>

          {/* Option chips */}
          {group.options.map(opt => {
            const isActive = active[group.dimension] === opt.value
            return (
              <button
                key={opt.value}
                onClick={() => onToggle(group.dimension, opt.value)}
                className={[
                  'text-[11px] font-semibold px-[10px] py-[3px] rounded-full border transition-all cursor-pointer',
                  isActive
                    ? 'bg-ink text-white border-ink'
                    : 'bg-surface-2 text-text-2 border-border-1 hover:border-border-2 hover:bg-white',
                ].join(' ')}
              >
                {opt.label}
                <span className={[
                  'ml-[5px] text-[10px]',
                  isActive ? 'text-white/70' : 'text-text-3',
                ].join(' ')}>
                  {opt.count}
                </span>
              </button>
            )
          })}
        </div>
      ))}

      {/* Clear all — only when at least one filter active */}
      {anyActive && (
        <div className="flex items-center gap-[6px] pt-[2px]">
          <span className="text-[10px] text-text-3 italic">
            {[
              active.outcome,
              active.court,
              active.type && active.type.toLowerCase(),
            ].filter(Boolean).join(' · ')}
          </span>
          <button
            onClick={onClearAll}
            className="text-[10.5px] text-text-3 hover:text-text-1 underline transition-colors"
          >
            Clear filters
          </button>
        </div>
      )}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function SearchPage() {
  const [query, setQuery]         = useState('')
  const [active, setActive]       = useState<ActiveFilters>(NO_FILTERS)
  const [allOwn, setAllOwn]       = useState<OwnFileResult[]>([])
  const [allPublic, setAllPublic] = useState<PublicJudgmentResult[]>([])
  const [hasSearched, setHasSearched] = useState(false)
  const [isPending, setIsPending] = useState(false)
  const [errorMsg, setErrorMsg]   = useState<string | null>(null)
  // Guard against stale responses if user triggers two searches quickly
  const searchIdRef = useRef(0)

  const handleSearch = async () => {
    const q = query.trim()
    if (!q || isPending) return

    const thisId = ++searchIdRef.current
    setIsPending(true)
    setErrorMsg(null)

    try {
      const resp = await unifiedSearch(q)
      // Ignore stale responses from a previous search
      if (thisId !== searchIdRef.current) return
      const data = resp.data
      setAllOwn(data.from_your_files ?? [])
      setAllPublic(data.from_public_judgments ?? [])
      setActive(NO_FILTERS)
      setHasSearched(true)
    } catch (err: unknown) {
      if (thisId !== searchIdRef.current) return
      const msg =
        err && typeof err === 'object' && 'message' in err
          ? String((err as { message: unknown }).message)
          : 'Search failed. Please try again.'
      setErrorMsg(msg)
      console.error('[Search] error:', err)
    } finally {
      if (thisId === searchIdRef.current) setIsPending(false)
    }
  }

  const handleToggle = (dim: keyof ActiveFilters, value: string) => {
    setActive(prev => ({
      ...prev,
      [dim]: prev[dim] === value ? '' : value,  // toggle off if same chip clicked again
    }))
  }

  const filteredPublic = applyFilters(allPublic, active)
  const filterGroups   = hasSearched ? deriveFilterGroups(allPublic, active) : []
  const anyActive      = !!(active.outcome || active.court || active.type)

  return (
    <div className="max-w-[800px]">
      {/* Search box */}
      <div className="flex gap-[6px] mb-4">
        <input
          className="flex-1 px-[14px] py-[10px] border border-border-1 rounded-sm bg-white text-text-1 font-sans text-[13px] outline-none focus:border-border-2 transition-colors shadow-sm"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSearch()}
          placeholder={'Search judgments, e.g. “section 138 partner liability favour”'}
        />
        <Button variant="primary" onClick={handleSearch} disabled={isPending}>
          {isPending ? (
            <svg className="animate-spin h-[14px] w-[14px]" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
          ) : 'Search'}
        </Button>
      </div>

      {/* Dynamic filter bar — only appears after search with ≥ 2 distinct values per dimension */}
      <FilterBar
        groups={filterGroups}
        active={active}
        onToggle={handleToggle}
        onClearAll={() => setActive(NO_FILTERS)}
      />

      {/* Error banner */}
      {errorMsg && (
        <div className="mb-4 px-[12px] py-[10px] bg-red-50 border border-red-200 rounded-sm text-[12px] text-red-700">
          ⚠ {errorMsg}
        </div>
      )}

      {/* Results */}
      {hasSearched && (
        <>
          {allOwn.length > 0 && (
            <div className="mb-6">
              <div className="text-[10px] font-bold tracking-[0.7px] uppercase text-text-3 mb-3">
                From your files ({allOwn.length})
              </div>
              {allOwn.map(r => <OwnFileCard key={r.document_id} result={r} />)}
            </div>
          )}

          <div>
            <div className="text-[10px] font-bold tracking-[0.7px] uppercase text-text-3 mb-3">
              From public judgments (
              {anyActive
                ? `${filteredPublic.length} of ${allPublic.length}`
                : allPublic.length}
              )
            </div>
            {filteredPublic.length === 0 ? (
              <div className="text-[12px] text-text-3 py-6 text-center">
                {anyActive
                  ? 'No results match the selected filters.'
                  : 'No public judgments found.'}
              </div>
            ) : (
              filteredPublic.map(r => <PublicJudgmentCard key={r.id} result={r} />)
            )}
          </div>
        </>
      )}

      {!hasSearched && !isPending && !errorMsg && (
        <div className="text-center py-16">
          <div className="text-[30px] mb-3">⚖️</div>
          <p className="font-serif text-[16px] text-text-2 mb-1">Search by concept, not just keywords</p>
          <p className="text-[12px] text-text-3">
            Searches SC, P&H HC, and Punjab district court judgments simultaneously.
          </p>
        </div>
      )}
    </div>
  )
}

// ── Result cards ──────────────────────────────────────────────────────────────

function PublicJudgmentCard({ result }: { result: PublicJudgmentResult }) {
  const isVerified  = VERIFIED_SOURCES.includes(result.official_source ?? '')
  const excerpt     = result.enrichment?.facts || result.enrichment?.relevance || result.summary || ''
  const sourceUrl   = resolveSourceUrl(result.source_url)
  const outcomeLabel = result.outcome ? getOutcomeLabel(result.outcome) : null
  const isPositive   = outcomeLabel
    ? ['Petitioner won', 'Bail granted'].includes(outcomeLabel)
    : false

  return (
    <div className="bg-surface-2 border border-border-1 rounded-sm px-[11px] py-[10px] mb-[7px] hover:border-border-2 hover:bg-white transition-all">
      <div className="text-[12px] font-bold text-text-1 mb-[2px]">{result.case_name}</div>

      <div className="flex gap-[7px] text-[10px] text-text-3 mb-[6px] flex-wrap items-center">
        <span>{normaliseCourt(result.court)}</span>
        <span>·</span>
        <span>{result.year}</span>
        {result.primary_citation && (
          <><span>·</span><span className="font-mono text-text-2">{result.primary_citation}</span></>
        )}
        {outcomeLabel && (
          <>
            <span>·</span>
            <span className={isPositive ? 'text-green font-semibold' : 'text-text-2 font-medium'}>
              {outcomeLabel}
            </span>
          </>
        )}
        {result.matter_type && (
          <>
            <span>·</span>
            <span className="bg-surface-3 px-[5px] py-[1px] rounded-full text-text-3 capitalize">
              {result.matter_type}
            </span>
          </>
        )}
        {sourceUrl && (
          <a
            href={sourceUrl}
            target="_blank"
            rel="noopener noreferrer"
            onClick={e => e.stopPropagation()}
            className="text-blue underline"
            title={sourceUrl === ESCR_HOME ? 'Direct PDF unavailable — opens eSCR homepage' : undefined}
          >
            {sourceUrl === ESCR_HOME ? 'eSCR ↗' : 'Source ↗'}
          </a>
        )}
      </div>

      {excerpt && (
        <div className="text-[11px] text-text-2 leading-[1.5] mb-[6px]">{excerpt}</div>
      )}

      <VerifiedBadge
        status={isVerified ? 'verified' : 'unverified'}
        source={isVerified ? result.official_source : undefined}
      />
    </div>
  )
}

function OwnFileCard({ result }: { result: OwnFileResult }) {
  return (
    <div className="bg-surface-2 border border-border-1 rounded-sm px-[11px] py-[10px] mb-[7px] hover:border-border-2 hover:bg-white transition-all">
      <div className="text-[12px] font-bold text-text-1 mb-[2px]">{result.document_name}</div>
      <div className="flex gap-[7px] text-[10px] text-text-3 mb-1">
        {result.page != null && <span>Page {result.page}</span>}
        <span>Confidence: {result.confidence}/10</span>
      </div>
      <div className="text-[11px] text-text-2 leading-[1.5]">{result.excerpt}</div>
    </div>
  )
}
