import { useState, useRef } from 'react'
import { unifiedSearch, openJudgmentPdf, downloadJudgmentPdf, getCitationSummary } from '@/api/search'
import { toast } from '@/store/toastStore'
import VerifiedBadge from '@/components/ui/VerifiedBadge'
import Button from '@/components/ui/Button'
import type { PublicJudgmentResult, OwnFileResult } from '@/types'

const PAGE_SIZE = 10

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
  outcome: string
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

function deriveFilterGroups(
  all: PublicJudgmentResult[],
  active: ActiveFilters,
): FilterGroup[] {
  const groups: FilterGroup[] = []

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

const VERIFIED_SOURCES = ['eSCR', 'P&H HC', 'escr', 'panhc']

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
          <span className="text-[10px] font-bold tracking-[0.5px] uppercase text-text-3 w-[44px] flex-shrink-0">
            {group.label}
          </span>
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
                <span className={['ml-[5px] text-[10px]', isActive ? 'text-white/70' : 'text-text-3'].join(' ')}>
                  {opt.count}
                </span>
              </button>
            )
          })}
        </div>
      ))}

      {anyActive && (
        <div className="flex items-center gap-[6px] pt-[2px]">
          <span className="text-[10px] text-text-3 italic">
            {[active.outcome, active.court, active.type && active.type.toLowerCase()]
              .filter(Boolean).join(' · ')}
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
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE)
  const searchIdRef = useRef(0)

  const handleSearch = async () => {
    const q = query.trim()
    if (!q || isPending) return

    const thisId = ++searchIdRef.current
    setIsPending(true)
    setErrorMsg(null)

    try {
      const resp = await unifiedSearch(q, 50)
      if (thisId !== searchIdRef.current) return
      const data = resp.data
      setAllOwn(data.from_your_files ?? [])
      setAllPublic(data.from_public_judgments ?? [])
      setActive(NO_FILTERS)
      setVisibleCount(PAGE_SIZE)
      setHasSearched(true)
    } catch (err: unknown) {
      if (thisId !== searchIdRef.current) return
      const msg =
        err && typeof err === 'object' && 'message' in err
          ? String((err as { message: unknown }).message)
          : 'Search failed. Please try again.'
      setErrorMsg(msg)
    } finally {
      if (thisId === searchIdRef.current) setIsPending(false)
    }
  }

  const handleToggle = (dim: keyof ActiveFilters, value: string) => {
    setActive(prev => ({ ...prev, [dim]: prev[dim] === value ? '' : value }))
    setVisibleCount(PAGE_SIZE)
  }

  const filteredPublic = applyFilters(allPublic, active)
  const filterGroups   = hasSearched ? deriveFilterGroups(allPublic, active) : []
  const anyActive      = !!(active.outcome || active.court || active.type)
  const visiblePublic  = filteredPublic.slice(0, visibleCount)
  const remaining      = filteredPublic.length - visibleCount

  return (
    <div className="max-w-[800px]">
      {/* Search box */}
      <div className="flex gap-[6px] mb-4">
        <input
          className="flex-1 px-[14px] py-[10px] border border-border-1 rounded-sm bg-white text-text-1 font-sans text-[13px] outline-none focus:border-border-2 transition-colors shadow-sm"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSearch()}
          placeholder='Search judgments, e.g. "section 138 partner liability"'
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

      <FilterBar
        groups={filterGroups}
        active={active}
        onToggle={handleToggle}
        onClearAll={() => { setActive(NO_FILTERS); setVisibleCount(PAGE_SIZE) }}
      />

      {errorMsg && (
        <div className="mb-4 px-[12px] py-[10px] bg-red-50 border border-red-200 rounded-sm text-[12px] text-red-700">
          ⚠ {errorMsg}
        </div>
      )}

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
                {anyActive ? 'No results match the selected filters.' : 'No public judgments found.'}
              </div>
            ) : (
              <>
                {visiblePublic.map(r => (
                  <PublicJudgmentCard key={r.id} result={r} />
                ))}

                {remaining > 0 && (
                  <button
                    onClick={() => setVisibleCount(v => v + PAGE_SIZE)}
                    className="w-full mt-2 py-[10px] text-[12px] font-semibold text-text-2 border border-border-1 rounded-sm hover:bg-surface-2 hover:text-text-1 transition-colors"
                  >
                    Load {Math.min(PAGE_SIZE, remaining)} more
                    <span className="ml-[6px] text-text-3 font-normal">
                      ({remaining} remaining)
                    </span>
                  </button>
                )}
              </>
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
  const [expanded, setExpanded]         = useState(false)
  const [summary, setSummary]           = useState<string | null>(
    result.enrichment?.facts || result.enrichment?.relevance || result.summary || null
  )
  const [summaryState, setSummaryState] = useState<'idle' | 'loading' | 'done' | 'error'>('idle')
  const [opening, setOpening]           = useState(false)
  const [downloading, setDownloading]   = useState(false)

  const isVerified   = VERIFIED_SOURCES.includes(result.official_source ?? '')
  const judgmentUrl  = result.judgment_url
  const officialUrl  = result.official_source_url || result.source_url
  const outcomeLabel = result.outcome ? getOutcomeLabel(result.outcome) : null
  const isPositive   = outcomeLabel
    ? ['Petitioner won', 'Bail granted'].includes(outcomeLabel)
    : false
  const safeFilename = (result.citation_key || result.id).replace(/[^a-z0-9-]/gi, '-') + '.pdf'

  const handleExpand = async () => {
    const nowExpanded = !expanded
    setExpanded(nowExpanded)
    if (nowExpanded && !summary && summaryState === 'idle') {
      setSummaryState('loading')
      try {
        const res = await getCitationSummary(result.id)
        setSummary(res.data.summary)
        setSummaryState('done')
      } catch {
        setSummaryState('error')
      }
    }
  }

  const handleView = async (e: React.MouseEvent) => {
    e.stopPropagation()
    if (!judgmentUrl || opening) return
    setOpening(true)
    const ok = await openJudgmentPdf(judgmentUrl)
    if (!ok) toast('Could not open the judgment PDF.')
    setOpening(false)
  }

  const handleDownload = async (e: React.MouseEvent) => {
    e.stopPropagation()
    if (!judgmentUrl || downloading) return
    setDownloading(true)
    const ok = await downloadJudgmentPdf(judgmentUrl, safeFilename)
    if (!ok) toast('Could not download the judgment PDF.')
    setDownloading(false)
  }

  return (
    <div
      className={[
        'border border-border-1 rounded-sm mb-[6px] transition-all cursor-pointer',
        expanded ? 'bg-white shadow-sm' : 'bg-surface-2 hover:bg-white hover:border-border-2',
      ].join(' ')}
      onClick={handleExpand}
    >
      {/* ── Header row ─────────────────────────────────────────────── */}
      <div className="px-[14px] pt-[12px] pb-[10px]">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="text-[12.5px] font-bold text-text-1 leading-snug mb-[4px]">
              {result.case_name}
            </div>

            <div className="flex items-center gap-[6px] flex-wrap text-[10.5px] text-text-3">
              <span>{normaliseCourt(result.court)}</span>
              <span>·</span>
              <span>{result.year}</span>
              {result.primary_citation && (
                <>
                  <span>·</span>
                  <span className="font-mono text-text-2">{result.primary_citation}</span>
                </>
              )}
              {outcomeLabel && (
                <>
                  <span>·</span>
                  <span className={isPositive ? 'text-green font-semibold' : 'text-text-2 font-medium'}>
                    {outcomeLabel}
                  </span>
                </>
              )}
            </div>
          </div>

          {/* Right: matter chip + expand chevron */}
          <div className="flex items-center gap-[6px] flex-shrink-0 pt-[1px]">
            {result.matter_type && (
              <span className="text-[9.5px] font-semibold uppercase tracking-[0.4px] bg-surface-3 text-text-3 px-[7px] py-[2px] rounded-full border border-border-1">
                {result.matter_type}
              </span>
            )}
            <svg
              className={['w-[14px] h-[14px] text-text-3 transition-transform flex-shrink-0', expanded ? 'rotate-180' : ''].join(' ')}
              viewBox="0 0 20 20" fill="currentColor"
            >
              <path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.17l3.71-3.94a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clipRule="evenodd" />
            </svg>
          </div>
        </div>

        {!expanded && (
          <div className="mt-[6px] text-[10px] text-text-3 italic">
            Click to read summary and open PDF
          </div>
        )}
      </div>

      {/* ── Expanded panel ─────────────────────────────────────────── */}
      {expanded && (
        <div
          className="border-t border-border-1 px-[14px] pt-[10px] pb-[12px]"
          onClick={e => e.stopPropagation()}
        >
          {/* AI Summary */}
          <div className="mb-[10px]">
            <div className="text-[9.5px] font-bold uppercase tracking-[0.5px] text-text-3 mb-[5px]">
              AI Summary
            </div>

            {summaryState === 'loading' && (
              <div className="flex items-center gap-[6px] text-[11px] text-text-3">
                <svg className="animate-spin h-[12px] w-[12px]" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                Generating summary…
              </div>
            )}

            {summaryState !== 'loading' && summary && (
              <p className="text-[12px] text-text-2 leading-[1.6]">{summary}</p>
            )}

            {summaryState === 'error' && !summary && (
              <p className="text-[11px] text-text-3 italic">Summary not available.</p>
            )}

            {summaryState === 'done' && !summary && (
              <p className="text-[11px] text-text-3 italic">No text available for this judgment.</p>
            )}
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-[8px] flex-wrap">
            {judgmentUrl && (
              <button
                onClick={handleView}
                disabled={opening}
                className="inline-flex items-center gap-[5px] px-[12px] py-[6px] bg-ink text-white text-[11.5px] font-semibold rounded-sm hover:bg-ink/90 disabled:opacity-50 transition-colors"
              >
                <svg className="w-[13px] h-[13px]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
                {opening ? 'Opening…' : 'View PDF'}
              </button>
            )}

            {judgmentUrl && (
              <button
                onClick={handleDownload}
                disabled={downloading}
                className="inline-flex items-center gap-[5px] px-[12px] py-[6px] bg-white border border-border-2 text-text-1 text-[11.5px] font-semibold rounded-sm hover:bg-surface-2 disabled:opacity-50 transition-colors"
              >
                <svg className="w-[13px] h-[13px]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                {downloading ? 'Downloading…' : 'Download'}
              </button>
            )}

            {officialUrl && (
              <a
                href={officialUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-[4px] text-[11px] text-text-3 hover:text-text-1 underline transition-colors"
              >
                Official source
                <svg className="w-[10px] h-[10px]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </a>
            )}

            <div className="ml-auto">
              <VerifiedBadge
                status={isVerified ? 'verified' : 'unverified'}
                source={isVerified ? result.official_source : undefined}
              />
            </div>
          </div>
        </div>
      )}
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
