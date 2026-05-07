import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { generateSynopsisFromUpload, type Synopsis } from '@/api/synopsis'
import DropZone from '@/components/ui/DropZone'
import Button from '@/components/ui/Button'
import { renderInline } from '@/components/ui/MarkdownText'
import { toast } from '@/store/toastStore'

// ── Wrong document type card ──────────────────────────────────────────────────

const DOC_TYPE_LABELS: Record<string, string> = {
  legal_notice:      'Legal Notice',
  contract:          'Contract',
  affidavit:         'Affidavit',
  written_statement: 'Written Statement',
  other:             'Non-judgment document',
}

function WrongDocTypeCard({
  docType,
  filename,
  onReset,
}: {
  docType: string
  filename: string
  onReset: () => void
}) {
  const navigate = useNavigate()
  const label = DOC_TYPE_LABELS[docType] ?? docType.replace(/_/g, ' ')
  const isLegalNotice = docType === 'legal_notice'

  return (
    <div className="max-w-[500px] mx-auto mt-9">
      {/* Icon + headline */}
      <div className="flex flex-col items-center text-center mb-5">
        <div className="w-[44px] h-[44px] rounded-full bg-amber-bg border border-amber/30 flex items-center justify-center mb-3">
          <span className="text-[20px]">⚠</span>
        </div>
        <p className="font-serif text-[18px] tracking-[-0.2px] text-text-1 leading-snug mb-[6px]">
          Wrong document type
        </p>
        <p className="text-[12px] text-text-3">
          {filename && <span className="font-medium text-text-2">{filename}</span>}
          {filename && ' appears to be a '}
          {!filename && 'This appears to be a '}
          <span className="font-semibold text-amber">{label}</span>.
        </p>
      </div>

      {/* Explanation card */}
      <div className="bg-white border border-border-1 rounded-DEFAULT px-[18px] py-[14px] mb-4">
        <div className="text-[10px] font-bold tracking-[0.7px] uppercase text-text-3 mb-[8px]">
          Case Synopsis works best with
        </div>
        <ul className="space-y-[5px] mb-[14px]">
          {['Court judgments', 'High Court / Supreme Court orders', 'Petitions filed in court'].map((item, i) => (
            <li key={i} className="flex items-start gap-[7px] text-[12.5px] text-text-2">
              <span className="text-green text-[11px] mt-[2px] flex-shrink-0">✓</span>
              {item}
            </li>
          ))}
        </ul>

        <div className="text-[10px] font-bold tracking-[0.7px] uppercase text-text-3 mb-[8px]">
          What to use for a {label}
        </div>
        <div className="space-y-[8px]">
          {isLegalNotice && (
            <div
              className="flex items-start gap-[10px] p-[10px] rounded-[6px] border border-border-1 hover:border-ink/30 cursor-pointer group"
              onClick={() => navigate('/reply')}
            >
              <div className="w-[28px] h-[28px] rounded-[5px] bg-surface-2 flex items-center justify-center flex-shrink-0 text-[13px]">
                ↩
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-[12px] font-semibold text-text-1 group-hover:underline">
                  Smart Reply Generator
                </div>
                <div className="text-[11px] text-text-3 leading-snug mt-[1px]">
                  Extracts every allegation, suggests legal grounds, drafts a complete reply
                </div>
              </div>
              <span className="text-text-3 text-[12px] mt-[4px]">→</span>
            </div>
          )}
          <div
            className="flex items-start gap-[10px] p-[10px] rounded-[6px] border border-border-1 hover:border-ink/30 cursor-pointer group"
            onClick={() => navigate('/pdf')}
          >
            <div className="w-[28px] h-[28px] rounded-[5px] bg-surface-2 flex items-center justify-center flex-shrink-0 text-[13px]">
              ⊞
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-[12px] font-semibold text-text-1 group-hover:underline">
                PDF Extractor
              </div>
              <div className="text-[11px] text-text-3 leading-snug mt-[1px]">
                Extracts parties, dates, amounts, conditions and lets you Q&amp;A the document
              </div>
            </div>
            <span className="text-text-3 text-[12px] mt-[4px]">→</span>
          </div>
        </div>
      </div>

      {/* Reset */}
      <div className="text-center">
        <button
          onClick={onReset}
          className="text-[11.5px] font-semibold text-ink hover:underline"
        >
          ← Try a different file
        </button>
      </div>
    </div>
  )
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function splitSentences(text: string): string[] {
  // Split on period+space only when NOT preceded by a common abbreviation.
  // Avoids splitting "Mr. Kunal", "Dr. Singh", "Hon'ble", "Art. 21", "Smt. X", "Ltd.", "No." etc.
  const ABBR = /\b(Mr|Mrs|Ms|Dr|Prof|Hon|Smt|Shri|St|Lt|Col|Gen|Pvt|Ltd|Co|No|Art|Sec|Para|vs|viz|etc|approx|govt|dept)\s*$/i
  const parts = text.split(/(?<=\.)\s+/)
  const raw: string[] = []
  let buffer = ''
  for (const part of parts) {
    const candidate = buffer ? buffer + ' ' + part : part
    if (buffer && ABBR.test(buffer)) {
      buffer = candidate
    } else {
      if (buffer) raw.push(buffer)
      buffer = part
    }
  }
  if (buffer) raw.push(buffer)

  // Merge short orphan fragments (< 20 chars) into next sentence
  const merged: string[] = []
  for (let i = 0; i < raw.length; i++) {
    if (raw[i].length < 20 && i + 1 < raw.length) {
      raw[i + 1] = raw[i] + ' ' + raw[i + 1]
    } else {
      merged.push(raw[i])
    }
  }
  return merged.filter(s => s.length > 4)
}

function confidenceColor(n: number) {
  if (n >= 7) return 'text-green'
  if (n >= 4) return 'text-amber'
  return 'text-red-500'
}

// ── Sub-components ────────────────────────────────────────────────────────────

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="py-[13px] border-b border-border-1 last:border-b-0">
      <div className="text-[10px] font-bold tracking-[0.7px] uppercase text-text-3 mb-[7px]">{label}</div>
      <div className="text-[12.5px] text-text-2 leading-[1.6]">{children}</div>
    </div>
  )
}

