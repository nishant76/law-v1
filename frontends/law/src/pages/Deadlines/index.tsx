import { useState, useEffect } from 'react'
import dayjs from 'dayjs'
import { useDeadlineStore, type Deadline, type DeadlineType } from '@/store/deadlineStore'
import Button from '@/components/ui/Button'
import { toast } from '@/store/toastStore'
import { getEcourtsStatus, setEcourtsAdvocateName, syncEcourtsHearings } from '@/api/ecourts'

// ── Helpers ───────────────────────────────────────────────────────────────────

function uid() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
}

function daysUntil(due: string) {
  return dayjs(due).diff(dayjs().startOf('day'), 'day')
}

function urgencyLabel(due: string) {
  const diff = daysUntil(due)
  if (diff < 0)   return { text: 'Missed',    cls: 'bg-red-bg text-red-600 border-red-200' }
  if (diff === 0) return { text: 'Today',     cls: 'bg-red-bg text-red-600 border-red-200' }
  if (diff === 1) return { text: 'Tomorrow',  cls: 'bg-amber-bg text-amber border-amber/30' }
  if (diff <= 7)  return { text: `${diff}d`,  cls: 'bg-amber-bg text-amber border-amber/30' }
  return           { text: `${diff}d`,        cls: 'bg-green-bg text-green border-green/30' }
}

const TYPE_LABEL: Record<DeadlineType, string> = {
  hearing: 'Hearing',
  filing: 'Filing',
  limitation: 'Limitation',
}

const TYPE_OPTIONS: { value: DeadlineType; label: string }[] = [
  { value: 'hearing',   label: 'Hearing Date' },
  { value: 'filing',    label: 'Filing Deadline' },
  { value: 'limitation', label: 'Limitation Period' },
]

// ── Add Form ──────────────────────────────────────────────────────────────────

const inputCls  = 'w-full px-[9px] py-[6px] border border-border-1 rounded-sm bg-white text-text-1 text-[12.5px] outline-none focus:border-border-2 transition-colors'
const selectCls = 'px-[9px] py-[6px] border border-border-1 rounded-sm bg-white text-text-1 text-[12.5px] outline-none focus:border-border-2 transition-colors'

interface AddFormProps {
  onAdd: (d: Deadline) => void
  onCancel: () => void
}

