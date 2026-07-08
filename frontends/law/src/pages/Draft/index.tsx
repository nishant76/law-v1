import { useState, useRef, useMemo, useCallback } from 'react'
import Button from '@/components/ui/Button'
import DropZone from '@/components/ui/DropZone'
import MarkdownText from '@/components/ui/MarkdownText'
import { Input, Textarea } from '@/components/ui/FormField'
import {
  generateFilingTemplate,
  generateFilingTemplateFromFile,
  exportFilingTemplate,
  type FilingTemplateResponse,
  type KeyField,
} from '@/api/filing'
import { unifiedSearch } from '@/api/search'
import { toast } from '@/store/toastStore'
import { downloadBlob } from '@/lib/utils'
import type { PublicJudgmentResult } from '@/types'

type Step = 'input' | 'edit'

// ── Template fill helper (client-side, live) ────────────────────────────────────

const TOKEN_RE = /\{\{(\w+)\}\}/g

function fillTemplate(
  template: string,
  fields: KeyField[],
  values: Record<string, string>,
  citations: PublicJudgmentResult[],
  forView: boolean,
): string {
  let out = template.replace(TOKEN_RE, (_m, key: string) => {
    const v = (values[key] ?? '').trim()
    if (v) return v
    const label = fields.find(f => f.key === key)?.label ?? key
    return forView ? `⟦${label}⟧` : `[${label}]`
  })
  if (citations.length) {
    const items = citations
      .map((c, i) => {
        const cite = c.primary_citation ? `, ${c.primary_citation}` : ''
        return `${i + 1}. ${c.case_name}${cite} (${c.court}${c.year ? `, ${c.year}` : ''})`
      })
      .join('\n')
    out += `\n\n## Citations Relied Upon\n\n${items}`
  }
  return out
}

// ── Step 1: Input ───────────────────────────────────────────────────────────────

interface InputStepProps {
  court: string
  details: string
  file: File | null
  isGenerating: boolean
  errMsg: string | null
  onChange: (patch: Partial<{ court: string; details: string; file: File | null }>) => void
  onGenerate: () => void
}

function InputStep({
  court, details, file, isGenerating, errMsg, onChange, onGenerate,
}: InputStepProps) {
  return (
    <div className="max-w-[640px] mx-auto">
      <h1 className="font-serif text-[20px] tracking-[-0.2px] text-text-1 mb-[4px]">Draft a Filing</h1>
      <p className="text-[12px] text-text-3 mb-5">
        Describe your filing in plain language — or upload an existing draft to improve. We'll produce a
        properly formatted draft with blanks you fill in on the next screen.
      </p>

      <Input
        label="Court"
        value={court}
        onChange={e => onChange({ court: e.target.value })}
        placeholder="e.g. Punjab & Haryana High Court, Chandigarh"
      />

      <Textarea
        label="Describe your draft"
        value={details}
        onChange={e => onChange({ details: e.target.value })}
        minRows={6}
        placeholder="Write the facts and what you want, even in rough/informal language. e.g. 'bail for my client Gurnam, arrested in NDPS case FIR 234/2024, only 10g recovered, first offence, in custody 4 months, investigation complete…'"
      />

      {/* Or upload */}
      <div className="mt-[14px]">
        <div className="flex items-center gap-[10px] mb-[8px]">
          <div className="h-[1px] flex-1 bg-border-1" />
          <span className="text-[10px] font-bold tracking-[0.5px] uppercase text-text-3">or improve an existing draft</span>
          <div className="h-[1px] flex-1 bg-border-1" />
        </div>
        {file ? (
          <div className="flex items-center justify-between gap-2 px-[12px] py-[9px] bg-surface-2 border border-border-1 rounded-sm">
            <span className="text-[12px] text-text-1 truncate">📄 {file.name}</span>
            <button onClick={() => onChange({ file: null })} className="text-[12px] text-text-3 hover:text-text-1 flex-shrink-0">Remove</button>
          </div>
        ) : (
          <DropZone onFile={f => onChange({ file: f })} />
        )}
      </div>

      {errMsg && <p className="mt-3 text-[11.5px] text-red-500">{errMsg}</p>}

      <div className="mt-5 flex items-center gap-[12px]">
        <Button variant="primary" size="lg" onClick={onGenerate} disabled={isGenerating}>
          {isGenerating ? '⏳ Drafting…' : '✦ Generate Draft'}
        </Button>
        {isGenerating && <span className="text-[11px] text-text-3 italic">Rewriting into legal format — this may take 20–40 seconds…</span>}
      </div>
    </div>
  )
}

// ── Citations panel (find & add) ────────────────────────────────────────────────

