import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { unifiedSearch } from '@/api/search'
import VerifiedBadge from '@/components/ui/VerifiedBadge'
import Button from '@/components/ui/Button'
import type { PublicJudgmentResult, OwnFileResult } from '@/types'

const OUTCOME_FILTERS = [
  { value: '', label: 'All results' },
  { value: 'petitioner', label: 'Favour of petitioner' },
  { value: 'respondent', label: 'Favour of respondent' },
  { value: 'bail_granted', label: 'Bail granted' },
  { value: 'bail_refused', label: 'Bail refused' },
]

const VERIFIED_SOURCES = ['eSCR', 'P&H HC']

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [outcome, setOutcome] = useState('')
  const [results, setResults] = useState<{
    own: OwnFileResult[]
    public: PublicJudgmentResult[]
  } | null>(null)

  const searchMutation = useMutation({
    mutationFn: () => unifiedSearch(query, outcome || undefined),
    onSuccess: ({ data }) => {
      setResults({
        own: data.from_your_files ?? [],
        public: data.from_public_judgments ?? [],
      })
    },
  })

  const handleSearch = () => {
    if (!query.trim()) return
    searchMutation.mutate()
  }

  return (
    <div className="max-w-[800px]">
      {/* Search box */}
      <div className="flex gap-[6px] mb-4">
        <input
          className="flex-1 px-[14px] py-[10px] border border-border-1 rounded-sm bg-white text-text-1 font-sans text-[13px] outline-none focus:border-border-2 transition-colors shadow-sm"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          placeholder={'Search judgments, e.g. \u201csection 138 partner liability favour\u201d'}
        />
        <Button variant="primary" onClick={handleSearch} disabled={searchMutation.isPending}>
          {searchMutation.isPending ? (
            <svg className="animate-spin h-[14px] w-[14px]" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
          ) : 'Search'}
        </Button>
      </div>

      {/* Outcome filter */}
      <div className="flex gap-[5px] flex-wrap mb-5">
        {OUTCOME_FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => setOutcome(f.value)}
            className={[
              'text-[11px] font-semibold px-[10px] py-1 rounded-full border cursor-pointer transition-all',
              outcome === f.value
                ? 'bg-ink text-white border-ink'
                : 'bg-surface-2 text-text-2 border-border-1 hover:bg-surface-3',
            ].join(' ')}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Results */}
      {results && (
        <>
          {results.own.length > 0 && (
            <div className="mb-6">
              <div className="text-[10px] font-bold tracking-[0.7px] uppercase text-text-3 mb-3">
                From your files ({results.own.length})
              </div>
              {results.own.map((r) => <OwnFileCard key={r.document_id} result={r} />)}
            </div>
          )}
          <div>
            <div className="text-[10px] font-bold tracking-[0.7px] uppercase text-text-3 mb-3">
              From public judgments ({results.public.length})
            </div>
            {results.public.length === 0 ? (
              <div className="text-[12px] text-text-3 py-6 text-center">No public judgments found.</div>
            ) : (
              results.public.map((r) => <PublicJudgmentCard key={r.id} result={r} />)
            )}
          </div>
        </>
      )}

      {!results && !searchMutation.isPending && (
        <div className="text-center py-16">
          <div className="text-[30px] mb-3">⚖️</div>
          <p className="font-serif text-[16px] text-text-2 mb-1">Search by concept, not just keywords</p>
          <p className="text-[12px] text-text-3">Searches SC, P&H HC, and Punjab district court judgments simultaneously.</p>
        </div>
      )}
    </div>
  )
}

function PublicJudgmentCard({ result }: { result: PublicJudgmentResult }) {
  const isVerified = VERIFIED_SOURCES.includes(result.official_source ?? '')
  const excerpt =
    result.enrichment?.facts ||
    result.enrichment?.relevance ||
    result.summary ||
    ''

  return (
    <div className="bg-surface-2 border border-border-1 rounded-sm px-[11px] py-[10px] mb-[7px] hover:border-border-2 hover:bg-white transition-all cursor-pointer">
      <div className="text-[12px] font-bold text-text-1 mb-[2px]">{result.case_name}</div>
      <div className="flex gap-[7px] text-[10px] text-text-3 mb-1 flex-wrap">
        <span>{result.court}</span>
        <span>·</span>
        <span>{result.year}</span>
        {result.primary_citation && (
          <><span>·</span><span className="font-mono">{result.primary_citation}</span></>
        )}
        {result.source_url && (
          <a
            href={result.source_url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="text-blue underline"
          >
            Source ↗
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
    <div className="bg-surface-2 border border-border-1 rounded-sm px-[11px] py-[10px] mb-[7px] hover:border-border-2 hover:bg-white transition-all cursor-pointer">
      <div className="text-[12px] font-bold text-text-1 mb-[2px]">{result.document_name}</div>
      <div className="flex gap-[7px] text-[10px] text-text-3 mb-1">
        {result.page != null && <span>Page {result.page}</span>}
        <span>Confidence: {result.confidence}/10</span>
      </div>
      <div className="text-[11px] text-text-2 leading-[1.5]">{result.excerpt}</div>
    </div>
  )
}
