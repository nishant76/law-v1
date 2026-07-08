import { useState, useRef } from 'react'
import { useMutation } from '@tanstack/react-query'
import { extractFromUpload } from '@/api/extract'
import { getCnrCase } from '@/api/ecourts'
import type { EcourtsCase } from '@/api/ecourts'
import { useCaseStore } from '@/store/caseStore'
import { toast } from '@/store/toastStore'
import { Input, Textarea, FieldLabel } from '@/components/ui/FormField'
import Button from '@/components/ui/Button'
import type {
  LegalCase,
  MatterType,
  CaseStatus,
  CasePerson,
  CaseHearing,
  CasePayment,
  UniversalExtraction,
} from '@/types'

// ── Constants ─────────────────────────────────────────────────────────────────

const MATTER_TYPES: { value: MatterType; label: string }[] = [
  { value: 'bail', label: 'Bail Application' },
  { value: 'writ', label: 'Writ Petition' },
  { value: 'civil', label: 'Civil Suit' },
  { value: 'criminal', label: 'Criminal Matter' },
  { value: 'cheque_bounce', label: 'Cheque Bounce (S.138)' },
  { value: 'matrimonial', label: 'Matrimonial' },
  { value: 'consumer', label: 'Consumer Case' },
  { value: 'property', label: 'Property Dispute' },
  { value: 'other', label: 'Other' },
]

const STATUS_OPTIONS: { value: CaseStatus; label: string }[] = [
  { value: 'active', label: 'Active' },
  { value: 'stayed', label: 'Stayed' },
  { value: 'settled', label: 'Settled' },
  { value: 'disposed', label: 'Disposed' },
]

// ── Types ─────────────────────────────────────────────────────────────────────

interface PaymentRow {
  id: string
  label: string
  amount: string
  due_date: string
  paid: boolean
}

interface FormState {
  // Step 1 — Core
  title: string
  case_number: string
  cnr_number: string
  court: string
  matter_type: MatterType
  status: CaseStatus
  filing_date: string
  notes: string
  // Step 2 — People & Hearing
  client_name: string
  client_phone: string
  opponent_name: string
  opponent_counsel: string
  judge_name: string
  next_hearing: string
  // Step 3 — Payments
  total_fees: string
  payments: PaymentRow[]
}

