import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useCaseStore } from '@/store/caseStore'
import Button from '@/components/ui/Button'
import { toast } from '@/store/toastStore'
import type { CaseStatus, MatterType, CasePerson, CaseHearing, CasePayment } from '@/types'

// ── Constants ─────────────────────────────────────────────────────────────────

const STATUS_DOT: Record<CaseStatus, string> = {
  active:   'bg-green animate-pulseDot',
  disposed: 'bg-white/40',
  stayed:   'bg-amber animate-pulseDot',
  settled:  'bg-blue',
}

const STATUS_BADGE: Record<CaseStatus, string> = {
  active:   'bg-green/20 text-green border-green/30',
  disposed: 'bg-white/10 text-white/50 border-white/15',
  stayed:   'bg-amber/20 text-amber border-amber/30',
  settled:  'bg-blue/20 text-blue border-blue/30',
}

const STATUS_LABEL: Record<CaseStatus, string> = {
  active: 'Active', disposed: 'Disposed', stayed: 'Stayed', settled: 'Settled',
}

const MATTER_LABEL: Record<MatterType, string> = {
  bail: 'Bail', writ: 'Writ Petition', civil: 'Civil Suit', criminal: 'Criminal',
  cheque_bounce: 'Cheque Bounce', matrimonial: 'Matrimonial',
  consumer: 'Consumer', property: 'Property Dispute', other: 'Other',
}