function AddForm({ onAdd, onCancel }: AddFormProps) {
  const [matterTitle,     setMatterTitle]     = useState('')
  const [court,           setCourt]           = useState('')
  const [caseNumber,      setCaseNumber]      = useState('')
  const [deadlineType,    setDeadlineType]    = useState<DeadlineType>('hearing')
  const [dueDate,         setDueDate]         = useState('')
  const [notes,           setNotes]           = useState('')
  const [clientPhone,     setClientPhone]     = useState('')
  const [whatsappEnabled, setWhatsappEnabled] = useState(false)

  const submit = () => {
    if (!matterTitle.trim()) { toast('Matter title is required'); return }
    if (!court.trim())       { toast('Court is required');        return }
    if (!dueDate)            { toast('Due date is required');     return }
    if (whatsappEnabled && !clientPhone.trim()) {
      toast('Enter client phone number to enable WhatsApp reminders')
      return
    }

    onAdd({
      id:               uid(),
      matter_title:     matterTitle.trim(),
      court:            court.trim(),
      case_number:      caseNumber.trim() || undefined,
      deadline_type:    deadlineType,
      due_date:         dueDate,
      notes:            notes.trim() || undefined,
      client_phone:     clientPhone.trim() || undefined,
      whatsapp_enabled: whatsappEnabled && !!clientPhone.trim(),
      created_at:       new Date().toISOString(),
    })
  }

  return (
    <div className="bg-white border border-border-1 rounded-DEFAULT px-[16px] py-[14px] mb-5">
      <div className="text-[11px] font-bold tracking-[0.5px] uppercase text-text-3 mb-[12px]">
        New Deadline
      </div>

      {/* Core fields */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-[10px] mb-[10px]">
        <div>
          <label className="text-[10.5px] text-text-3 mb-[3px] block">Matter / Case Title *</label>
          <input
            className={inputCls}
            placeholder="e.g. Sharma vs State of Punjab"
            value={matterTitle}
            onChange={e => setMatterTitle(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && submit()}
          />
        </div>
        <div>
          <label className="text-[10.5px] text-text-3 mb-[3px] block">Court *</label>
          <input
            className={inputCls}
            placeholder="e.g. P&H High Court, Chandigarh"
            value={court}
            onChange={e => setCourt(e.target.value)}
          />
        </div>
        <div>
          <label className="text-[10.5px] text-text-3 mb-[3px] block">Case Number</label>
          <input
            className={inputCls}
            placeholder="CWP-1234-2025"
            value={caseNumber}
            onChange={e => setCaseNumber(e.target.value)}
          />
        </div>
        <div>
          <label className="text-[10.5px] text-text-3 mb-[3px] block">Deadline Type *</label>
          <select
            className={`${selectCls} w-full`}
            value={deadlineType}
            onChange={e => setDeadlineType(e.target.value as DeadlineType)}
          >
            {TYPE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
        <div>
          <label className="text-[10.5px] text-text-3 mb-[3px] block">Due Date *</label>
          <input
            type="date"
            className={`${selectCls} w-full`}
            value={dueDate}
            onChange={e => setDueDate(e.target.value)}
          />
        </div>
        <div>
          <label className="text-[10.5px] text-text-3 mb-[3px] block">Notes</label>
          <input
            className={inputCls}
            placeholder="Optional notes"
            value={notes}
            onChange={e => setNotes(e.target.value)}
          />
        </div>
      </div>

      {/* WhatsApp section */}
      <div className="border-t border-border-1 pt-[11px] mt-[4px] mb-[12px]">
        <div className="text-[10px] font-bold tracking-[0.5px] uppercase text-text-3 mb-[9px]">
          Client WhatsApp Reminders
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-[10px] mb-[9px]">
          <div>
            <label className="text-[10.5px] text-text-3 mb-[3px] block">
              Client Phone Number
              <span className="text-text-3 font-normal ml-[4px]">(optional)</span>
            </label>
            <input
              className={inputCls}
              placeholder="+91 98765 43210"
              value={clientPhone}
              onChange={e => setClientPhone(e.target.value)}
              type="tel"
            />
          </div>
        </div>
        <label className="flex items-start gap-[9px] cursor-pointer group">
          <div className="relative mt-[1px] flex-shrink-0">
            <input
              type="checkbox"
              className="sr-only"
              checked={whatsappEnabled}
              onChange={e => setWhatsappEnabled(e.target.checked)}
            />
            <div className={[
              'w-[15px] h-[15px] rounded-[3px] border flex items-center justify-center transition-colors',
              whatsappEnabled
                ? 'bg-green border-green'
                : 'bg-white border-border-2 group-hover:border-border-2',
            ].join(' ')}>
              {whatsappEnabled && (
                <svg width="9" height="7" viewBox="0 0 9 7" fill="none">
                  <path d="M1 3.5L3.5 6L8 1" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              )}
            </div>
          </div>
          <div>
            <span className="text-[12px] font-medium text-text-1">
              Send WhatsApp reminders to client
            </span>
            <p className="text-[10.5px] text-text-3 leading-snug mt-[1px]">
              Client will receive reminders 7 days, 1 day before, and on the day of the deadline.
              By checking this, the client consents to receive automated WhatsApp messages from
              your firm regarding their matter.
            </p>
          </div>
        </label>
      </div>

      <div className="flex items-center gap-[10px]">
        <Button onClick={submit}>Save Deadline</Button>
        <button
          onClick={onCancel}
          className="text-[12px] font-medium text-text-3 hover:text-text-1 transition-colors"
        >
          Cancel
        </button>
      </div>
    </div>
  )
}

// ── Deadline Row ──────────────────────────────────────────────────────────────

function DeadlineRow({ d, onDelete }: { d: Deadline; onDelete: () => void }) {
  const { text, cls } = urgencyLabel(d.due_date)
  const dayNum = dayjs(d.due_date).format('D')
  const mon    = dayjs(d.due_date).format('MMM').toUpperCase()

  return (
    <div className="bg-white border border-border-1 rounded-DEFAULT px-[15px] py-[11px] flex items-center gap-[13px] group hover:border-border-2 hover:shadow-[0_1px_8px_rgba(0,0,0,0.05)] transition-all">
      {/* Date block */}
      <div className="w-[36px] text-center flex-shrink-0">
        <div className="font-serif text-[20px] text-text-1 leading-none">{dayNum}</div>
        <div className="text-[9px] font-bold tracking-[0.5px] uppercase text-text-3">{mon}</div>
      </div>

      <div className="w-px h-8 bg-border-1 flex-shrink-0" />

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="text-[12.5px] font-semibold text-text-1 truncate">{d.matter_title}</div>
        <div className="flex items-center gap-[6px] mt-[2px] flex-wrap">
          <span className="text-[11px] text-text-3">{d.court}</span>
          {d.case_number && (
            <>
              <span className="text-[9px] text-text-3">·</span>
              <span className="text-[11px] text-text-3 font-mono">{d.case_number}</span>
            </>
          )}
          <span className="text-[9px] text-text-3">·</span>
          <span className="text-[10.5px] text-text-3">{TYPE_LABEL[d.deadline_type]}</span>
          {d.whatsapp_enabled && d.client_phone && (
            <>
              <span className="text-[9px] text-text-3">·</span>
              <span className="text-[10px] text-green font-medium flex items-center gap-[3px]">
                <span>💬</span> WhatsApp
              </span>
            </>
          )}
        </div>
        {d.notes && (
          <div className="text-[11px] text-text-3 mt-[2px] truncate">{d.notes}</div>
        )}
      </div>

      {/* Urgency badge */}
      <span className={`text-[10px] font-bold px-[8px] py-[3px] rounded-full border flex-shrink-0 ${cls}`}>
        {text}
      </span>

      {/* Delete */}
      <button
        onClick={onDelete}
        className="opacity-0 group-hover:opacity-100 text-text-3 hover:text-red-500 transition-all text-[16px] leading-none flex-shrink-0 px-1"
        title="Remove"
      >
        ×
      </button>
    </div>
  )
}

// ── eCourts sync panel ──────────────────────────────────────────────────────

function ECourtsPanel({
  deadlines, addDeadline,
}: {
  deadlines: Deadline[]
  addDeadline: (d: Deadline) => void
}) {
  const [configured, setConfigured] = useState(false)
  const [advocateName, setAdvocateName] = useState('')
  const [editing, setEditing] = useState(false)
  const [draftName, setDraftName] = useState('')
  const [isSyncing, setIsSyncing] = useState(false)
  const [available, setAvailable] = useState(false) // backend reachable

  useEffect(() => {
    let alive = true
    getEcourtsStatus()
      .then(({ data }) => {
        if (!alive) return
        setAvailable(true)
        setConfigured(!!data.configured)
        setAdvocateName(data.advocate_name ?? '')
        setEditing(!data.advocate_name)
      })
      .catch(() => { /* backend not reachable / not logged in — hide gracefully */ })
    return () => { alive = false }
  }, [])

  if (!available) return null

  const saveName = async () => {
    const name = draftName.trim()
    if (name.length < 2) { toast('Enter your eCourts advocate name'); return }
    try {
      await setEcourtsAdvocateName(name)
      setAdvocateName(name)
      setEditing(false)
      toast('Advocate name saved')
    } catch {
      toast('Could not save advocate name.')
    }
  }

  const sync = async () => {
    if (isSyncing) return
    setIsSyncing(true)
    try {
      const { data } = await syncEcourtsHearings()
      // Map fetched hearings into the deadline tracker (dedupe by CNR + date).
      let added = 0
      for (const h of data.upcoming ?? []) {
        const dup = deadlines.some(d => d.case_number === h.cnr && d.due_date === h.next_hearing_date)
        if (dup) continue
        addDeadline({
          id: `ec-${h.cnr}-${h.next_hearing_date}`,
          matter_title: h.case_name,
          court: h.court ?? 'eCourts',
          case_number: h.cnr,
          deadline_type: 'hearing',
          due_date: h.next_hearing_date,
          notes: 'Synced from eCourts',
          whatsapp_enabled: false,
          created_at: new Date().toISOString(),
        })
        added++
      }
      toast(`eCourts: ${data.fetched} case${data.fetched !== 1 ? 's' : ''} found · ${added} hearing${added !== 1 ? 's' : ''} added`)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast(msg || 'eCourts sync failed.')
    } finally {
      setIsSyncing(false)
    }
  }

  return (
    <div className="bg-white border border-border-1 rounded-DEFAULT px-[15px] py-[12px] mb-5">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="min-w-0">
          <div className="text-[12px] font-bold text-text-1 flex items-center gap-[6px]">⚖ eCourts sync</div>
          <p className="text-[11px] text-text-3 mt-[1px]">
            {configured
              ? 'Auto-pull your hearing dates from eCourts into your deadlines.'
              : 'eCourts API not configured on the server — ask your admin to set ECOURTS_API_TOKEN.'}
          </p>
        </div>
        {!editing && advocateName && (
          <div className="flex items-center gap-[8px] flex-shrink-0">
            <span className="text-[11.5px] text-text-2">Advocate: <strong className="text-text-1">{advocateName}</strong></span>
            <button onClick={() => { setDraftName(advocateName); setEditing(true) }} className="text-[11px] text-text-3 hover:text-text-1">Edit</button>
            <Button onClick={sync} disabled={isSyncing || !configured}>
              {isSyncing ? 'Syncing…' : '↻ Sync now'}
            </Button>
          </div>
        )}
      </div>

      {editing && (
        <div className="flex items-center gap-[8px] mt-[10px]">
          <input
            className="flex-1 px-[9px] py-[6px] border border-border-1 rounded-sm bg-white text-text-1 text-[12.5px] outline-none focus:border-border-2"
            placeholder="Your advocate name as registered on eCourts"
            value={draftName}
            onChange={e => setDraftName(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && saveName()}
          />
          <Button onClick={saveName}>Save</Button>
          {advocateName && (
            <button onClick={() => setEditing(false)} className="text-[11px] text-text-3 hover:text-text-1">Cancel</button>
          )}
        </div>
      )}
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function DeadlinesPage() {
  const { deadlines, addDeadline, removeDeadline } = useDeadlineStore()
  const [showForm, setShowForm] = useState(false)

  const missed   = deadlines.filter(d => daysUntil(d.due_date) < 0)
  const urgent   = deadlines.filter(d => { const diff = daysUntil(d.due_date); return diff >= 0 && diff <= 7 })
  const upcoming = deadlines.filter(d => daysUntil(d.due_date) > 7)

  const handleAdd = (d: Deadline) => {
    addDeadline(d)
    setShowForm(false)
    toast(d.whatsapp_enabled ? 'Deadline added · WhatsApp reminders enabled' : 'Deadline added')
  }

  return (
    <div className="max-w-[860px]">

      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="font-serif text-[22px] tracking-[-0.3px] text-text-1">Deadlines</h1>
          <p className="text-[12px] text-text-3 mt-[1px]">
            {deadlines.length} deadline{deadlines.length !== 1 ? 's' : ''} tracked
            {missed.length > 0 && (
              <span className="text-red-600 font-semibold"> · {missed.length} missed</span>
            )}
          </p>
        </div>
        <Button onClick={() => setShowForm(s => !s)}>
          {showForm ? '✕ Cancel' : '+ Add Deadline'}
        </Button>
      </div>

      {/* eCourts sync */}
      <ECourtsPanel deadlines={deadlines} addDeadline={addDeadline} />

      {/* Add form */}
      {showForm && (
        <AddForm
          onAdd={handleAdd}
          onCancel={() => setShowForm(false)}
        />
      )}

      {/* Missed alerts */}
      {missed.length > 0 && (
        <div className="mb-5">
          <div className="text-[10px] font-bold tracking-[0.7px] uppercase text-red-600 mb-[8px]">
            ⚠️ Missed — Immediate Attention Required
          </div>
          {missed.map(d => (
            <div key={d.id} className="mb-2">
              <div className="bg-red-bg border border-red-200 rounded-DEFAULT px-[15px] py-[12px] flex items-start gap-3">
                <div className="flex-1">
                  <div className="text-[12.5px] font-semibold text-text-1">{d.matter_title}</div>
                  <div className="text-[11px] text-text-3 mt-[2px]">
                    {TYPE_LABEL[d.deadline_type]} deadline was{' '}
                    <strong className="text-red-600">{dayjs(d.due_date).format('D MMMM YYYY')}</strong>
                    {d.court && ` · ${d.court}`}
                  </div>
                </div>
                <button
                  onClick={() => removeDeadline(d.id)}
                  className="text-text-3 hover:text-red-500 transition-colors text-[16px] leading-none flex-shrink-0"
                  title="Remove"
                >
                  ×
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Urgent — this week */}
      {urgent.length > 0 && (
        <div className="mb-5">
          <div className="text-[10px] font-bold tracking-[0.7px] uppercase text-amber mb-[8px]">
            This Week
          </div>
          <div className="space-y-[7px]">
            {urgent.map(d => (
              <DeadlineRow key={d.id} d={d} onDelete={() => { removeDeadline(d.id); toast('Deadline removed') }} />
            ))}
          </div>
        </div>
      )}

      {/* Upcoming */}
      {upcoming.length > 0 && (
        <div className="mb-5">
          <div className="text-[10px] font-bold tracking-[0.7px] uppercase text-text-3 mb-[8px]">
            Upcoming
          </div>
          <div className="space-y-[7px]">
            {upcoming.map(d => (
              <DeadlineRow key={d.id} d={d} onDelete={() => { removeDeadline(d.id); toast('Deadline removed') }} />
            ))}
          </div>
        </div>
      )}

      {/* Empty state */}
      {deadlines.length === 0 && !showForm && (
        <div className="text-center py-16">
          <div className="text-[30px] mb-3">📅</div>
          <p className="font-serif text-[16px] text-text-2 mb-1">No deadlines yet</p>
          <p className="text-[12px] text-text-3 mb-4">
            Track hearings, filing deadlines, and limitation periods for your matters.
          </p>
          <Button onClick={() => setShowForm(true)}>+ Add First Deadline</Button>
        </div>
      )}
    </div>
  )
}
