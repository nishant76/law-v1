import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { uploadDocument } from '@/api/documents'
import { generateSynopsis, exportSynopsis, type Synopsis } from '@/api/synopsis'
import DropZone from '@/components/ui/DropZone'
import Button from '@/components/ui/Button'
import { toast } from '@/store/toastStore'
import { downloadBlob } from '@/lib/utils'

export default function SynopsisPage() {
  const [synopsis, setSynopsis] = useState<Synopsis | null>(null)

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadDocument(file),
    onSuccess: ({ data }) => {
      toast('Document uploaded — generating synopsis…')
      synopsisMutation.mutate(data.data.id)
    },
    onError: () => toast('Upload failed.'),
  })

  const synopsisMutation = useMutation({
    mutationFn: (id: string) => generateSynopsis(id),
    onSuccess: ({ data }) => { setSynopsis(data.data); toast('Synopsis generated') },
    onError: () => toast('Synopsis generation failed.'),
  })

  const exportMutation = useMutation({
    mutationFn: (id: string) => exportSynopsis(id),
    onSuccess: (res) => downloadBlob(res.data as Blob, 'synopsis.docx'),
  })

  if (!synopsis) {
    return (
      <div className="max-w-[480px] mx-auto mt-9">
        <p className="font-serif text-[18px] text-text-1 mb-[6px] text-center">Case Synopsis Generator</p>
        <p className="text-[12px] text-text-3 mb-6 text-center">Upload any judgment or petition to generate a structured one-pager.</p>
        <DropZone onFile={(f) => uploadMutation.mutate(f)} />
        {(uploadMutation.isPending || synopsisMutation.isPending) && (
          <div className="text-[11px] text-text-3 italic text-center mt-3">
            {uploadMutation.isPending ? 'Uploading…' : 'Generating synopsis…'}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="max-w-[760px]">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h2 className="font-serif text-[18px] text-text-1">{synopsis.case_name}</h2>
          <p className="text-[11px] text-text-3">{synopsis.court}{synopsis.judgment_date ? ` · ${synopsis.judgment_date}` : ''}</p>
        </div>
        <div className="flex gap-2">
          <Button size="sm" onClick={() => setSynopsis(null)}>← New</Button>
          <Button size="sm" variant="primary" onClick={() => exportMutation.mutate(synopsis.id)}>↓ .docx</Button>
        </div>
      </div>
      <div className="bg-white border border-border-1 rounded-DEFAULT p-5 space-y-4">
        <Section label="Parties">
          <p><strong>Petitioner:</strong> {synopsis.petitioner}</p>
          <p><strong>Respondent:</strong> {synopsis.respondent}</p>
        </Section>
        <Section label="Facts">{synopsis.facts}</Section>
        <Section label="Issues">
          <ul className="list-disc pl-4 space-y-1">
            {synopsis.issues.map((iss, i) => <li key={i} className="text-[12.5px]">{iss}</li>)}
          </ul>
        </Section>
        <Section label="Held">{synopsis.held}</Section>
        {synopsis.citations_used.length > 0 && (
          <Section label="Citations Used">
            <div className="flex flex-wrap gap-[6px]">
              {synopsis.citations_used.map((c, i) => (
                <span key={i} className="text-[10px] font-bold bg-green-bg text-green border border-green/20 px-[6px] py-[1px] rounded-[4px]">{c}</span>
              ))}
            </div>
          </Section>
        )}
        <div className="text-[11px] text-text-3 pt-2 border-t border-border-1">
          Confidence: <strong className={synopsis.confidence >= 7 ? 'text-green' : synopsis.confidence >= 4 ? 'text-amber' : 'text-red'}>{synopsis.confidence}/10</strong>
        </div>
      </div>
    </div>
  )
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-[10px] font-bold tracking-[0.7px] uppercase text-text-3 mb-[6px]">{label}</div>
      <div className="text-[12.5px] text-text-2 leading-[1.6]">{children}</div>
    </div>
  )
}