const MATTER_OPTIONS: { value: MatterType; label: string }[] = [
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

const ROLE_OPTIONS: { value: CasePerson['role']; label: string }[] = [
  { value: 'client', label: 'Client' },
  { value: 'opponent', label: 'Opponent' },
  { value: 'opp_counsel', label: 'Opp. Counsel' },
  { value: 'judge', label: 'Judge / Bench' },
  { value: 'witness', label: 'Witness' },
  { value: 'other', label: 'Other' },
]

const ROLE_LABEL: Record<CasePerson['role'], string> = {
  client: 'Client', opponent: 'Opponent', opp_counsel: 'Opp. Counsel',
  judge: 'Judge / Bench', witness: 'Witness', other: 'Other',
}

// Role chip colours
const ROLE_CHIP: Record<CasePerson['role'], string> = {
  client:      'bg-blue-bg text-blue border-blue/25',
  opponent:    'bg-red-50 text-red-600 border-red-200',
  opp_counsel: 'bg-surface-3 text-text-2 border-border-1',
  judge:       'bg-purple-50 text-purple-700 border-purple-200',
  witness:     'bg-amber-bg text-amber border-amber/25',
  other:       'bg-surface-2 text-text-3 border-border-1',
}

// ── Edit draft type ───────────────────────────────────────────────────────────

interface EditDraft {
  title: string
  case_number: string
  court: string
  matter_type: MatterType
  status: CaseStatus
  filing_date: string
  notes: string
  total_fees: string
  persons: CasePerson[]
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function uid() { return `${Date.now()}-${Math.random().toString(36).slice(2, 7)}` }

function fmtDate(d?: string) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}

function daysUntil(dateStr?: string): number | null {
  if (!dateStr) return null
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return null
  return Math.floor((d.getTime() - Date.now()) / 86400000)
}

function HearingBadge({ date }: { date: string }) {
  const days = daysUntil(date)
  if (days === null) return <span className="text-[11px] text-text-3">{fmtDate(date)}</span>
  if (days < 0)  return <span className="text-[11px] text-text-3">{fmtDate(date)}</span>
  if (days === 0) return <span className="text-[11px] font-bold text-red-600">{fmtDate(date)} · Today!</span>
  if (days <= 3)  return <span className="text-[11px] font-bold text-red-600">{fmtDate(date)} · {days}d</span>
  if (days <= 7)  return <span className="text-[11px] font-semibold text-amber">{fmtDate(date)} · {days}d</span>
  return <span className="text-[11px] text-text-2">{fmtDate(date)} · {days}d</span>
}

// ── Shared input styles ───────────────────────────────────────────────────────

const inputCls = 'w-full px-[9px] py-[6px] border border-border-2 rounded-sm bg-white text-text-1 text-[12.5px] outline-none focus:ring-[1.5px] focus:ring-ink/20 transition-all'
const selectCls = 'px-[9px] py-[6px] border border-border-2 rounded-sm bg-white text-text-1 text-[12.5px] outline-none focus:ring-[1.5px] focus:ring-ink/20 transition-all'

// ── Section primitive — no card, just hairline divider ────────────────────────

function Section({ title, action, children }: {
  title: string
  action?: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <div className="border-t border-border-1 pt-[16px] pb-[20px]">
      <div className="flex items-center justify-between mb-[12px]">
        <div className="text-[10px] font-bold tracking-[1px] uppercase text-text-3">{title}</div>
        {action}
      </div>
      {children}
    </div>
  )
}

function Row({ label, value, highlight }: { label: string; value: React.ReactNode; highlight?: boolean }) {
  return (
    <div className="flex items-start gap-[10px] py-[7px] border-b border-border-1 last:border-b-0">
      <span className="text-[11px] text-text-3 w-[140px] flex-shrink-0 mt-[1px]">{label}</span>
      <span className={`text-[12.5px] flex-1 ${highlight ? 'font-semibold text-text-1' : 'text-text-2'}`}>{value || '—'}</span>
    </div>
  )
}

// ── Add Hearing inline form ───────────────────────────────────────────────────

function AddHearingRow({ onAdd }: { onAdd: (h: CaseHearing) => void }) {
  const [open, setOpen] = useState(false)
  const [date, setDate] = useState('')
  const [notes, setNotes] = useState('')

  const submit = () => {
    if (!date) return
    onAdd({ id: uid(), date, notes: notes || undefined })
    setDate(''); setNotes(''); setOpen(false)
  }

  if (!open) {
    return (
      <button onClick={() => setOpen(true)} className="text-[11.5px] font-semibold text-ink hover:underline">
        + Add Hearing
      </button>
    )
  }

  return (
    <div className="flex items-center gap-[8px] mt-[4px] flex-wrap">
      <input type="date" className={`${selectCls} flex-shrink-0`} value={date} onChange={e => setDate(e.target.value)} />
      <input
        className={`${inputCls} flex-1 min-w-[120px]`}
        placeholder="Notes (optional)"
        value={notes}
        onChange={e => setNotes(e.target.value)}
        onKeyDown={e => e.key === 'Enter' && submit()}
      />
      <button onClick={submit} className="text-[11px] font-bold text-ink hover:underline flex-shrink-0">Save</button>
      <button onClick={() => setOpen(false)} className="text-[11px] text-text-3 hover:text-text-1 flex-shrink-0">Cancel</button>
    </div>
  )
}

// ── Add Payment inline form ───────────────────────────────────────────────────

function AddPaymentRow({ onAdd }: { onAdd: (p: CasePayment) => void }) {
  const [open, setOpen] = useState(false)
  const [label, setLabel] = useState('')
  const [amount, setAmount] = useState('')
  const [dueDate, setDueDate] = useState('')

  const submit = () => {
    if (!amount || parseFloat(amount) <= 0) return
    onAdd({ id: uid(), label: label.trim() || 'Payment', amount: parseFloat(amount), due_date: dueDate || undefined, paid: false })
    setLabel(''); setAmount(''); setDueDate(''); setOpen(false)
  }

  if (!open) {
    return (
      <button onClick={() => setOpen(true)} className="text-[11.5px] font-semibold text-ink hover:underline">
        + Add Installment
      </button>
    )
  }

  return (
    <div className="flex items-center gap-[8px] mt-[4px] flex-wrap">
      <input className={`${inputCls} flex-[2] min-w-[100px]`} placeholder="Label (optional)" value={label} onChange={e => setLabel(e.target.value)} />
      <input className={`${inputCls} flex-[1] min-w-[80px]`} placeholder="₹ Amount" type="number" value={amount} onChange={e => setAmount(e.target.value)} />
      <input type="date" className={`${selectCls} flex-shrink-0`} value={dueDate} onChange={e => setDueDate(e.target.value)} />
      <button onClick={submit} className="text-[11px] font-bold text-ink hover:underline flex-shrink-0">Save</button>
      <button onClick={() => setOpen(false)} className="text-[11px] text-text-3 hover:text-text-1 flex-shrink-0">Cancel</button>
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function CaseDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { getCase, updateCase, addHearing, addPayment, togglePaymentPaid, removeCase } = useCaseStore()

  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState<EditDraft | null>(null)

  const c = id ? getCase(id) : undefined

  if (!c) {
    return (
      <div className="text-center py-20">
        <div className="text-[28px] mb-3">🔍</div>
        <div className="text-[13px] font-semibold text-text-2 mb-2">Case not found</div>
        <Button onClick={() => navigate('/cases')}>← Back to Cases</Button>
      </div>
    )
  }

  const client = c.persons.find(p => p.role === 'client')
  const paidTotal = c.payments.filter(p => p.paid).reduce((s, p) => s + p.amount, 0)
  const balance = c.total_fees != null ? c.total_fees - paidTotal : null

  const today = new Date().toISOString().slice(0, 10)
  const upcoming = c.hearings.filter(h => h.date >= today).sort((a, b) => a.date.localeCompare(b.date))
  const past     = c.hearings.filter(h => h.date < today).sort((a, b)  => b.date.localeCompare(a.date))

  // ── Edit handlers ──────────────────────────────────────────────────────────

  const startEdit = () => {
    setDraft({
      title: c.title,
      case_number: c.case_number ?? '',
      court: c.court,
      matter_type: c.matter_type,
      status: c.status,
      filing_date: c.filing_date ?? '',
      notes: c.notes ?? '',
      total_fees: c.total_fees != null ? String(c.total_fees) : '',
      persons: c.persons.map(p => ({ ...p })),
    })
    setEditing(true)
  }

  const cancelEdit = () => { setEditing(false); setDraft(null) }

  const saveEdit = () => {
    if (!draft) return
    if (!draft.title.trim()) { toast('Case title is required'); return }
    if (!draft.court.trim()) { toast('Court is required'); return }

    updateCase(c.id, {
      title:       draft.title.trim(),
      case_number: draft.case_number.trim() || undefined,
      court:       draft.court.trim(),
      matter_type: draft.matter_type,
      status:      draft.status,
      filing_date: draft.filing_date || undefined,
      notes:       draft.notes.trim() || undefined,
      total_fees:  draft.total_fees ? parseFloat(draft.total_fees) : undefined,
      persons:     draft.persons.filter(p => p.name.trim()),
    })

    setEditing(false)
    setDraft(null)
    toast('Case updated')
  }

  const setDraftField = <K extends keyof EditDraft>(k: K, v: EditDraft[K]) =>
    setDraft(d => d ? { ...d, [k]: v } : d)

  const updatePerson = (idx: number, key: keyof CasePerson, val: string) =>
    setDraft(d => d ? {
      ...d,
      persons: d.persons.map((p, i) => i === idx ? { ...p, [key]: val } : p),
    } : d)

  const removePerson = (idx: number) =>
    setDraft(d => d ? { ...d, persons: d.persons.filter((_, i) => i !== idx) } : d)

  const addPerson = () =>
    setDraft(d => d ? {
      ...d,
      persons: [...d.persons, { id: uid(), role: 'other', name: '', phone: '' }],
    } : d)

  const handleDelete = () => {
    if (!window.confirm('Delete this case? This cannot be undone.')) return
    removeCase(c.id)
    navigate('/cases')
    toast('Case deleted')
  }

  // ── Days until display helper ───────────────────────────────────────────────
  const hearingDays = daysUntil(c.next_hearing)
  const hearingDaySub = (() => {
    if (hearingDays === null) return undefined
    if (hearingDays === 0) return 'Today!'
    if (hearingDays < 0) return 'Past'
    return `${hearingDays}d away`
  })()

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="max-w-[760px]">

      {/* ── Dark hero strip ── */}
      <div className="bg-sidebar rounded-[10px] px-[20px] pt-[16px] pb-[20px] mb-[24px]">

        {/* Back + Edit row */}
        <div className="flex items-center justify-between mb-[14px]">
          <button
            onClick={() => editing ? cancelEdit() : navigate('/cases')}
            className="text-[11px] font-medium text-white/40 hover:text-white/70 transition-colors"
          >
            {editing ? '✕ Cancel' : '← Cases'}
          </button>
          {editing ? (
            <button
              onClick={saveEdit}
              className="text-[11.5px] font-bold px-[14px] py-[5px] rounded-sm bg-gold text-sidebar hover:bg-gold/90 transition-colors"
            >
              Save Changes
            </button>
          ) : (
            <button
              onClick={startEdit}
              className="text-[11.5px] font-semibold px-[12px] py-[5px] rounded-sm bg-white/10 text-white/70 hover:bg-white/[0.15] hover:text-white transition-colors"
            >
              Edit
            </button>
          )}
        </div>

        {/* Title + status */}
        {editing && draft ? (
          <div className="space-y-[10px]">
            <input
              className="w-full px-[10px] py-[7px] bg-white/10 border border-white/20 rounded-sm text-white text-[18px] font-serif tracking-[-0.2px] placeholder-white/30 outline-none focus:border-gold/50 transition-colors"
              value={draft.title}
              onChange={e => setDraftField('title', e.target.value)}
              placeholder="Case title"
            />
            <div className="flex items-center gap-[8px] flex-wrap">
              <select
                className="px-[9px] py-[5px] bg-white/10 border border-white/20 rounded-sm text-white/80 text-[12px] outline-none"
                value={draft.status}
                onChange={e => setDraftField('status', e.target.value as CaseStatus)}
              >
                {STATUS_OPTIONS.map(s => <option key={s.value} value={s.value} className="bg-sidebar">{s.label}</option>)}
              </select>
              <select
                className="px-[9px] py-[5px] bg-white/10 border border-white/20 rounded-sm text-white/80 text-[12px] outline-none"
                value={draft.matter_type}
                onChange={e => setDraftField('matter_type', e.target.value as MatterType)}
              >
                {MATTER_OPTIONS.map(m => <option key={m.value} value={m.value} className="bg-sidebar">{m.label}</option>)}
              </select>
            </div>
          </div>
        ) : (
          <>
            <h1 className="font-serif text-[21px] tracking-[-0.3px] text-white leading-tight mb-[6px]">
              {c.title}
            </h1>
            <div className="flex items-center gap-[8px] flex-wrap">
              <span className={`inline-flex items-center gap-[5px] text-[10px] font-bold px-[8px] py-[2px] rounded-full border ${STATUS_BADGE[c.status]}`}>
                <span className={`w-[5px] h-[5px] rounded-full flex-shrink-0 ${STATUS_DOT[c.status]}`} />
                {STATUS_LABEL[c.status]}
              </span>
              <span className="text-white/30 text-[11px]">·</span>
              <span className="text-white/50 text-[11px]">{c.court}</span>
              <span className="text-white/30 text-[11px]">·</span>
              <span className="text-white/50 text-[11px]">{MATTER_LABEL[c.matter_type]}</span>
              {c.case_number && (
                <>
                  <span className="text-white/30 text-[11px]">·</span>
                  <span className="text-white/40 text-[11px] font-mono">{c.case_number}</span>
                </>
              )}
            </div>
          </>
        )}

        {/* Stats grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-[1px] bg-white/[0.07] rounded-[6px] overflow-hidden mt-[16px]">
          {[
            {
              label: 'Client',
              value: client?.name || '—',
              sub: client?.phone,
            },
            {
              label: 'Next Hearing',
              value: c.next_hearing ? fmtDate(c.next_hearing) : '—',
              sub: hearingDaySub,
              urgent: (hearingDays ?? 99) >= 0 && (hearingDays ?? 99) <= 3,
            },
            {
              label: 'Total Fees',
              value: c.total_fees != null ? `₹${c.total_fees.toLocaleString('en-IN')}` : '—',
              sub: paidTotal > 0 ? `₹${paidTotal.toLocaleString('en-IN')} paid` : undefined,
            },
            {
              label: 'Balance Due',
              value: balance != null ? (balance <= 0 ? 'Paid ✓' : `₹${balance.toLocaleString('en-IN')}`) : '—',
              positive: balance !== null && balance <= 0,
              urgent: balance !== null && balance > 0,
            },
          ].map(stat => (
            <div key={stat.label} className="bg-sidebar px-[14px] py-[10px]">
              <div className="text-[9px] font-bold tracking-[0.8px] uppercase text-white/30 mb-[3px]">{stat.label}</div>
              <div className={`text-[13px] font-semibold leading-tight truncate ${
                (stat as { urgent?: boolean }).urgent ? 'text-red-400'
                : (stat as { positive?: boolean }).positive ? 'text-green-400'
                : 'text-white'
              }`}>{stat.value}</div>
              {stat.sub && <div className="text-[10px] text-white/35 mt-[1px] truncate">{stat.sub}</div>}
            </div>
          ))}
        </div>
      </div>

      {/* ── Parties ── */}
      {(c.persons.length > 0 || (editing && draft)) && (
        <Section title="Parties Involved">
          {editing && draft ? (
            <div className="space-y-[8px]">
              {draft.persons.map((p, i) => (
                <div key={p.id} className="flex items-center gap-[8px] flex-wrap">
                  <select
                    className={`${selectCls} w-[130px] flex-shrink-0`}
                    value={p.role}
                    onChange={e => updatePerson(i, 'role', e.target.value)}
                  >
                    {ROLE_OPTIONS.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
                  </select>
                  <input
                    className={`${inputCls} flex-[2] min-w-[120px]`}
                    placeholder="Full name"
                    value={p.name}
                    onChange={e => updatePerson(i, 'name', e.target.value)}
                  />
                  <input
                    className={`${inputCls} flex-[1] min-w-[100px]`}
                    placeholder="Phone (optional)"
                    value={p.phone ?? ''}
                    onChange={e => updatePerson(i, 'phone', e.target.value)}
                  />
                  <button
                    onClick={() => removePerson(i)}
                    className="text-text-3 hover:text-red-500 text-[16px] leading-none flex-shrink-0 transition-colors"
                    title="Remove"
                  >×</button>
                </div>
              ))}
              <button onClick={addPerson} className="text-[11.5px] font-semibold text-ink hover:underline mt-[4px]">
                + Add Person
              </button>
            </div>
          ) : (
            <div className="flex flex-wrap gap-[8px]">
              {c.persons.map(p => (
                <div
                  key={p.id}
                  className={`inline-flex items-center gap-[7px] border rounded-[6px] px-[10px] py-[6px] ${ROLE_CHIP[p.role]}`}
                >
                  <span className="text-[9.5px] font-bold uppercase tracking-[0.5px] opacity-70">{ROLE_LABEL[p.role]}</span>
                  <span className="text-[12.5px] font-semibold leading-tight">{p.name}</span>
                  {p.phone && (
                    <span className="text-[10.5px] font-mono opacity-60 ml-[2px]">{p.phone}</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </Section>
      )}

      {/* ── Hearings ── */}
      <Section title="Hearings" action={<AddHearingRow onAdd={h => addHearing(c.id, h)} />}>
        {upcoming.length === 0 && past.length === 0 ? (
          <div className="text-[12px] text-text-3 italic">No hearings logged yet.</div>
        ) : (
          <div>
            {upcoming.map(h => (
              <div key={h.id} className="flex items-start gap-[10px] py-[8px] border-b border-border-1 last:border-b-0">
                <span className="flex-shrink-0"><HearingBadge date={h.date} /></span>
                <span className="text-[10px] bg-green-bg text-green font-bold px-[6px] py-[1.5px] rounded-sm flex-shrink-0 uppercase tracking-[0.4px]">Upcoming</span>
                {h.notes && <span className="text-[12px] text-text-2 flex-1">{h.notes}</span>}
              </div>
            ))}
            {past.map(h => (
              <div key={h.id} className="flex items-start gap-[10px] py-[8px] border-b border-border-1 last:border-b-0 opacity-60">
                <span className="text-[11px] text-text-3 flex-shrink-0">{fmtDate(h.date)}</span>
                <span className="text-[10px] bg-surface-3 text-text-3 font-bold px-[6px] py-[1.5px] rounded-sm flex-shrink-0 uppercase tracking-[0.4px]">Past</span>
                {h.notes && <span className="text-[12px] text-text-2 flex-1">{h.notes}</span>}
                {h.outcome && <span className="text-[11.5px] font-medium text-text-1 flex-shrink-0">{h.outcome}</span>}
              </div>
            ))}
          </div>
        )}
      </Section>

      {/* ── Fees & Payments ── */}
      <Section title="Fees & Payments" action={<AddPaymentRow onAdd={p => addPayment(c.id, p)} />}>

        {/* Compact fee summary strip */}
        {!editing ? (
          <div className="inline-flex items-center divide-x divide-border-1 border border-border-1 rounded-sm mb-[12px] text-[12px] overflow-hidden">
            <div className="flex items-center gap-[5px] px-[12px] py-[6px]">
              <span className="text-text-3">Agreed</span>
              <span className="font-semibold text-text-1">
                {c.total_fees != null ? `₹${c.total_fees.toLocaleString('en-IN')}` : '—'}
              </span>
            </div>
            <div className="flex items-center gap-[5px] px-[12px] py-[6px]">
              <span className="text-text-3">Paid</span>
              <span className="font-semibold text-green">₹{paidTotal.toLocaleString('en-IN')}</span>
            </div>
            {balance != null && (
              <div className="flex items-center gap-[5px] px-[12px] py-[6px]">
                <span className="text-text-3">Due</span>
                <span className={`font-semibold ${balance <= 0 ? 'text-green' : 'text-amber'}`}>
                  {balance <= 0 ? '₹0 ✓' : `₹${balance.toLocaleString('en-IN')}`}
                </span>
              </div>
            )}
          </div>
        ) : draft ? (
          <div className="flex items-center gap-[10px] mb-[12px]">
            <span className="text-[12px] text-text-3 flex-shrink-0">Total agreed fees</span>
            <input
              className={`${inputCls} w-[140px]`}
              type="number"
              placeholder="₹ 0"
              value={draft.total_fees}
              onChange={e => setDraftField('total_fees', e.target.value)}
            />
          </div>
        ) : null}

        {/* Payment rows */}
        {c.payments.length === 0 ? (
          <div className="text-[12px] text-text-3 italic">No payments logged yet.</div>
        ) : (
          <div>
            {c.payments.map(p => (
              <div key={p.id} className="flex items-center gap-[10px] py-[8px] border-b border-border-1 last:border-b-0">
                <button
                  onClick={() => togglePaymentPaid(c.id, p.id)}
                  className={[
                    'w-[17px] h-[17px] rounded-sm border-[1.5px] flex items-center justify-center flex-shrink-0 transition-colors',
                    p.paid ? 'bg-ink border-ink text-white' : 'border-border-2 hover:border-ink',
                  ].join(' ')}
                  title={p.paid ? 'Mark unpaid' : 'Mark paid'}
                >
                  {p.paid && <span className="text-[9px] font-bold">✓</span>}
                </button>
                <div className="flex-1 min-w-0">
                  <span className={`text-[12.5px] font-medium ${p.paid ? 'text-text-3 line-through' : 'text-text-1'}`}>
                    {p.label}
                  </span>
                  {p.paid && p.paid_date && <span className="text-[10px] text-text-3 ml-[6px]">paid {fmtDate(p.paid_date)}</span>}
                  {!p.paid && p.due_date && <span className="text-[10px] text-text-3 ml-[6px]">due {fmtDate(p.due_date)}</span>}
                </div>
                <span className={`text-[12.5px] font-semibold flex-shrink-0 ${p.paid ? 'text-green' : 'text-text-1'}`}>
                  ₹{p.amount.toLocaleString('en-IN')}
                </span>
              </div>
            ))}
          </div>
        )}
      </Section>

      {/* ── Notes ── */}
      {(editing && draft) || c.notes ? (
        <Section title="Notes">
          {editing && draft ? (
            <textarea
              className={`${inputCls} w-full leading-[1.6] resize-none`}
              rows={4}
              placeholder="Key facts, client instructions, strategy notes…"
              value={draft.notes}
              onChange={e => setDraftField('notes', e.target.value)}
            />
          ) : (
            <p className="text-[12.5px] text-text-2 leading-[1.6] whitespace-pre-wrap">{c.notes}</p>
          )}
        </Section>
      ) : null}

      {/* ── Case Info ── */}
      <Section title="Case Info">
        {editing && draft ? (
          <div className="space-y-[10px]">
            <div className="flex items-start gap-[10px]">
              <span className="text-[11px] text-text-3 w-[140px] flex-shrink-0 mt-[8px]">Case Number</span>
              <input
                className={`${inputCls} flex-1`}
                placeholder="CWP-12345-2025"
                value={draft.case_number}
                onChange={e => setDraftField('case_number', e.target.value)}
              />
            </div>
            <div className="flex items-start gap-[10px]">
              <span className="text-[11px] text-text-3 w-[140px] flex-shrink-0 mt-[8px]">Court</span>
              <input
                className={`${inputCls} flex-1`}
                placeholder="Court name"
                value={draft.court}
                onChange={e => setDraftField('court', e.target.value)}
              />
            </div>
            <div className="flex items-start gap-[10px]">
              <span className="text-[11px] text-text-3 w-[140px] flex-shrink-0 mt-[8px]">Filing Date</span>
              <input
                type="date"
                className={selectCls}
                value={draft.filing_date}
                onChange={e => setDraftField('filing_date', e.target.value)}
              />
            </div>
          </div>
        ) : (
          <>
            <Row label="Case Number" value={c.case_number} />
            <Row label="Court" value={c.court} highlight />
            <Row label="Matter Type" value={MATTER_LABEL[c.matter_type]} />
            <Row label="Filing Date" value={fmtDate(c.filing_date)} />
            <Row label="Registered on" value={fmtDate(c.created_at)} />
          </>
        )}

        <div className="pt-[14px] mt-[6px] border-t border-border-1">
          {editing ? (
            <div className="flex items-center gap-[12px]">
              <button
                onClick={saveEdit}
                className="text-[11.5px] font-bold px-[14px] py-[5px] rounded-sm bg-ink text-white hover:bg-[#2e2b27] transition-colors"
              >
                Save Changes
              </button>
              <button onClick={cancelEdit} className="text-[12px] font-medium text-text-3 hover:text-text-1 transition-colors">
                Cancel
              </button>
            </div>
          ) : (
            <button onClick={handleDelete} className="text-[11.5px] font-medium text-red-400 hover:text-red-600 transition-colors">
              Delete this case
            </button>
          )}
        </div>
      </Section>

    </div>
  )
}
