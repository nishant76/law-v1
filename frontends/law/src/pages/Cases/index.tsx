import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useCaseStore } from '@/store/caseStore'
import NewCaseModal from './NewCaseModal'
import Button from '@/components/ui/Button'
import type { LegalCase, CaseStatus, MatterType } from '@/types'

// ── Helpers ──────────────────────────────────────────────────────────────────

const STATUS_LABEL: Record<CaseStatus, string> = {
  active: 'Active', disposed: 'Disposed', stayed: 'Stayed', settled: 'Settled',
}

const STATUS_CLS: Record<CaseStatus, string> = {
  active: 'bg-green-bg text-green',
  disposed: 'bg-surface-3 text-text-3',
  stayed: 'bg-amber-bg text-amber',
  settled: 'bg-blue-bg text-blue',
}

const MATTER_LABEL: Record<MatterType, string> = {
  bail: 'Bail', writ: 'Writ', civil: 'Civil', criminal: 'Criminal',
  cheque_bounce: 'Cheque Bounce', matrimonial: 'Matrimonial',
  consumer: 'Consumer', property: 'Property', other: 'Other',
}

const FILTER_TABS: { value: CaseStatus | 'all'; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'active', label: 'Active' },
  { value: 'stayed', label: 'Stayed' },
  { value: 'settled', label: 'Settled' },
  { value: 'disposed', label: 'Disposed' },
]

function daysUntil(dateStr?: string): number | null {
  if (!dateStr) return null
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return null
  return Math.floor((d.getTime() - Date.now()) / 86400000)
}

function hearingChip(dateStr?: string) {
  const days = daysUntil(dateStr)
  if (days === null) return null
  const date = new Date(dateStr!).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
  if (days < 0) return <span className="text-text-3 text-[11px]">Past · {date}</span>
  if (days === 0) return <span className="font-bold text-red-600 text-[11px]">Today!</span>
  if (days <= 3) return <span className="font-bold text-red-600 text-[11px]">{date} · {days}d</span>
  if (days <= 7) return <span className="font-semibold text-amber text-[11px]">{date} · {days}d</span>
  return <span className="text-text-2 text-[11px]">{date} · {days}d</span>
}

function paymentTag(c: LegalCase) {
  if (!c.total_fees && c.payments.length === 0) return null
  const paid = c.payments.filter(p => p.paid).reduce((s, p) => s + p.amount, 0)
  if (c.total_fees) {
    const balance = c.total_fees - paid
    if (balance <= 0) return <span className="text-[10px] font-semibold text-green">Paid ✓</span>
    return <span className="text-[10px] font-semibold text-amber">₹{(balance / 1000).toFixed(0)}k due</span>
  }
  if (paid > 0) return <span className="text-[10px] text-text-3">₹{(paid / 1000).toFixed(0)}k rcvd</span>
  return null
}

// ── Status dot colour ─────────────────────────────────────────────────────────

const STATUS_DOT: Record<CaseStatus, string> = {
  active:   'bg-green shadow-[0_0_0_3px_rgba(22,163,74,0.18)]',
  disposed: 'bg-text-3',
  stayed:   'bg-amber shadow-[0_0_0_3px_rgba(180,83,9,0.18)]',
  settled:  'bg-blue shadow-[0_0_0_3px_rgba(29,78,216,0.18)]',
}

// ── Case Row ──────────────────────────────────────────────────────────────────