const EMPTY_FORM: FormState = {
  title: '', case_number: '', cnr_number: '', court: '', matter_type: 'civil',
  status: 'active', filing_date: '', notes: '',
  client_name: '', client_phone: '', opponent_name: '',
  opponent_counsel: '', judge_name: '', next_hearing: '',
  total_fees: '', payments: [],
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function uid() { return `${Date.now()}-${Math.random().toString(36).slice(2, 7)}` }

function selectCls(extra = '') {
  return `w-full px-[10px] py-[7px] border border-border-1 rounded-sm bg-surface-2 text-text-1 font-sans text-[12.5px] outline-none transition-all mb-[11px] focus:border-border-2 focus:bg-white ${extra}`
}

function StepDot({ step, current }: { step: number; current: number }) {
  const done = step < current
  const active = step === current
  return (
    <div className="flex items-center gap-[6px]">
      <div className={[
        'w-[22px] h-[22px] rounded-full flex items-center justify-center text-[10px] font-bold transition-colors',
        done ? 'bg-ink text-white' : active ? 'bg-ink text-white' : 'bg-surface-3 text-text-3',
      ].join(' ')}>
        {done ? '✓' : step}
      </div>
      <span className={`text-[11px] font-medium ${active ? 'text-text-1' : 'text-text-3'}`}>
        {step === 1 ? 'Case Details' : step === 2 ? 'People & Dates' : 'Fees'}
      </span>
    </div>
  )
}

// ── Auto-fill helpers ─────────────────────────────────────────────────────────

// Safely coerce any field value to a plain string
function fieldStr(v: unknown): string {
  if (v == null) return ''
  if (typeof v === 'string') return v.trim()
  if (typeof v === 'number') return String(v)
  if (Array.isArray(v)) return v.filter(Boolean).join(', ')
  if (typeof v === 'object') {
    // Try common sub-keys
    const obj = v as Record<string, unknown>
    for (const k of ['name', 'value', 'text', 'label']) {
      if (obj[k] && typeof obj[k] === 'string') return (obj[k] as string).trim()
    }
    return Object.values(obj).filter(x => typeof x === 'string').join(', ')
  }
  return ''
}

// Try a list of field name aliases; return first non-empty value
function pick(fields: Record<string, { value: unknown } | undefined>, ...keys: string[]): string {
  for (const k of keys) {
    const val = fieldStr(fields[k]?.value)
    if (val) return val
  }
  return ''
}

// Detect problems with the uploaded document for case registration
interface DocWarning {
  level: 'error' | 'warn'
  message: string
  detail: string
}

function detectDocumentIssue(ext: UniversalExtraction): DocWarning | null {
  const category = ext.document_type?.category
  const subType = (ext.document_type?.sub_type || '').toLowerCase()
  const summary = (ext.summary?.value || '').toLowerCase()
  const hasActions = (ext.action_items ?? []).length > 0
  const hasFutureDeadlines = (ext.critical_deadlines ?? []).some(
    d => d.date && d.date > new Date().toISOString().slice(0, 10)
  )

  // Non-legal document
  if (category && category !== 'Legal') {
    return {
      level: 'error',
      message: `This looks like a ${category} document, not a court order`,
      detail: `Document detected as: ${ext.document_type?.sub_type || category}. For case registration, upload a court order, petition, or FIR.`,
    }
  }

  // Final disposed judgment — no pending steps
  const disposalKeywords = ['dismissed', 'disposed', 'disposed of', 'allowed and disposed', 'writ dismissed', 'petition dismissed', 'appeal dismissed']
  const isDisposed = disposalKeywords.some(w => summary.includes(w))
  const isFinalJudgment = subType.includes('judgment') || subType.includes('final order')

  if ((isDisposed || isFinalJudgment) && !hasActions && !hasFutureDeadlines) {
    return {
      level: 'warn',
      message: 'This appears to be a final/disposed judgment',
      detail: 'No pending action items or future dates found. You can still register it as a case — just verify the status.',
    }
  }

  return null
}

function mapExtractionToForm(ext: UniversalExtraction, prev: FormState): Partial<FormState> {
  const f = ext.identity_fields ?? {} as Record<string, { value: unknown } | undefined>

  // Try multiple field name aliases — LLM is not always consistent
  const petitioner = pick(f,
    'petitioner', 'appellant', 'applicant', 'complainant', 'plaintiff',
    'petitioner_name', 'accused', 'writ_petitioner'
  )
  const respondent = pick(f,
    'respondent', 'respondents', 'opposite_party', 'defendant',
    'accused', 'state', 'opponent', 'non_applicant'
  )
  const court = pick(f, 'court', 'court_name', 'forum', 'tribunal', 'high_court')
  const caseNumber = pick(f,
    'case_number', 'cnr_number', 'case_no', 'writ_number', 'fir_number',
    'petition_number', 'appeal_number', 'suit_number', 'case_id', 'number'
  )
  const judge = pick(f, 'judge_name', 'bench', 'judge', 'coram', 'presiding_officer', 'justice')
  const caseName = pick(f, 'case_name', 'title', 'matter_title')

  const autoTitle = petitioner && respondent
    ? `${petitioner} v. ${respondent}`
    : caseName || prev.title

  // Best-effort next hearing from future deadlines
  const today = new Date().toISOString().slice(0, 10)
  const futureDates = (ext.critical_deadlines ?? [])
    .filter(d => d.date && d.date > today)
    .sort((a, b) => a.date.localeCompare(b.date))
  const nextHearing = futureDates[0]?.date || prev.next_hearing

  return {
    title: autoTitle || prev.title,
    case_number: caseNumber || prev.case_number,
    court: court || prev.court,
    judge_name: judge || prev.judge_name,
    client_name: petitioner || prev.client_name,
    opponent_name: respondent || prev.opponent_name,
    next_hearing: nextHearing,
  }
}

// ── Main Modal ────────────────────────────────────────────────────────────────

interface Props {
  open: boolean
  onClose: () => void
  onCreated: (id: string) => void
}

type CnrState = 'idle' | 'loading' | 'found' | 'not_found' | 'error'

export default function NewCaseModal({ open, onClose, onCreated }: Props) {
  const [step, setStep] = useState(1)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [autoFilling, setAutoFilling] = useState(false)
  const [autoFilled, setAutoFilled] = useState(false)
  const [docWarning, setDocWarning] = useState<DocWarning | null>(null)
  const [detectedType, setDetectedType] = useState<string | null>(null)
  const [cnrState, setCnrState] = useState<CnrState>('idle')
  const fileRef = useRef<HTMLInputElement>(null)
  const addCase = useCaseStore((s) => s.addCase)

  const extractMutation = useMutation({
    mutationFn: (file: File) => extractFromUpload(file),
    onSuccess: ({ data }) => {
      setAutoFilling(false)
      if (!data.success || !data.data) {
        toast('Could not read document — try a clearer scan')
        return
      }
      const ext = data.data as UniversalExtraction
      const warning = detectDocumentIssue(ext)
      const mapped = mapExtractionToForm(ext, form)

      setDocWarning(warning)
      setDetectedType(ext.document_type?.sub_type || ext.document_type?.category || null)
      setForm((f) => ({ ...f, ...mapped }))
      setAutoFilled(true)

      if (warning?.level === 'error') {
        // Don't toast success for clearly wrong documents
      } else {
        const filled = [mapped.title, mapped.case_number, mapped.court].filter(Boolean).length
        toast(filled > 0 ? `${filled} field${filled > 1 ? 's' : ''} auto-filled` : 'Document read — fill in the details below')
      }
    },
    onError: () => { setAutoFilling(false); toast('Could not read document') },
  })

  if (!open) return null

  const set = (k: keyof FormState, v: unknown) =>
    setForm((f) => ({ ...f, [k]: v }))

  const handleCnrBlur = async () => {
    const cnr = form.cnr_number.trim().toUpperCase()
    if (!cnr || cnr.length < 10) return
    setCnrState('loading')
    try {
      const res = await getCnrCase(cnr)
      const c: EcourtsCase = res.data.case
      if (!c) { setCnrState('not_found'); return }

      const petitioner = c.petitioner || ''
      const respondent = c.respondent || ''
      setForm((f) => ({
        ...f,
        title: f.title || (petitioner && respondent ? `${petitioner} v. ${respondent}` : f.title),
        court: f.court || c.court || '',
        case_number: f.case_number || c.case_number || '',
        client_name: f.client_name || petitioner,
        opponent_name: f.opponent_name || respondent,
        next_hearing: f.next_hearing || c.next_hearing_date || '',
      }))
      setCnrState('found')
    } catch {
      setCnrState('error')
    }
  }

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (file) startAutoFill(file)
  }

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) startAutoFill(file)
  }

  const startAutoFill = (file: File) => {
    if (file.size > 50 * 1024 * 1024) { toast('File too large — max 50MB'); return }
    setAutoFilling(true)
    extractMutation.mutate(file)
  }

  const canProceed1 = form.title.trim() && form.court.trim()
  const canProceed2 = form.client_name.trim()

  const resetModal = () => {
    setForm(EMPTY_FORM)
    setStep(1)
    setAutoFilled(false)
    setDocWarning(null)
    setDetectedType(null)
    setCnrState('idle')
  }

  const handleCreate = () => {
    const now = new Date().toISOString()
    const id = uid()

    const persons: CasePerson[] = []
    if (form.client_name) persons.push({ id: uid(), role: 'client', name: form.client_name, phone: form.client_phone || undefined })
    if (form.opponent_name) persons.push({ id: uid(), role: 'opponent', name: form.opponent_name })
    if (form.opponent_counsel) persons.push({ id: uid(), role: 'opp_counsel', name: form.opponent_counsel })
    if (form.judge_name) persons.push({ id: uid(), role: 'judge', name: form.judge_name })

    const hearings: CaseHearing[] = form.next_hearing
      ? [{ id: uid(), date: form.next_hearing, notes: 'Next hearing' }]
      : []

    const payments: CasePayment[] = form.payments
      .filter(p => parseFloat(p.amount) > 0)   // only require a valid amount > 0
      .map(p => ({
        id: p.id,
        label: p.label.trim() || 'Payment',    // default label if user left it blank
        amount: parseFloat(p.amount),
        due_date: p.due_date || undefined,
        paid: p.paid,
        paid_date: p.paid ? now.slice(0, 10) : undefined,
      }))

    const newCase: LegalCase = {
      id,
      case_number: form.case_number || undefined,
      title: form.title,
      court: form.court,
      matter_type: form.matter_type,
      status: form.status,
      filing_date: form.filing_date || undefined,
      next_hearing: form.next_hearing || undefined,
      total_fees: form.total_fees ? parseFloat(form.total_fees) : undefined,
      persons,
      hearings,
      payments,
      notes: form.notes || undefined,
      created_at: now,
      updated_at: now,
    }

    addCase(newCase)
    toast('Case registered')
    resetModal()
    onCreated(id)
  }

  const handleClose = () => {
    resetModal()
    onClose()
  }

  const addPaymentRow = () =>
    setForm((f) => ({
      ...f,
      payments: [...f.payments, { id: uid(), label: '', amount: '', due_date: '', paid: false }],
    }))

  const updatePayment = (idx: number, key: keyof PaymentRow, val: unknown) =>
    setForm((f) => ({
      ...f,
      payments: f.payments.map((p, i) => (i === idx ? { ...p, [key]: val } : p)),
    }))

  const removePayment = (idx: number) =>
    setForm((f) => ({ ...f, payments: f.payments.filter((_, i) => i !== idx) }))

  const totalPaid = form.payments
    .filter(p => p.paid && parseFloat(p.amount) > 0)
    .reduce((s, p) => s + parseFloat(p.amount), 0)

  const totalInstallments = form.payments
    .filter(p => parseFloat(p.amount) > 0)
    .reduce((s, p) => s + parseFloat(p.amount), 0)

  const totalDue = form.total_fees
    ? parseFloat(form.total_fees) - totalPaid
    : totalInstallments > 0
    ? totalInstallments - totalPaid
    : null

  return (
    <div
      className="fixed inset-0 bg-black/50 z-[500] flex items-center justify-center p-4"
      onClick={(e) => { if (e.target === e.currentTarget) handleClose() }}
    >
      <div className="bg-white rounded-DEFAULT w-full max-w-[560px] shadow-xl flex flex-col max-h-[88vh]">

        {/* Header */}
        <div className="flex items-center justify-between px-5 pt-5 pb-[14px] border-b border-border-1 flex-shrink-0">
          <div>
            <div className="text-[14px] font-bold text-text-1">Register New Case</div>
            <div className="text-[11px] text-text-3 mt-[1px]">Step {step} of 3</div>
          </div>
          <button onClick={handleClose} className="text-text-3 hover:text-text-1 text-[18px] leading-none transition-colors">×</button>
        </div>

        {/* Step indicator */}
        <div className="flex items-center gap-[6px] px-5 py-[12px] border-b border-border-1 flex-shrink-0">
          <StepDot step={1} current={step} />
          <div className="flex-1 h-[1px] bg-border-1" />
          <StepDot step={2} current={step} />
          <div className="flex-1 h-[1px] bg-border-1" />
          <StepDot step={3} current={step} />
        </div>

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto px-5 py-4">

          {/* ── Step 1 ── */}
          {step === 1 && (
            <div>
              {/* PDF Auto-fill */}
              <div className="mb-5">
                <div
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={handleFileDrop}
                  onClick={() => fileRef.current?.click()}
                  className={[
                    'border-[1.5px] border-dashed rounded-sm px-4 py-[14px] cursor-pointer transition-colors text-center',
                    autoFilled && !docWarning
                      ? 'border-green bg-green-bg'
                      : autoFilled && docWarning?.level === 'error'
                      ? 'border-red-300 bg-red-50'
                      : autoFilled && docWarning?.level === 'warn'
                      ? 'border-amber bg-amber-bg'
                      : 'border-border-2 bg-surface-2 hover:border-ink hover:bg-surface-3',
                  ].join(' ')}
                >
                  <input ref={fileRef} type="file" accept=".pdf,.jpg,.jpeg,.png" className="hidden" onChange={handleFileInput} />
                  {autoFilling ? (
                    <div className="flex items-center justify-center gap-2 text-[12px] text-text-2">
                      <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                      </svg>
                      Reading document…
                    </div>
                  ) : autoFilled && docWarning?.level === 'error' ? (
                    <div>
                      <div className="text-[12px] font-bold text-red-600 mb-[2px]">⚠ Wrong document type</div>
                      <div className="text-[11.5px] text-red-500">{docWarning.message}</div>
                    </div>
                  ) : autoFilled && docWarning?.level === 'warn' ? (
                    <div>
                      <div className="text-[12px] font-bold text-amber mb-[2px]">⚠ Check before continuing</div>
                      <div className="text-[11.5px] text-amber">{docWarning.message}</div>
                    </div>
                  ) : autoFilled ? (
                    <div className="flex items-center justify-center gap-[6px]">
                      <span className="text-[12px] text-green font-medium">✓ Fields filled from document</span>
                      {detectedType && (
                        <span className="text-[10px] bg-green-bg text-green font-semibold px-[6px] py-[1px] rounded-full border border-green">
                          {detectedType}
                        </span>
                      )}
                    </div>
                  ) : (
                    <>
                      <div className="text-[12px] font-medium text-text-2">📎 Upload court order or petition to auto-fill</div>
                      <div className="text-[11px] text-text-3 mt-[2px]">PDF, JPG, PNG · optional</div>
                    </>
                  )}
                </div>

                {/* Warning detail box */}
                {autoFilled && docWarning && (
                  <div className={[
                    'rounded-sm px-[12px] py-[9px] mt-[6px] text-[11.5px] leading-[1.5]',
                    docWarning.level === 'error'
                      ? 'bg-red-50 border border-red-200 text-red-600'
                      : 'bg-amber-bg border border-amber text-amber',
                  ].join(' ')}>
                    <span className="font-semibold">{docWarning.level === 'error' ? 'What to do: ' : 'Note: '}</span>
                    {docWarning.detail}
                    {autoFilled && (
                      <button
                        onClick={(e) => { e.stopPropagation(); fileRef.current?.click() }}
                        className="ml-[6px] underline font-semibold"
                      >
                        Upload different document
                      </button>
                    )}
                  </div>
                )}
              </div>

              <Input label="Case Title *" placeholder="e.g. Gurnam Singh v. State of Punjab" value={form.title} onChange={(e) => set('title', e.target.value)} />
              <div className="grid grid-cols-2 gap-[10px]">
                <Input label="Case Number" placeholder="CWP-12345-2025" value={form.case_number} onChange={(e) => set('case_number', e.target.value)} />
                <div>
                  <FieldLabel label="Matter Type" />
                  <select className={selectCls()} value={form.matter_type} onChange={(e) => set('matter_type', e.target.value as MatterType)}>
                    {MATTER_TYPES.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
                  </select>
                </div>
              </div>

              {/* CNR auto-fill */}
              <div className="mb-[11px]">
                <div className="flex items-center justify-between mb-[4px]">
                  <FieldLabel label="CNR Number" className="mb-0" />
                  {cnrState === 'found' && (
                    <span className="text-[10.5px] font-semibold text-green">✓ Filled from eCourts</span>
                  )}
                  {cnrState === 'not_found' && (
                    <span className="text-[10.5px] text-amber">Case not found on eCourts</span>
                  )}
                  {cnrState === 'error' && (
                    <span className="text-[10.5px] text-text-3">eCourts unavailable</span>
                  )}
                </div>
                <div className="relative">
                  <input
                    className={[
                      'w-full px-[10px] py-[7px] border rounded-sm bg-surface-2 text-text-1 font-sans text-[12.5px] outline-none transition-all',
                      'uppercase tracking-[0.5px] placeholder:normal-case placeholder:tracking-normal',
                      cnrState === 'found'
                        ? 'border-green bg-green-bg focus:border-green'
                        : 'border-border-1 focus:border-border-2 focus:bg-white',
                    ].join(' ')}
                    placeholder="e.g. PBLU010012342020"
                    maxLength={16}
                    value={form.cnr_number}
                    onChange={(e) => { set('cnr_number', e.target.value.toUpperCase()); setCnrState('idle') }}
                    onBlur={handleCnrBlur}
                  />
                  {cnrState === 'loading' && (
                    <div className="absolute right-[10px] top-1/2 -translate-y-1/2">
                      <svg className="animate-spin h-[14px] w-[14px] text-text-3" viewBox="0 0 24 24" fill="none">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                      </svg>
                    </div>
                  )}
                </div>
                <div className="text-[10.5px] text-text-3 mt-[3px]">
                  Paste CNR from your eCourts app — court, parties &amp; hearing date will fill automatically
                </div>
              </div>

              <Input label="Court *" placeholder="e.g. High Court of Punjab & Haryana, Chandigarh" value={form.court} onChange={(e) => set('court', e.target.value)} />
              <div className="grid grid-cols-2 gap-[10px]">
                <div>
                  <FieldLabel label="Status" />
                  <select className={selectCls()} value={form.status} onChange={(e) => set('status', e.target.value as CaseStatus)}>
                    {STATUS_OPTIONS.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
                  </select>
                </div>
                <Input label="Filing Date" type="date" value={form.filing_date} onChange={(e) => set('filing_date', e.target.value)} />
              </div>
              <Textarea label="Notes" placeholder="Key facts, client instructions, strategy notes…" minRows={3} value={form.notes} onChange={(e) => set('notes', e.target.value)} />
            </div>
          )}

          {/* ── Step 2 ── */}
          {step === 2 && (
            <div>
              <div className="text-[10px] font-bold tracking-[0.6px] uppercase text-text-3 mb-[12px]">Your Client</div>
              <div className="grid grid-cols-2 gap-[10px]">
                <Input label="Client Name *" placeholder="Full name" value={form.client_name} onChange={(e) => set('client_name', e.target.value)} />
                <Input label="Client Phone" placeholder="+91 98XXX XXXXX" type="tel" value={form.client_phone} onChange={(e) => set('client_phone', e.target.value)} />
              </div>

              <div className="text-[10px] font-bold tracking-[0.6px] uppercase text-text-3 mb-[12px] mt-[2px]">Opposite Party</div>
              <div className="grid grid-cols-2 gap-[10px]">
                <Input label="Opponent Name" placeholder="Party name" value={form.opponent_name} onChange={(e) => set('opponent_name', e.target.value)} />
                <Input label="Opponent's Counsel" placeholder="Advocate name" value={form.opponent_counsel} onChange={(e) => set('opponent_counsel', e.target.value)} />
              </div>

              <div className="text-[10px] font-bold tracking-[0.6px] uppercase text-text-3 mb-[12px] mt-[2px]">Court</div>
              <div className="grid grid-cols-2 gap-[10px]">
                <Input label="Judge / Bench" placeholder="Hon'ble Justice…" value={form.judge_name} onChange={(e) => set('judge_name', e.target.value)} />
                <Input label="Next Hearing Date" type="date" value={form.next_hearing} onChange={(e) => set('next_hearing', e.target.value)} />
              </div>
            </div>
          )}

          {/* ── Step 3 ── */}
          {step === 3 && (
            <div>
              <Input
                label="Total Agreed Fees (₹)"
                placeholder="75000"
                type="number"
                value={form.total_fees}
                onChange={(e) => set('total_fees', e.target.value)}
              />

              {/* Payment rows */}
              <div className="mb-[10px]">
                <div className="flex items-center justify-between mb-[8px]">
                  <FieldLabel label="Payment Installments" className="mb-0" />
                  <button
                    onClick={addPaymentRow}
                    className="text-[11px] font-semibold text-ink hover:underline"
                  >+ Add</button>
                </div>

                {form.payments.length === 0 && (
                  <div className="text-[11.5px] text-text-3 italic py-[6px]">No installments added. Click "+ Add" to add one.</div>
                )}

                {form.payments.map((p, i) => (
                  <div key={p.id} className="flex gap-[8px] items-start mb-[8px]">
                    <input
                      className="flex-[2] px-[8px] py-[6px] border border-border-1 rounded-sm bg-surface-2 text-[12px] outline-none focus:border-border-2 focus:bg-white"
                      placeholder='Label (optional)'
                      value={p.label}
                      onChange={(e) => updatePayment(i, 'label', e.target.value)}
                    />
                    <input
                      className="flex-[1.2] px-[8px] py-[6px] border border-border-1 rounded-sm bg-surface-2 text-[12px] outline-none focus:border-border-2 focus:bg-white"
                      placeholder="₹ Amount"
                      type="number"
                      value={p.amount}
                      onChange={(e) => updatePayment(i, 'amount', e.target.value)}
                    />
                    <input
                      className="flex-[1.5] px-[8px] py-[6px] border border-border-1 rounded-sm bg-surface-2 text-[12px] outline-none focus:border-border-2 focus:bg-white"
                      type="date"
                      value={p.due_date}
                      onChange={(e) => updatePayment(i, 'due_date', e.target.value)}
                    />
                    <label className="flex items-center gap-[4px] pt-[7px] cursor-pointer flex-shrink-0">
                      <input
                        type="checkbox"
                        checked={p.paid}
                        onChange={(e) => updatePayment(i, 'paid', e.target.checked)}
                        className="accent-ink"
                      />
                      <span className="text-[11px] text-text-3">Paid</span>
                    </label>
                    <button
                      onClick={() => removePayment(i)}
                      className="text-text-3 hover:text-red-500 pt-[7px] text-[15px] flex-shrink-0"
                    >×</button>
                  </div>
                ))}
              </div>

              {/* Live summary — updates as user fills in rows */}
              {(form.total_fees || totalInstallments > 0) && (
                <div className="bg-surface-2 border border-border-1 rounded-sm px-4 py-[10px] mt-2">
                  {form.total_fees && (
                    <div className="flex justify-between text-[12px] mb-[4px]">
                      <span className="text-text-3">Total agreed fees</span>
                      <span className="font-semibold text-text-1">
                        ₹{Number(form.total_fees).toLocaleString('en-IN')}
                      </span>
                    </div>
                  )}
                  {totalInstallments > 0 && (
                    <div className="flex justify-between text-[12px] mb-[4px]">
                      <span className="text-text-3">
                        Sum of installments
                        <span className="ml-[5px] text-[10px] text-text-3">
                          ({form.payments.filter(p => parseFloat(p.amount) > 0).length} added)
                        </span>
                      </span>
                      <span className="font-medium text-text-2">
                        ₹{totalInstallments.toLocaleString('en-IN')}
                      </span>
                    </div>
                  )}
                  <div className="flex justify-between text-[12px] mb-[4px]">
                    <span className="text-text-3">
                      Received so far
                      {totalPaid > 0 && (
                        <span className="ml-[5px] text-[10px] text-green">
                          ({form.payments.filter(p => p.paid && parseFloat(p.amount) > 0).length} paid ✓)
                        </span>
                      )}
                    </span>
                    <span className={`font-semibold ${totalPaid > 0 ? 'text-green' : 'text-text-3'}`}>
                      ₹{totalPaid.toLocaleString('en-IN')}
                    </span>
                  </div>
                  {totalDue !== null && (
                    <div className="flex justify-between text-[12px] border-t border-border-1 pt-[6px] mt-[4px]">
                      <span className="font-semibold text-text-2">Balance outstanding</span>
                      <span className={`font-bold ${totalDue <= 0 ? 'text-green' : 'text-amber'}`}>
                        {totalDue <= 0 ? 'Fully paid ✓' : `₹${totalDue.toLocaleString('en-IN')}`}
                      </span>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-5 py-[14px] border-t border-border-1 flex-shrink-0 bg-surface-2">
          <button
            onClick={step === 1 ? handleClose : () => setStep(s => s - 1)}
            className="text-[12px] font-medium text-text-3 hover:text-text-1 transition-colors"
          >
            {step === 1 ? 'Cancel' : '← Back'}
          </button>

          <div className="flex items-center gap-[8px]">
            {step < 3 ? (
              <>
                {step === 2 && (
                  <button
                    onClick={() => setStep(3)}
                    className="text-[12px] font-medium text-text-3 hover:text-text-1 transition-colors mr-1"
                  >
                    Skip fees →
                  </button>
                )}
                <Button
                  onClick={() => setStep(s => s + 1)}
                  disabled={step === 1 ? !canProceed1 : !canProceed2}
                >
                  Continue →
                </Button>
              </>
            ) : (
              <Button onClick={handleCreate}>
                Register Case
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