function CitationsPanel({
  selected, onToggle,
}: {
  selected: PublicJudgmentResult[]
  onToggle: (r: PublicJudgmentResult) => void
}) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<PublicJudgmentResult[]>([])
  const [isPending, setIsPending] = useState(false)
  const searchIdRef = useRef(0)

  const handleSearch = async () => {
    const q = query.trim()
    if (!q || isPending) return
    const id = ++searchIdRef.current
    setIsPending(true)
    try {
      const { data } = await unifiedSearch(q)
      if (id !== searchIdRef.current) return
      setResults(data.from_public_judgments ?? [])
    } catch {
      if (id === searchIdRef.current) toast('Citation search failed.')
    } finally {
      if (id === searchIdRef.current) setIsPending(false)
    }
  }

  const selectedIds = new Set(selected.map(s => s.id))

  return (
    <div>
      <div className="flex gap-[6px] mb-[10px]">
        <input
          className="flex-1 px-[10px] py-[7px] border border-border-1 rounded-sm bg-white text-text-1 text-[12px] outline-none focus:border-border-2 placeholder:text-text-3"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSearch()}
          placeholder="e.g. S.37 NDPS bail first offender"
        />
        <Button size="sm" variant="primary" onClick={handleSearch} disabled={isPending || !query.trim()}>
          {isPending ? '…' : 'Search'}
        </Button>
      </div>

      {selected.length > 0 && (
        <div className="mb-[10px] flex flex-wrap gap-[5px]">
          {selected.map(r => (
            <button
              key={r.id}
              onClick={() => onToggle(r)}
              className="flex items-center gap-[5px] text-[10.5px] font-medium bg-green-bg text-green border border-green/30 px-[8px] py-[3px] rounded-full hover:bg-green/10"
              title="Remove from draft"
            >
              <span className="max-w-[180px] truncate">✓ {r.case_name}</span>
              <span className="opacity-60">✕</span>
            </button>
          ))}
        </div>
      )}

      <div className="space-y-[6px] max-h-[300px] overflow-y-auto">
        {results.map(r => {
          const added = selectedIds.has(r.id)
          return (
            <div key={r.id} className="border border-border-1 rounded-sm px-[10px] py-[8px] bg-white">
              <div className="text-[11.5px] font-semibold text-text-1 leading-snug mb-[2px]">{r.case_name}</div>
              <div className="flex flex-wrap items-center gap-[5px] text-[10px] text-text-3 mb-[5px]">
                <span>{r.court}</span><span>·</span><span>{r.year}</span>
                {r.primary_citation && (<><span>·</span><span className="font-mono text-text-2">{r.primary_citation}</span></>)}
              </div>
              <button
                onClick={() => onToggle(r)}
                className="text-[11px] font-semibold text-ink hover:underline disabled:text-text-3 disabled:no-underline"
                disabled={added}
              >
                {added ? 'Added' : '+ Add to draft'}
              </button>
            </div>
          )
        })}
        {!isPending && results.length === 0 && (
          <p className="text-[11px] text-text-3 py-2">Search verified judgments to weave into your draft.</p>
        )}
      </div>
    </div>
  )
}

// ── Step 2: Edit (live fill) ──────────────────────────────────────────────────

interface EditScreenProps {
  template: FilingTemplateResponse
  values: Record<string, string>
  onValue: (key: string, val: string) => void
  citations: PublicJudgmentResult[]
  onToggleCitation: (r: PublicJudgmentResult) => void
  onNew: () => void
  onExport: () => void
  isExporting: boolean
}