function CaseCard({ c }: { c: LegalCase }) {
  const navigate = useNavigate()
  const client = c.persons.find(p => p.role === 'client')

  return (
    <div
      onClick={() => navigate(`/cases/${c.id}`)}
      className="flex items-center gap-[14px] px-[14px] py-[13px] border-b border-border-1 cursor-pointer hover:bg-surface-2 transition-colors group last:border-b-0"
    >
      {/* Status dot */}
      <span className={`w-[8px] h-[8px] rounded-full flex-shrink-0 ${STATUS_DOT[c.status]}`} />

      {/* Main info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-[8px] mb-[2px]">
          <span className="text-[13px] font-semibold text-text-1 truncate">{c.title}</span>
          <span className="text-[9.5px] font-medium px-[5px] py-[1px] rounded-full bg-surface-3 text-text-3 flex-shrink-0 hidden sm:inline">
            {MATTER_LABEL[c.matter_type]}
          </span>
        </div>
        <div className="flex items-center gap-[6px] text-[11px] text-text-3 flex-wrap">
          <span>{c.court}</span>
          {c.case_number && (
            <><span>·</span><span className="font-mono">{c.case_number}</span></>
          )}
          {client && (
            <><span>·</span><span className="text-text-2">{client.name}</span></>
          )}
        </div>
      </div>

      {/* Right side — hearing + fee */}
      <div className="flex flex-col items-end gap-[3px] flex-shrink-0">
        {c.next_hearing
          ? hearingChip(c.next_hearing)
          : <span className="text-[11px] text-text-3">No hearing set</span>
        }
        {paymentTag(c)}
      </div>

      <span className="text-text-3 text-[15px] group-hover:text-text-2 transition-colors flex-shrink-0">›</span>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function CasesPage() {
  const navigate = useNavigate()
  const cases = useCaseStore((s) => s.cases)
  const [filter, setFilter] = useState<CaseStatus | 'all'>('all')
  const [search, setSearch] = useState('')
  const [showModal, setShowModal] = useState(false)

  const filtered = cases
    .filter(c => filter === 'all' || c.status === filter)
    .filter(c => {
      if (!search.trim()) return true
      const q = search.toLowerCase()
      return (
        c.title.toLowerCase().includes(q) ||
        (c.case_number?.toLowerCase().includes(q) ?? false) ||
        c.court.toLowerCase().includes(q) ||
        c.persons.some(p => p.name.toLowerCase().includes(q))
      )
    })

  const activeCnt = cases.filter(c => c.status === 'active').length

  return (
    <div className="max-w-[860px]">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="font-serif text-[22px] tracking-[-0.3px] text-text-1">My Cases</h1>
          <p className="text-[12px] text-text-3 mt-[1px]">
            {cases.length} case{cases.length !== 1 ? 's' : ''} · {activeCnt} active
          </p>
        </div>
        <Button onClick={() => setShowModal(true)}>+ New Case</Button>
      </div>

      {/* Search + filter */}
      <div className="flex items-center gap-[10px] mb-[14px]">
        <input
          className="flex-1 px-[10px] py-[7px] border border-border-1 rounded-sm bg-white text-text-1 text-[12.5px] outline-none focus:border-border-2 transition-colors"
          placeholder="Search by name, case number, court…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <div className="flex items-center gap-[6px] mb-[14px]">
        {FILTER_TABS.map(t => (
          <button
            key={t.value}
            onClick={() => setFilter(t.value)}
            className={[
              'text-[11px] font-semibold px-[10px] py-[5px] rounded-full transition-colors',
              filter === t.value
                ? 'bg-ink text-white'
                : 'bg-surface-2 text-text-3 hover:bg-surface-3 hover:text-text-2',
            ].join(' ')}
          >
            {t.label}
            {t.value !== 'all' && (
              <span className="ml-[5px] opacity-70">
                {cases.filter(c => c.status === t.value).length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* List */}
      {filtered.length === 0 ? (
        <div className="text-center py-16">
          <div className="text-[28px] mb-3">⚖️</div>
          <div className="text-[13px] font-semibold text-text-2 mb-[4px]">
            {cases.length === 0 ? 'No cases yet' : 'No matching cases'}
          </div>
          <div className="text-[12px] text-text-3 mb-4">
            {cases.length === 0
              ? 'Register your first case to get started'
              : 'Try a different search or filter'}
          </div>
          {cases.length === 0 && (
            <Button onClick={() => setShowModal(true)}>+ Register First Case</Button>
          )}
        </div>
      ) : (
        <div className="bg-white border border-border-1 rounded-DEFAULT overflow-hidden">
          {filtered.map(c => <CaseCard key={c.id} c={c} />)}
        </div>
      )}

      <NewCaseModal
        open={showModal}
        onClose={() => setShowModal(false)}
        onCreated={(id) => { setShowModal(false); navigate(`/cases/${id}`) }}
      />
    </div>
  )
}
