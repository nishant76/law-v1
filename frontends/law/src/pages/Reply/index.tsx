import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { uploadDocument } from '@/api/documents'
import { extractAllegations, getLegalGrounds, generateReply, type Allegation, type NoticeExtraction } from '@/api/reply'
import DropZone from '@/components/ui/DropZone'
import Button from '@/components/ui/Button'
import { toast } from '@/store/toastStore'

type Stance = 'admit' | 'deny' | 'partial'

const STANCE_LABELS: Record<Stance, string> = { admit: 'Admit', deny: 'Deny', partial: 'Partial' }
const STANCE_CLS: Record<Stance, string> = {
  admit: 'bg-green-bg text-green border-green/20',
  deny: 'bg-red-bg text-red border-red/20',
  partial: 'bg-amber-bg text-amber border-amber/20',
}

export default function ReplyPage() {
  const [documentId, setDocumentId] = useState<string | null>(null)
  const [extraction, setExtraction] = useState<NoticeExtraction | null>(null)
  const [stances, setStances] = useState<Record<number, Stance>>({})

  const uploadMutation = useMutation({
    mutationFn: (f: File) => uploadDocument(f),
    onSuccess: ({ data }) => {
      toast('Document uploaded — extracting allegations…')
      extractMutation.mutate(data.data.id)
      setDocumentId(data.data.id)
    },
    onError: () => toast('Upload failed.'),
  })

  const extractMutation = useMutation({
    mutationFn: (id: string) => extractAllegations(id),
    onSuccess: ({ data }) => { setExtraction(data.data); toast('Allegations extracted') },
    onError: () => toast('Extraction failed.'),
  })

  const replyMutation = useMutation({
    mutationFn: () => {
      const allegations: Allegation[] = extraction!.allegations.map((a) => ({
        ...a, stance: stances[a.point_number] ?? 'deny',
      }))
      return generateReply(documentId!, allegations)
    },
    onSuccess: () => toast('Reply draft generated — go to Draft page to view'),
    onError: () => toast('Reply generation failed.'),
  })

  if (!extraction) {
    return (
      <div className="max-w-[480px] mx-auto mt-9">
        <p className="font-serif text-[18px] text-text-1 mb-[6px] text-center">Smart Reply Generator</p>
        <p className="text-[12px] text-text-3 mb-6 text-center">Upload a legal notice. We'll extract each allegation and suggest legal grounds to deny them.</p>
        <DropZone onFile={(f) => uploadMutation.mutate(f)} />
        {(uploadMutation.isPending || extractMutation.isPending) && (
          <div className="text-[11px] text-text-3 italic text-center mt-3">
            {uploadMutation.isPending ? 'Uploading…' : 'Extracting allegations…'}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="max-w-[860px]">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h2 className="font-serif text-[18px] text-text-1">Reply to Legal Notice</h2>
          <p className="text-[11px] text-text-3">
            {extraction.sender && `From: ${extraction.sender}`}
            {extraction.notice_date && ` · ${extraction.notice_date}`}
            {` · ${extraction.notice_type}`}
          </p>
        </div>
        <div className="flex gap-2">
          <Button size="sm" onClick={() => { setExtraction(null); setDocumentId(null) }}>← New</Button>
          <Button size="sm" variant="primary" onClick={() => replyMutation.mutate()} disabled={replyMutation.isPending}>
            Generate Reply
          </Button>
        </div>
      </div>

      <div className="space-y-3">
        {extraction.allegations.map((a) => {
          const stance = stances[a.point_number]
          return (
            <div key={a.point_number} className="bg-white border border-border-1 rounded-DEFAULT p-4">
              <div className="flex items-start gap-3">
                <span className="text-[10px] font-bold text-text-3 w-5 flex-shrink-0 pt-[2px]">{a.point_number}.</span>
                <div className="flex-1">
                  <p className="text-[12.5px] text-text-1 mb-2">{a.allegation}</p>
                  {a.legal_basis_claimed && (
                    <p className="text-[11px] text-text-3 mb-2">Claimed basis: {a.legal_basis_claimed}</p>
                  )}
                  <div className="flex gap-[5px]">
                    {(['admit', 'deny', 'partial'] as Stance[]).map((s) => (
                      <button
                        key={s}
                        onClick={() => setStances((prev) => ({ ...prev, [a.point_number]: s }))}
                        className={[
                          'text-[11px] font-semibold px-[10px] py-1 rounded-full border cursor-pointer transition-all',
                          stance === s ? STANCE_CLS[s] : 'bg-surface-2 text-text-2 border-border-1 hover:bg-surface-3',
                        ].join(' ')}
                      >
                        {STANCE_LABELS[s]}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