function BulletList({ items }: { items: string[] }) {
  return (
    <ul className="space-y-[4px]">
      {items.map((item, i) => (
        <li key={i} className="flex items-start gap-[7px]">
          <span className="text-[10px] text-text-3 mt-[4px] flex-shrink-0">●</span>
          <span>{renderInline(item)}</span>
        </li>
      ))}
    </ul>
  )
}

function PartyRow({ label, value }: { label: string; value: string | null }) {
  if (!value) return null
  return (
    <div className="flex items-start gap-[10px] py-[6px] border-b border-border-1 last:border-b-0">
      <span className="text-[11px] text-text-3 w-[110px] flex-shrink-0 mt-[1px]">{label}</span>
      <span className="text-[12.5px] font-semibold text-text-1">{value}</span>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function SynopsisPage() {
  const [synopsis, setSynopsis] = useState<Synopsis | null>(null)
  const [filename, setFilename] = useState('')
  const [wrongDocType, setWrongDocType] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: (file: File) => generateSynopsisFromUpload(file),
    onSuccess: (res) => {
      const err = res.data?.error as (typeof res.data.error & { document_type?: string }) | undefined
      if (err?.code === 'wrong_document_type') {
        setWrongDocType(err.document_type ?? 'other')
        return
      }
      const data = res.data?.data
      if (!data) { toast('Synopsis generation failed.'); return }
      setSynopsis(data)
    },
    onError: () => toast('Synopsis generation failed. Please try again.'),
  })

  const handleFile = (file: File) => {
    setFilename(file.name)
    setWrongDocType(null)
    mutation.mutate(file)
  }

  const handleReset = () => {
    setSynopsis(null)
    setFilename('')
    setWrongDocType(null)
    mutation.reset()
  }

  // ── Wrong document type ───────────────────────────────────────────────────

  if (wrongDocType) {
    return (
      <WrongDocTypeCard
        docType={wrongDocType}
        filename={filename}
        onReset={handleReset}
      />
    )
  }

  // ── Upload state ──────────────────────────────────────────────────────────

  if (!synopsis) {
    return (
      <div className="max-w-[500px] mx-auto mt-9">
        <p className="font-serif text-[20px] tracking-[-0.2px] text-text-1 mb-[5px] text-center">
          Case Synopsis Generator
        </p>
        <p className="text-[12px] text-text-3 mb-6 text-center">
          Upload any judgment or petition. Get a structured one-pager in seconds.
        </p>
        <DropZone onFile={handleFile} />
        {mutation.isPending && (
          <div className="mt-4 text-center">
            <div className="text-[11px] text-text-3 italic mb-[6px]">
              {filename ? `Analysing ${filename}…` : 'Generating synopsis…'}
            </div>
            <div className="h-[2px] bg-surface-3 rounded-full overflow-hidden mx-8">
              <div className="h-full bg-ink rounded-full animate-pulse" style={{ width: '60%' }} />
            </div>
          </div>
        )}
        {mutation.isError && (
          <div className="mt-3 text-center text-[11.5px] text-red-500">
            Generation failed. Please check the file and try again.
          </div>
        )}
      </div>
    )
  }

  // ── Result ────────────────────────────────────────────────────────────────

  const facts = synopsis.facts ? splitSentences(synopsis.facts) : []
  const held = synopsis.held ? splitSentences(synopsis.held) : []
  const relief = synopsis.relief_granted ? splitSentences(synopsis.relief_granted) : []

  return (
    <div className="max-w-[760px]">

      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-5">
        <div className="flex-1 min-w-0">
          <h1 className="font-serif text-[20px] tracking-[-0.2px] text-text-1 leading-tight mb-[3px]">
            {synopsis.case_name || 'Case Synopsis'}
          </h1>
          <div className="flex items-center gap-[8px] flex-wrap text-[12px] text-text-3">
            {synopsis.court && <span>{synopsis.court}</span>}
            {synopsis.court && synopsis.judgment_date && <span>·</span>}
            {synopsis.judgment_date && <span>{synopsis.judgment_date}</span>}
            {synopsis.case_number && (
              <>
                <span>·</span>
                <span className="font-mono">{synopsis.case_number}</span>
              </>
            )}
          </div>
        </div>
        <Button size="sm" onClick={handleReset}>← New</Button>
      </div>

      {/* Confidence badge */}
      <div className="flex items-center gap-[8px] mb-4">
        <span className={`text-[11px] font-bold ${confidenceColor(synopsis.confidence)}`}>
          Confidence {synopsis.confidence}/10
        </span>
        {synopsis.confidence < 4 && (
          <span className="text-[10.5px] text-amber bg-amber-bg border border-amber/20 px-[8px] py-[2px] rounded-full">
            Low confidence — verify against original document
          </span>
        )}
      </div>

      {/* Main card */}
      <div className="bg-white border border-border-1 rounded-DEFAULT px-[18px] py-[4px]">

        {/* Parties */}
        <Section label="Parties">
          <PartyRow label="Petitioner" value={synopsis.petitioner} />
          <PartyRow label="Respondent" value={synopsis.respondent} />
        </Section>

        {/* Facts */}
        {facts.length > 0 && (
          <Section label="Facts">
            <BulletList items={facts} />
          </Section>
        )}

        {/* Issues */}
        {synopsis.issues.length > 0 && (
          <Section label="Issues">
            <ul className="space-y-[5px]">
              {synopsis.issues.map((issue, i) => (
                <li key={i} className="flex items-start gap-[8px]">
                  <span className="text-[10px] font-bold text-text-3 mt-[3px] flex-shrink-0 w-[16px]">{i + 1}.</span>
                  <span>{issue}</span>
                </li>
              ))}
            </ul>
          </Section>
        )}

        {/* Held */}
        {held.length > 0 && (
          <Section label="Held">
            <BulletList items={held} />
          </Section>
        )}

        {/* Relief Granted / Sought — label depends on document type */}
        {relief.length > 0 && (
          <Section label={synopsis.held ? 'Relief Granted' : 'Relief Sought'}>
            <BulletList items={relief} />
          </Section>
        )}

        {/* Citations */}
        {synopsis.citations_used.length > 0 && (
          <Section label="Citations Used">
            <div className="flex flex-wrap gap-[6px]">
              {synopsis.citations_used.map((c, i) => (
                <span
                  key={i}
                  className="text-[10.5px] font-medium bg-green-bg text-green border border-green/20 px-[8px] py-[2px] rounded-[4px]"
                >
                  {c}
                </span>
              ))}
            </div>
          </Section>
        )}
      </div>

      {/* Footer actions */}
      <div className="mt-3 flex items-center gap-[10px]">
        <button
          onClick={() => {
            const text = [
              synopsis.case_name,
              synopsis.court && `Court: ${synopsis.court}`,
              synopsis.judgment_date && `Date: ${synopsis.judgment_date}`,
              synopsis.petitioner && `Petitioner: ${synopsis.petitioner}`,
              synopsis.respondent && `Respondent: ${synopsis.respondent}`,
              synopsis.facts && `\nFacts:\n${synopsis.facts}`,
              synopsis.issues.length && `\nIssues:\n${synopsis.issues.map((x, i) => `${i + 1}. ${x}`).join('\n')}`,
              synopsis.held && `\nHeld:\n${synopsis.held}`,
              synopsis.relief_granted && `\nRelief: ${synopsis.relief_granted}`,
              synopsis.citations_used.length && `\nCitations: ${synopsis.citations_used.join(', ')}`,
            ].filter(Boolean).join('\n')
            navigator.clipboard.writeText(text)
            toast('Synopsis copied to clipboard')
          }}
          className="text-[11.5px] font-semibold text-ink hover:underline"
        >
          Copy Synopsis
        </button>
        <span className="text-text-3 text-[10px]">·</span>
        <span className="text-[11px] text-text-3">
          {filename && `From: ${filename}`}
        </span>
      </div>
    </div>
  )
}
