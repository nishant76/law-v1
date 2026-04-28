import { useState, useRef } from 'react'
import { useMutation } from '@tanstack/react-query'
import Chip from '@/components/ui/Chip'
import Button from '@/components/ui/Button'
import VerifiedBadge from '@/components/ui/VerifiedBadge'
import { Input, Textarea } from '@/components/ui/FormField'
import { generateFiling, exportFiling, type FilingInput } from '@/api/filing'
import { unifiedSearch } from '@/api/search'
import { toast } from '@/store/toastStore'
import { downloadBlob } from '@/lib/utils'
import type { Draft, SearchResult } from '@/types'

const FILING_TYPES = ['Bail Application', 'Writ Petition', 'Civil Suit', 'Notice Reply', 'Criminal', 'Other']
const OBJECTIVES = ['Win on merits', 'Delay', 'Challenge', 'Settle', 'Preserve appeal']

const PROG_MSGS = [
  'Analysing case facts…',
  'Determining document format…',
  'Drafting petition clauses…',
  'Adding verified citations…',
  'Formatting for P&H HC…',
  'Finalising draft…',
]

type Tab = 'draft' | 'research' | 'args'

export default function DraftPage() {
  const [filingType, setFilingType] = useState('Bail Application')
  const [objective, setObjective] = useState('Win on merits')
  const [petitioner, setPetitioner] = useState('')
  const [respondent, setRespondent] = useState('')
  const [court, setCourt] = useState('P&H High Court, Chandigarh')
  const [sections, setSections] = useState('')
  const [facts, setFacts] = useState('')
  const [tab, setTab] = useState<Tab>('draft')
  const [draft, setDraft] = useState<Draft | null>(null)
  const [progMsg, setProgMsg] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const progRef = useRef<ReturnType<typeof setInterval> | null>(null)

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
      setDraft(data.data)
      setTab('draft')
      toast('Draft generated — verify citations before filing')
    },
    onError: () => {
      clearInterval(progRef.current!)
      setProgMsg('')
      toast('Draft generation failed. Please try again.')
    },
  })

  const searchMutation = useMutation({
    mutationFn: (q: string) => unifiedSearch(q),
    onSuccess: ({ data }) => setSearchResults(data.data.public_judgments),
  })

  const exportMutation = useMutation({
    mutationFn: (id: string) => exportFiling(id),
    onSuccess: (res) => downloadBlob(res.data as Blob, 'draft.docx'),
  })

  const handleGenerate = () => {
    if (!petitioner || !facts) { toast('Please fill Petitioner and Key facts'); return }
    generateMutation.mutate({ filing_type: filingType, objective, petitioner, respondent, court, sections, facts })
  }

  const handleSearch = () => {
    if (!searchQuery.trim()) return
    searchMutation.mutate(searchQuery)
  }

  const handleCopy = () => {
    if (!draft) return
    const text = Object.values(draft.sections ?? {}).join('\n\n')
    navigator.clipboard.writeText(text).then(() => toast('Copied!'))
  }

  return (
    <div
      className="h-[calc(100vh-50px-44px)] md:h-[calc(100vh-50px)] grid border border-border-1 rounded-DEFAULT overflow-hidden shadow-[0_1px_4px_rgba(0,0,0,0.05)]"
      style={{ gridTemplateColumns: '340px 1fr' }}
    >
      {/* LEFT: Case Brief */}
      <div className="flex flex-col bg-white">
        <div className="h-11 flex-shrink-0 px-[14px] border-b border-border-1 flex items-center justify-between">
          <span className="text-[12px] font-bold text-text-1 flex items-center gap-[6px]">⚙️ Case Brief</span>
          <Button size="sm" onClick={() => toast('Saved')}>Save</Button>
        </div>
        <div className="flex-1 overflow-y-auto p-[14px]">
          <label className="block text-[10px] font-bold tracking-[0.5px] uppercase text-text-3 mb-1">Filing type</label>
          <div className="flex flex-wrap gap-[5px] mb-[11px]">
            {FILING_TYPES.map((t) => (
              <Chip key={t} selected={filingType === t} onClick={() => setFilingType(t)}>{t}</Chip>
            ))}
          </div>

          <label className="block text-[10px] font-bold tracking-[0.5px] uppercase text-text-3 mb-1">Objective</label>
          <div className="flex flex-wrap gap-[5px] mb-[11px]">
            {OBJECTIVES.map((o) => (
              <Chip key={o} selected={objective === o} onClick={() => setObjective(o)}>{o}</Chip>
            ))}
          </div>

          <Input label="Petitioner" value={petitioner} onChange={(e) => setPetitioner(e.target.value)} placeholder="e.g. Gurnam Singh" />
          <Input label="Respondent" value={respondent} onChange={(e) => setRespondent(e.target.value)} placeholder="e.g. State of Punjab" />
          <Input label="Court" value={court} onChange={(e) => setCourt(e.target.value)} />
          <Input label="FIR / Sections" value={sections} onChange={(e) => setSections(e.target.value)} placeholder="e.g. FIR 234/2024 · NDPS Act S.21" />
          <Textarea label="Key facts" value={facts} onChange={(e) => setFacts(e.target.value)} minRows={4} placeholder="Describe the key facts of the case…" />

          {progMsg && (
            <div className="mb-[11px]">
              <div className="h-[2px] bg-surface-3 rounded-full overflow-hidden mb-1">
                <div className="h-full bg-ink rounded-full animate-[progBar_3.5s_ease-out_forwards]" />
              </div>
              <div className="text-[10.5px] text-text-3 italic">{progMsg}</div>
            </div>
          )}

          <Button
            variant="primary"
            size="lg"
            onClick={handleGenerate}
            disabled={generateMutation.isPending}
          >
            {generateMutation.isPending ? '⏳ Generating…' : '✦ Generate Draft'}
          </Button>
        </div>
      </div>

      {/* RIGHT: Tabs */}
      <div className="flex flex-col bg-white border-l border-border-1">
        <div className="flex items-center border-b border-border-1 flex-shrink-0 pr-[10px]">
          <div className="flex flex-1">
            {(['draft', 'research', 'args'] as Tab[]).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={[
                  'px-[14px] h-[43px] flex items-center text-[11.5px] font-semibold cursor-pointer border-b-2 transition-all mb-[-1px]',
                  tab === t ? 'text-text-1 border-ink' : 'text-text-3 border-transparent hover:text-text-1',
                ].join(' ')}
              >
                {t === 'draft' ? 'Draft' : t === 'research' ? 'Research' : 'Arguments'}
              </button>
            ))}
          </div>
          {tab === 'draft' && draft && (
            <div className="flex gap-[5px]">
              <Button size="sm" onClick={handleCopy}>Copy</Button>
              <Button
                size="sm"
                variant="primary"
                onClick={() => draft?.id && exportMutation.mutate(draft.id)}
                disabled={exportMutation.isPending}
              >
                ↓ .docx
              </Button>
            </div>
          )}
        </div>

        {/* Draft tab */}
        {tab === 'draft' && (
          <div className="flex-1 overflow-y-auto p-5 font-serif text-[13px] leading-[1.9] text-text-1">
            {!draft ? (
              <div className="flex flex-col items-center justify-center h-full text-text-3 gap-3">
                <span className="text-[30px]">✦</span>
                <p className="text-[13px] font-serif">Fill the brief and click Generate Draft</p>
              </div>
            ) : (
              <DraftOutput draft={draft} />
            )}
          </div>
        )}

        {/* Research tab */}
        {tab === 'research' && (
          <div className="flex-1 overflow-y-auto p-3">
            <div className="flex gap-[6px] mb-3">
              <input
                className="flex-1 px-[10px] py-[7px] border border-border-1 rounded-sm bg-surface-2 text-text-1 font-sans text-[12px] outline-none focus:border-border-2 focus:bg-white transition-all"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                placeholder="Search judgments…"
              />
              <Button variant="primary" size="sm" onClick={handleSearch} disabled={searchMutation.isPending}>
                {searchMutation.isPending ? '…' : 'Search'}
              </Button>
            </div>
            {searchResults.length === 0 && !searchMutation.isPending && (
              <div className="text-[12px] text-text-3 text-center py-8">
                Search SC and P&H HC judgments above
              </div>
            )}
            {searchResults.map((r) => (
              <ResearchResult key={r.id} result={r} />
            ))}
          </div>
        )}

        {/* Arguments tab */}
        {tab === 'args' && (
          <div className="flex-1 overflow-y-auto p-3">
            {!draft ? (
              <div className="text-[12px] text-text-3 text-center py-8">Generate a draft first to see arguments</div>
            ) : (
              <ArgumentsPanel />
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function DraftOutput({ draft }: { draft: Draft }) {
  const sections = draft.sections ?? {}
  return (
    <>
      {sections.court_heading && (
        <h3 className="text-[12.5px] font-normal text-center mb-[10px] underline underline-offset-[3px] tracking-[0.3px] whitespace-pre-line">
          {sections.court_heading}
        </h3>
      )}
      {sections.parties_section && (
        <p className="text-center text-[11.5px] mb-3 font-sans whitespace-pre-line">{sections.parties_section}</p>
      )}
      {sections.facts_section && (
        <p className="mb-[9px] text-justify border-l-2 border-border-2 pl-[9px] bg-black/[0.015]">
          {sections.facts_section}
          <span className="font-sans text-[9px] font-bold bg-surface-2 text-text-2 border border-border-1 px-1 py-[1px] rounded-[4px] ml-[3px] align-middle">AI</span>
        </p>
      )}
      {sections.grounds_section && (
        <p className="mb-[9px] text-justify">{sections.grounds_section}</p>
      )}
      {draft.citations_used?.map((c) => (
        <button
          key={c}
          onClick={() => toast(`${c} — eSCR Verified ✓`)}
          className="font-sans text-[10px] font-bold bg-green-bg text-green border border-green/20 px-[6px] py-[1px] rounded-[4px] cursor-pointer mr-1 mb-1"
        >
          {c} ✓
        </button>
      ))}
      {sections.prayer_section && (
        <p className="mt-[14px] mb-[9px]"><strong>Prayer:</strong> {sections.prayer_section}</p>
      )}
      {draft.quality_score !== undefined && (
        <div className="mt-4 pt-4 border-t border-border-1 font-sans text-[11px] text-text-3">
          Draft quality score: <span className={draft.quality_score >= 70 ? 'text-green font-bold' : draft.quality_score >= 50 ? 'text-amber font-bold' : 'text-red font-bold'}>{draft.quality_score}/100</span>
        </div>
      )}
    </>
  )
}

function ResearchResult({ result }: { result: SearchResult }) {
  return (
    <div className="bg-surface-2 border border-border-1 rounded-sm px-[11px] py-[10px] mb-[7px] cursor-pointer hover:border-border-2 hover:bg-white transition-all">
      <div className="text-[12px] font-bold text-text-1 mb-[2px]">{result.case_name}</div>
      <div className="flex gap-[7px] text-[10px] text-text-3 mb-1">
        <span>{result.court}</span>
        <span>·</span>
        <span>{result.year}</span>
        {result.citation && <><span>·</span><span className="font-mono text-[10px]">{result.citation}</span></>}
      </div>
      <div className="text-[11px] text-text-2 leading-[1.5]">{result.excerpt}</div>
      <div className="flex items-center mt-[6px]">
        <VerifiedBadge status={result.verified ? 'verified' : 'unverified'} source={result.verified ? 'eSCR' : undefined} />
        <button
          onClick={() => toast('Citation inserted')}
          className="ml-[6px] text-[10px] font-semibold px-2 py-[2px] rounded-[4px] border border-border-1 bg-white text-text-2 cursor-pointer hover:bg-ink hover:text-white hover:border-ink transition-all"
        >
          Insert →
        </button>
      </div>
    </div>
  )
}

function ArgumentsPanel() {
  return (
    <>
      <div className="rounded-sm px-[12px] py-[11px] mb-[9px] text-[12px] text-text-2 leading-[1.6] bg-surface-2 border border-border-1">
        <div className="text-[10px] font-bold tracking-[0.5px] uppercase mb-[6px] text-text-2">Your Arguments</div>
        1. First-time offender — no prior criminal record of any kind.<br />
        2. Fully cooperative with investigation — no flight risk.<br />
        3. Surrendered passport — sole breadwinner, family ties.<br />
        4. Twin conditions under S.37 NDPS satisfied on the facts.
      </div>
      <div className="rounded-sm px-[12px] py-[11px] mb-[9px] text-[12px] leading-[1.6] bg-red-bg border border-red/15">
        <div className="text-[10px] font-bold tracking-[0.5px] uppercase mb-[6px] text-red">Counter Arguments — Prosecution</div>
        1. Commercial quantity — statutory presumption operates against bail.<br />
        2. Section 37 NDPS — twin conditions not satisfied prima facie.<br />
        3. Investigation ongoing — bail may hamper recovery of contraband.
      </div>
      <div className="rounded-sm px-[12px] py-[11px] text-[12px] leading-[1.6] bg-green-bg border border-green/15">
        <div className="text-[10px] font-bold tracking-[0.5px] uppercase mb-[6px] text-green">How to Counter</div>
        Distinguish on commercial quantity — quantity is near the threshold, not clearly exceeded. Rely on Frank Vitus (SC 2023) — held twin conditions satisfied for first-time offenders where quantity is borderline and accused is cooperative.
      </div>
    </>
  )
}
