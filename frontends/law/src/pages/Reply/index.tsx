import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import {
  uploadAndExtractAllegations,
  generateReply,
  exportReplyDocx,
  rewriteGrounds,
  type NoticeExtraction,
  type Allegation,
  type AllegationResponse,
} from '@/api/reply'
import DropZone from '@/components/ui/DropZone'
import Button from '@/components/ui/Button'
import MarkdownText from '@/components/ui/MarkdownText'
import { toast } from '@/store/toastStore'
import { downloadBlob } from '@/lib/utils'

// ── Types ─────────────────────────────────────────────────────────────────────

type Stance = 'admit' | 'deny' | 'partial'
type Stage = 'upload' | 'stances' | 'reply'

const STANCE_LABEL: Record<Stance, string> = {
  admit: 'Admit',
  deny: 'Deny',
  partial: 'Partial',
}

const STANCE_CLS: Record<Stance, string> = {
  admit: 'bg-green-bg text-green border-green/30',
  deny: 'bg-red-bg text-red-600 border-red-200',
  partial: 'bg-amber-bg text-amber border-amber/30',
}

// ── Allegation card (per-point stance + facts) ──────────────────────────────────

function AllegationCard({
  a,
  stance,
  grounds,
  onStance,
  onGrounds,
}: {
  a: Allegation
  stance: Stance
  grounds: string
  onStance: (s: Stance) => void
  onGrounds: (text: string) => void
}) {
  const [rewriting, setRewriting] = useState(false)

  // Plain async/await (NOT useMutation) per CLAUDE.md GAP-050 — this is a
  // user-triggered call that must not be cancelled in React 18 Strict Mode.
  const handleRewrite = async () => {
    const facts = grounds.trim()
    if (!facts || rewriting) return
    setRewriting(true)
    try {
      const res = await rewriteGrounds(a.allegation, stance, facts)
      const rewritten = res.data?.data?.rewritten_grounds
      if (rewritten) {
        onGrounds(rewritten)
        toast('Rewritten in legal language')
      } else {
        toast(res.data?.error?.message ?? 'Could not rewrite the notes.')
      }
    } catch {
      toast('Rewrite failed. Please try again.')
    } finally {
      setRewriting(false)
    }
  }

  return (
    <div className="bg-white border border-border-1 rounded-DEFAULT px-[15px] py-[12px]">
      <div className="flex items-start gap-[10px]">
        <span className="text-[11px] font-bold text-text-3 flex-shrink-0 mt-[2px] w-[18px]">
          {a.point_number}.
        </span>
        <div className="flex-1 min-w-0">
          <p className="text-[12.5px] text-text-1 leading-[1.55] mb-[9px]">{a.allegation}</p>
          {a.legal_basis_claimed && (
            <p className="text-[11px] text-text-3 mb-[9px]">
              Claimed basis: <span className="text-text-2">{a.legal_basis_claimed}</span>
            </p>
          )}

          {/* Stance buttons */}
          <div className="flex gap-[6px] mb-[11px]">
            {(['admit', 'deny', 'partial'] as Stance[]).map((s) => (
              <button
                key={s}
                onClick={() => onStance(s)}
                className={[
                  'text-[11px] font-semibold px-[11px] py-[4px] rounded-full border transition-all',
                  stance === s
                    ? STANCE_CLS[s]
                    : 'bg-surface-2 text-text-2 border-border-1 hover:bg-surface-3',
                ].join(' ')}
              >
                {STANCE_LABEL[s]}
              </button>
            ))}
          </div>

          {/* Facts / grounds textbox */}
          <label className="block text-[10px] font-bold tracking-[0.5px] uppercase text-text-3 mb-[5px]">
            Your facts / grounds
          </label>
          <textarea
            value={grounds}
            onChange={(e) => onGrounds(e.target.value)}
            rows={3}
            placeholder="Note your version of the facts in plain language. The tool will rewrite it into formal legal language."
            className="w-full text-[12px] text-text-1 leading-[1.55] bg-surface-2 border border-border-2 rounded-sm px-[10px] py-[8px] resize-y focus:outline-none focus:border-ink placeholder:text-text-3"
          />

          <div className="flex flex-wrap items-center gap-[6px] mt-[8px]">
            <button
              onClick={handleRewrite}
              disabled={rewriting || !grounds.trim()}
              className="text-[11px] font-semibold px-[10px] py-[4px] rounded-full border border-border-1 bg-surface-2 text-text-2 hover:bg-surface-3 disabled:opacity-40 transition-all"
            >
              {rewriting ? 'Rewriting…' : '✎ Rewrite in legal language'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ReplyPage() {
  const [stage, setStage] = useState<Stage>('upload')
  const [filename, setFilename] = useState('')
  const [extraction, setExtraction] = useState<NoticeExtraction | null>(null)
  const [stances, setStances] = useState<Record<number, Stance>>({})
  const [grounds, setGrounds] = useState<Record<number, string>>({})
  const [replyText, setReplyText] = useState('')
  const [draftId, setDraftId] = useState('')

  // ── Step 1: upload + extract ───────────────────────────────────────────────

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadAndExtractAllegations(file),
    onSuccess: (res) => {
      const data = res.data?.data
      if (!data || !data.allegations?.length) {
        toast('Could not extract allegations from this document.')
        return
      }
      // Default all to 'deny'
      const defaultStances: Record<number, Stance> = {}
      data.allegations.forEach(a => { defaultStances[a.point_number] = 'deny' })
      setStances(defaultStances)
      setGrounds({})
      setExtraction(data)
      setStage('stances')
    },
    onError: () => toast('Upload failed. Please try again.'),
  })

  // ── Step 2: generate reply ─────────────────────────────────────────────────

  const generateMutation = useMutation({
    mutationFn: () => {
      const responses: AllegationResponse[] = extraction!.allegations.map(a => ({
        point_number: a.point_number,
        allegation: a.allegation,
        stance: stances[a.point_number] ?? 'deny',
        grounds: grounds[a.point_number] ?? '',
        legal_basis_claimed: a.legal_basis_claimed ?? null,
      }))
      return generateReply(extraction!.document_id, responses)
    },
    onSuccess: (res) => {
      const data = res.data?.data
      if (!data?.reply_text) { toast('Reply generation failed.'); return }
      setReplyText(data.reply_text)
      setDraftId(data.draft_id)
      setStage('reply')
    },
    onError: () => toast('Reply generation failed. Please try again.'),
  })

  // ── Step 3: export ─────────────────────────────────────────────────────────

  const exportMutation = useMutation({
    mutationFn: () => exportReplyDocx(draftId),
    onSuccess: (res) => downloadBlob(res.data as Blob, 'reply_notice.docx'),
    onError: () => toast('Export failed.'),
  })

  const reset = () => {
    setStage('upload'); setFilename(''); setExtraction(null)
    setStances({}); setGrounds({}); setReplyText(''); setDraftId('')
  }

  // ── Stage: upload ──────────────────────────────────────────────────────────

  if (stage === 'upload') {
    return (
      <div className="max-w-[500px] mx-auto mt-9">
        <p className="font-serif text-[20px] tracking-[-0.2px] text-text-1 mb-[5px] text-center">
          Smart Reply Generator
        </p>
        <p className="text-[12px] text-text-3 mb-6 text-center">
          Upload a legal notice. We'll extract each allegation so you can set your stance before generating a formal reply.
        </p>
        <DropZone onFile={(f) => { setFilename(f.name); uploadMutation.mutate(f) }} />
        {uploadMutation.isPending && (
          <div className="mt-4 text-center">
            <div className="text-[11px] text-text-3 italic mb-[6px]">
              {filename ? `Extracting allegations from ${filename}…` : 'Extracting allegations…'}
            </div>
            <div className="h-[2px] bg-surface-3 rounded-full overflow-hidden mx-8">
              <div className="h-full bg-ink rounded-full animate-pulse" style={{ width: '55%' }} />
            </div>
          </div>
        )}
        {uploadMutation.isError && (
          <div className="mt-3 text-center text-[11.5px] text-red-500">
            Extraction failed. Please check the file and try again.
          </div>
        )}
      </div>
    )
  }

  // ── Stage: stances ─────────────────────────────────────────────────────────

  if (stage === 'stances' && extraction) {
    return (
      <div className="max-w-[760px]">
        {/* Header */}
        <div className="flex items-start justify-between gap-3 mb-5">
          <div className="flex-1 min-w-0">
            <h1 className="font-serif text-[20px] tracking-[-0.2px] text-text-1 mb-[3px]">
              Set Your Stance
            </h1>
            <div className="flex items-center gap-[8px] text-[12px] text-text-3 flex-wrap">
              {extraction.sender && <span>From: {extraction.sender}</span>}
              {extraction.notice_date && (
                <>
                  {extraction.sender && <span>·</span>}
                  <span>Dated: {extraction.notice_date}</span>
                </>
              )}
              <span>·</span>
              <span className="capitalize">{extraction.notice_type.replace(/_/g, ' ')}</span>
              <span>·</span>
              <span>{extraction.allegations.length} allegation{extraction.allegations.length !== 1 ? 's' : ''}</span>
            </div>
          </div>
          <button onClick={reset} className="text-[12px] text-text-3 hover:text-text-1 transition-colors mt-[3px] flex-shrink-0">
            ← New
          </button>
        </div>

        {/* Info banner */}
        <div className="bg-surface-2 border border-border-1 rounded-DEFAULT px-[13px] py-[9px] mb-4 text-[11.5px] text-text-3">
          For each allegation, choose <strong className="text-text-2">Admit</strong>, <strong className="text-text-2">Deny</strong>, or <strong className="text-text-2">Partial</strong>, and note your facts — we'll rewrite them into formal legal language.
        </div>

        {/* Allegations */}
        <div className="space-y-[8px] mb-5">
          {extraction.allegations.map((a) => (
            <AllegationCard
              key={a.point_number}
              a={a}
              stance={stances[a.point_number] ?? 'deny'}
              grounds={grounds[a.point_number] ?? ''}
              onStance={(s) => setStances(prev => ({ ...prev, [a.point_number]: s }))}
              onGrounds={(text) => setGrounds(prev => ({ ...prev, [a.point_number]: text }))}
            />
          ))}
        </div>

        {/* Generate button */}
        <div className="flex items-center gap-[12px]">
          <Button
            variant="primary"
            onClick={() => generateMutation.mutate()}
            disabled={generateMutation.isPending}
          >
            {generateMutation.isPending ? 'Generating Reply…' : 'Generate Reply →'}
          </Button>
          {generateMutation.isPending && (
            <span className="text-[11px] text-text-3 italic">This may take 20–30 seconds…</span>
          )}
        </div>
        {generateMutation.isError && (
          <p className="mt-2 text-[11.5px] text-red-500">Generation failed. Please try again.</p>
        )}
      </div>
    )
  }

  // ── Stage: reply ───────────────────────────────────────────────────────────

  return (
    <div className="max-w-[760px]">
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-5">
        <div>
          <h1 className="font-serif text-[20px] tracking-[-0.2px] text-text-1 mb-[3px]">
            Reply to Legal Notice
          </h1>
          <p className="text-[12px] text-text-3">
            Review, copy, or download the generated reply.
          </p>
        </div>
        <div className="flex gap-[8px] flex-shrink-0">
          <Button size="sm" onClick={reset}>← New</Button>
          {draftId && (
            <Button
              size="sm"
              variant="primary"
              onClick={() => exportMutation.mutate()}
              disabled={exportMutation.isPending}
            >
              {exportMutation.isPending ? 'Exporting…' : '↓ .docx'}
            </Button>
          )}
        </div>
      </div>

      {/* Copy button */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-[11px] text-text-3">Generated reply — review before sending</span>
        <button
          onClick={() => { navigator.clipboard.writeText(replyText); toast('Copied to clipboard') }}
          className="text-[11.5px] font-semibold text-ink hover:underline"
        >
          Copy
        </button>
      </div>

      {/* Reply text */}
      <div className="bg-white border border-border-1 rounded-DEFAULT px-[20px] py-[18px]">
        <MarkdownText text={replyText} />
      </div>

      {/* Footer note */}
      <p className="mt-3 text-[11px] text-text-3">
        ⚠️ Review the reply carefully before sending. Verify all legal provisions and facts against the original notice.
      </p>
    </div>
  )
}