function EditScreen({
  template, values, onValue, citations, onToggleCitation, onNew, onExport, isExporting,
}: EditScreenProps) {
  const filledMarkdown = useMemo(
    () => fillTemplate(template.template_markdown, template.key_fields, values, citations, true),
    [template, values, citations],
  )
  const filledCount = template.key_fields.filter(f => (values[f.key] ?? '').trim()).length

  const handleCopy = () => {
    const plain = fillTemplate(template.template_markdown, template.key_fields, values, citations, false)
    navigator.clipboard.writeText(plain).then(() => toast('Copied to clipboard'))
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-4">
        <div className="min-w-0">
          <h1 className="font-serif text-[19px] tracking-[-0.2px] text-text-1 truncate">{template.title}</h1>
          <p className="text-[11.5px] text-text-3">
            Fill the key details on the right — the draft updates live. {filledCount}/{template.key_fields.length} filled.
          </p>
        </div>
        <div className="flex gap-[6px] flex-shrink-0">
          <Button size="sm" onClick={onNew}>← New</Button>
          <Button size="sm" onClick={handleCopy}>Copy</Button>
          <Button size="sm" variant="primary" onClick={onExport} disabled={isExporting}>
            {isExporting ? 'Exporting…' : '↓ .docx'}
          </Button>
        </div>
      </div>

      <div className="grid gap-4" style={{ gridTemplateColumns: 'minmax(0, 1fr) 320px' }}>
        {/* Left: live draft */}
        <div className="bg-white border border-border-1 rounded-DEFAULT px-[26px] py-[22px] font-serif text-[12.5px] leading-[1.85] text-text-1 min-h-[400px]">
          <MarkdownText text={filledMarkdown} />
        </div>

        {/* Right: key details + citations */}
        <div className="space-y-[18px]">
          <div>
            <div className="text-[10px] font-bold tracking-[0.6px] uppercase text-text-3 mb-[10px]">Key Details</div>
            <div className="space-y-[10px]">
              {template.key_fields.map(f => (
                <div key={f.key}>
                  <label className="block text-[11px] font-semibold text-text-2 mb-[3px]">{f.label}</label>
                  <input
                    className="w-full px-[10px] py-[7px] border border-border-2 rounded-sm bg-white text-text-1 text-[12px] outline-none focus:border-ink placeholder:text-text-3"
                    value={values[f.key] ?? ''}
                    onChange={e => onValue(f.key, e.target.value)}
                    placeholder={f.example || ''}
                  />
                </div>
              ))}
              {template.key_fields.length === 0 && (
                <p className="text-[11px] text-text-3">No fill-in details were detected for this draft.</p>
              )}
            </div>
          </div>

          <div className="border-t border-border-1 pt-[16px]">
            <div className="text-[10px] font-bold tracking-[0.6px] uppercase text-text-3 mb-[10px]">Find &amp; Add Citations</div>
            <CitationsPanel selected={citations} onToggle={onToggleCitation} />
          </div>
        </div>
      </div>

      <p className="mt-3 text-[11px] text-text-3">
        ⚠️ Review before filing — verify citations, case numbers, and all facts. Highlighted blanks must be filled.
      </p>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function DraftPage() {
  const [step, setStep] = useState<Step>('input')
  const [court, setCourt] = useState('Punjab & Haryana High Court, Chandigarh')
  const [details, setDetails] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const [errMsg, setErrMsg] = useState<string | null>(null)
  const genIdRef = useRef(0)

  const [template, setTemplate] = useState<FilingTemplateResponse | null>(null)
  const [values, setValues] = useState<Record<string, string>>({})
  const [citations, setCitations] = useState<PublicJudgmentResult[]>([])
  const [isExporting, setIsExporting] = useState(false)

  const patchInput = useCallback((patch: Partial<{ court: string; details: string; file: File | null }>) => {
    if (patch.court !== undefined) setCourt(patch.court)
    if (patch.details !== undefined) setDetails(patch.details)
    if (patch.file !== undefined) setFile(patch.file)
    setErrMsg(null)
  }, [])

  // Plain async/await (not useMutation) per CLAUDE.md GAP-050.
  const handleGenerate = async () => {
    if (isGenerating) return
    if (!file && !details.trim()) {
      setErrMsg('Describe your draft or upload a document to improve.')
      return
    }
    const id = ++genIdRef.current
    setIsGenerating(true)
    setErrMsg(null)
    try {
      const res = file
        ? await generateFilingTemplateFromFile(file, { court })
        : await generateFilingTemplate({ court, input_text: details })
      if (id !== genIdRef.current) return
      const data = res.data
      if (!data?.template_markdown) {
        setErrMsg('Draft generation failed — please try again.')
        return
      }
      // Pre-fill any detail the lawyer already gave in the description — so it
      // appears in both the draft and the textbox without re-typing.
      const init: Record<string, string> = {}
      data.key_fields.forEach(f => { init[f.key] = f.value ?? '' })
      setValues(init)
      setCitations([])
      setTemplate(data)
      setStep('edit')
    } catch (err: unknown) {
      if (id !== genIdRef.current) return
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setErrMsg(msg || 'Draft generation failed. Please try again.')
    } finally {
      if (id === genIdRef.current) setIsGenerating(false)
    }
  }

  const toggleCitation = (r: PublicJudgmentResult) => {
    setCitations(prev =>
      prev.find(s => s.id === r.id) ? prev.filter(s => s.id !== r.id) : [...prev, r],
    )
  }

  const handleExport = async () => {
    if (!template || isExporting) return
    setIsExporting(true)
    try {
      const filled = fillTemplate(template.template_markdown, template.key_fields, values, citations, false)
      const res = await exportFilingTemplate({
        title: template.title,
        filled_markdown: filled,
        court,
      })
      downloadBlob(res.data as Blob, 'draft.docx')
    } catch {
      toast('Export failed.')
    } finally {
      setIsExporting(false)
    }
  }

  const handleNew = () => {
    setStep('input')
    setDetails('')
    setFile(null)
    setTemplate(null)
    setValues({})
    setCitations([])
    setErrMsg(null)
  }

  return (
    <div className="py-6 px-4 md:px-6 max-w-[1100px]">
      {step === 'input' && (
        <InputStep
          court={court}
          details={details}
          file={file}
          isGenerating={isGenerating}
          errMsg={errMsg}
          onChange={patchInput}
          onGenerate={handleGenerate}
        />
      )}

      {step === 'edit' && template && (
        <EditScreen
          template={template}
          values={values}
          onValue={(key, val) => setValues(prev => ({ ...prev, [key]: val }))}
          citations={citations}
          onToggleCitation={toggleCitation}
          onNew={handleNew}
          onExport={handleExport}
          isExporting={isExporting}
        />
      )}
    </div>
  )
}
