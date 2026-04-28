import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { getMatterTypes, getProcedure, type ProcedureResult } from '@/api/legalProcess'
import Button from '@/components/ui/Button'
import { Input, Textarea } from '@/components/ui/FormField'
import { toast } from '@/store/toastStore'

const COURTS = [
  'P&H High Court, Chandigarh',
  'District Court, Ludhiana',
  'District Court, Amritsar',
  'District Court, Jalandhar',
  'District Court, Patiala',
  'District Court, Chandigarh',
  'District Court, Gurugram',
  'District Court, Faridabad',
]

export default function LegalProcessPage() {
  const [matterType, setMatterType] = useState('')
  const [court, setCourt] = useState(COURTS[0])
  const [facts, setFacts] = useState('')
  const [result, setResult] = useState<ProcedureResult | null>(null)

  const { data: matterTypes } = useQuery({
    queryKey: ['matter-types'],
    queryFn: () => getMatterTypes().then((r) => r.data.data),
  })

  const procedureMutation = useMutation({
    mutationFn: () => getProcedure(matterType, court, facts),
    onSuccess: ({ data }) => setResult(data.data),
    onError: () => toast('Could not fetch procedure. Try again.'),
  })

  return (
    <div className="max-w-[760px]">
      <div className="grid md:grid-cols-[320px_1fr] gap-5">
        {/* Form */}
        <div className="bg-white border border-border-1 rounded-DEFAULT p-4">
          <p className="font-serif text-[16px] text-text-1 mb-4">Legal Process Guide</p>

          <label className="block text-[10px] font-bold tracking-[0.5px] uppercase text-text-3 mb-1">Matter Type</label>
          <div className="flex flex-wrap gap-[5px] mb-[11px]">
            {(matterTypes ?? ['Civil Suit', 'Criminal', 'Consumer Case', 'Cheque Bounce', 'Property Dispute', 'Matrimonial']).map((t) => (
              <button
                key={t}
                onClick={() => setMatterType(t)}
                className={[
                  'text-[11px] font-semibold px-[10px] py-1 rounded-full border cursor-pointer transition-all',
                  matterType === t
                    ? 'bg-ink text-white border-ink'
                    : 'bg-surface-2 text-text-2 border-border-1 hover:bg-surface-3',
                ].join(' ')}
              >
                {t}
              </button>
            ))}
          </div>

          <label className="block text-[10px] font-bold tracking-[0.5px] uppercase text-text-3 mb-1">Court</label>
          <select
            className="w-full px-[10px] py-[7px] border border-border-1 rounded-sm bg-surface-2 text-text-1 font-sans text-[12.5px] outline-none mb-[11px] focus:border-border-2 focus:bg-white transition-all"
            value={court}
            onChange={(e) => setCourt(e.target.value)}
          >
            {COURTS.map((c) => <option key={c}>{c}</option>)}
          </select>

          <Textarea label="Brief Facts" value={facts} onChange={(e) => setFacts(e.target.value)} placeholder="Brief facts of the matter…" minRows={3} />

          <Button
            variant="primary"
            size="lg"
            onClick={() => procedureMutation.mutate()}
            disabled={!matterType || procedureMutation.isPending}
          >
            {procedureMutation.isPending ? 'Fetching…' : 'Get Procedure →'}
          </Button>
        </div>

        {/* Result */}
        <div>
          {!result && !procedureMutation.isPending && (
            <div className="flex flex-col items-center justify-center h-full text-text-3 gap-3 py-16">
              <span className="text-[30px]">📚</span>
              <p className="font-serif text-[15px] text-text-2">Step-by-step Punjab/Haryana court procedures</p>
              <p className="text-[12px] text-center">Select a matter type and court to see the exact filing procedure, documents required, court fees, and limitation period.</p>
            </div>
          )}

          {procedureMutation.isPending && (
            <div className="text-[12px] text-text-3 italic text-center py-12">Fetching procedure…</div>
          )}

          {result && (
            <div className="space-y-4">
              {result.verify_at_registry && (
                <div className="bg-amber-bg border border-amber/20 rounded-sm px-4 py-3 text-[12px] text-amber">
                  ⚠ Please verify current fees and procedures at the court registry before filing.
                </div>
              )}

              <Section label="Steps">
                <ol className="space-y-3">
                  {result.steps.map((s) => (
                    <li key={s.step_number} className="flex gap-3">
                      <span className="text-[11px] font-bold text-text-3 w-5 flex-shrink-0">{s.step_number}.</span>
                      <div>
                        <div className="text-[12.5px] font-semibold text-text-1">{s.action}</div>
                        <div className="text-[11.5px] text-text-2 mt-[2px]">{s.details}</div>
                        {s.source && <div className="text-[10px] text-text-3 mt-[2px]">Source: {s.source}</div>}
                      </div>
                    </li>
                  ))}
                </ol>
              </Section>

              <div className="grid grid-cols-2 gap-3">
                <InfoCard label="Documents Required">
                  <ul className="list-disc pl-4 space-y-1">
                    {result.documents_required.map((d, i) => <li key={i} className="text-[12px]">{d}</li>)}
                  </ul>
                </InfoCard>
                <div className="space-y-3">
                  <InfoCard label="Court Fees">{result.court_fees}</InfoCard>
                  <InfoCard label="Limitation Period">
                    <div>{result.limitation_period}</div>
                    <div className="text-[11px] text-text-3 mt-1">{result.limitation_calculation}</div>
                  </InfoCard>
                  <InfoCard label="Typical Timeline">{result.typical_timeline}</InfoCard>
                </div>
              </div>

              <div className="text-[11px] text-text-3">
                Confidence: <strong className={result.confidence >= 7 ? 'text-green' : result.confidence >= 4 ? 'text-amber' : 'text-red'}>{result.confidence}/10</strong>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="bg-white border border-border-1 rounded-DEFAULT p-4">
      <div className="text-[10px] font-bold tracking-[0.7px] uppercase text-text-3 mb-3">{label}</div>
      <div className="text-[12.5px] text-text-2 leading-[1.6]">{children}</div>
    </div>
  )
}

function InfoCard({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="bg-white border border-border-1 rounded-DEFAULT p-4">
      <div className="text-[10px] font-bold tracking-[0.7px] uppercase text-text-3 mb-2">{label}</div>
      <div className="text-[12.5px] text-text-2 leading-[1.6]">{children}</div>
    </div>
  )
}
