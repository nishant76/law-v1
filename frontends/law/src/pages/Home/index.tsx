import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { useCaseStore } from '@/store/caseStore'
import NewCaseModal from '@/pages/Cases/NewCaseModal'
import dayjs from 'dayjs'
import type { LegalCase, CaseStatus, MatterType } from '@/types'

// ── Live tool cards ───────────────────────────────────────────────────────────

interface LiveCard {
  icon: string
  iconBg: string
  accent: string
  title: string
  desc: string
  to?: string
  onClick?: () => void
}

interface SoonCard {
  icon: string
  title: string
  desc: string
}

const SOON_CARDS: SoonCard[] = [
  {
    icon: '✦',
    title: 'AI Legal Drafting',
    desc: 'Draft bail applications, writs and notices with AI research side by side.',
  },
  {
    icon: '⚡',
    title: 'Strategic Filing Drafter',
    desc: 'Win on merits, delay proceedings or challenge jurisdiction — strategy drives the draft.',
  },
  {
    icon: '📖',
    title: 'Legal Process Guide',
    desc: 'Step-by-step Punjab/Haryana procedures with court fees and limitation periods.',
  },
]

// ── Card components ───────────────────────────────────────────────────────────

function LiveCardTile({ card }: { card: LiveCard }) {
  const navigate = useNavigate()
  return (
    <div
      onClick={() => card.onClick ? card.onClick() : navigate(card.to!)}
      className="bg-white border border-border-1 rounded-DEFAULT p-[15px] cursor-pointer transition-all hover:border-border-2 hover:shadow-[0_2px_12px_rgba(0,0,0,0.07)] flex flex-col gap-[9px] relative overflow-hidden group"
    >
      <div className={`absolute left-0 top-0 bottom-0 w-[3px] rounded-l-DEFAULT opacity-0 group-hover:opacity-100 transition-opacity ${card.accent}`} />
      <div className={`w-8 h-8 rounded-icon flex items-center justify-center text-[15px] flex-shrink-0 ${card.iconBg}`}>
        <span className={card.iconBg === 'bg-ink' ? 'brightness-200 text-white' : ''}>{card.icon}</span>
      </div>
      <div>
        <div className="text-[12.5px] font-bold text-text-1 leading-[1.3]">{card.title}</div>
        <div className="text-[11px] text-text-3 leading-[1.5] mt-[1px]">{card.desc}</div>
      </div>
    </div>
  )
}

function SoonCardTile({ card }: { card: SoonCard }) {
  return (
    <div className="bg-surface-2 border border-border-1 rounded-DEFAULT p-[15px] flex flex-col gap-[9px] relative overflow-hidden">
      <div className="absolute top-[10px] right-[10px]">
        <span className="text-[9px] font-bold tracking-[0.5px] uppercase text-text-3 bg-white border border-border-1 px-[7px] py-[2px] rounded-full">
          Soon
        </span>
      </div>
      <div className="w-8 h-8 rounded-icon flex items-center justify-center text-[15px] bg-surface-3 flex-shrink-0">
        {card.icon}
      </div>
      <div>
        <div className="text-[12.5px] font-bold text-text-2 leading-[1.3]">{card.title}</div>
        <div className="text-[11px] text-text-3 leading-[1.5] mt-[1px]">{card.desc}</div>
      </div>
    </div>
  )
}

// ── Case card ─────────────────────────────────────────────────────────────────

const STATUS_CLS: Record<CaseStatus, string> = {
  active: 'text-green', disposed: 'text-text-3', stayed: 'text-amber', settled: 'text-blue',
}

const MATTER_SHORT: Record<MatterType, string> = {
  bail: 'Bail', writ: 'Writ', civil: 'Civil', criminal: 'Criminal',
  cheque_bounce: 'S.138', matrimonial: 'Matrimonial',
  consumer: 'Consumer', property: 'Property', other: 'Other',
}

function daysUntil(d?: string) {
  if (!d) return null
  const diff = Math.floor((new Date(d).getTime() - Date.now()) / 86400000)
  return isNaN(diff) ? null : diff
}

function HomeCaseCard({ c }: { c: LegalCase }) {
  const navigate = useNavigate()
  const client    = c.persons.find(p => p.role === 'client')
  const paidTotal = c.payments.filter(p => p.paid).reduce((s, p) => s + p.amount, 0)
  const balance   = c.total_fees != null ? c.total_fees - paidTotal : null
  const days      = daysUntil(c.next_hearing)

  return (
    <div
      onClick={() => navigate(`/cases/${c.id}`)}
      className="bg-white border border-border-1 rounded-DEFAULT px-[13px] py-[11px] cursor-pointer hover:border-border-2 hover:shadow-[0_1px_8px_rgba(0,0,0,0.05)] transition-all flex items-center gap-[12px]"
    >
      <div className="w-[32px] h-[32px] rounded-icon bg-surface-2 border border-border-1 flex items-center justify-center text-[14px] flex-shrink-0">⚖️</div>
      <div className="flex-1 min-w-0">
        <div className="text-[12.5px] font-semibold text-text-1 truncate">{c.title}</div>
        <div className="flex items-center gap-[6px] mt-[2px] flex-wrap">
          <span className={`text-[10.5px] font-semibold ${STATUS_CLS[c.status]}`}>{MATTER_SHORT[c.matter_type]}</span>
          <span className="text-text-3 text-[9px]">·</span>
          <span className="text-[10.5px] text-text-3 truncate max-w-[160px]">{c.court}</span>
          {client && (
            <>
              <span className="text-text-3 text-[9px]">·</span>
              <span className="text-[10.5px] text-text-3">{client.name}</span>
            </>
          )}
        </div>
      </div>
      <div className="flex flex-col items-end gap-[3px] flex-shrink-0">
        {days !== null && (
          <span className={`text-[11px] font-semibold ${
            days === 0 ? 'text-red-600' : days <= 3 ? 'text-red-600' : days <= 7 ? 'text-amber' : 'text-text-3'
          }`}>
            {days === 0 ? 'Today!' : days < 0 ? 'Past' : `${days}d`}
          </span>
        )}
        {balance !== null && (
          <span className={`text-[10.5px] font-semibold ${balance <= 0 ? 'text-green' : 'text-amber'}`}>
            {balance <= 0 ? 'Paid ✓' : `₹${(balance / 1000).toFixed(0)}k due`}
          </span>
        )}
      </div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function HomePage() {
  const navigate      = useNavigate()
  const user          = useAuthStore((s) => s.user)
  const cases         = useCaseStore((s) => s.cases)
  const [showNewCase, setShowNewCase] = useState(false)

  const firstName = user?.full_name?.split(' ')[0] ?? 'Advocate'
  const today     = dayjs().format('dddd, D MMMM YYYY')
  const firmName  = user?.firm_name ?? ''
  const activeCases = cases.filter(c => c.status === 'active').slice(0, 3)

  const liveCards: LiveCard[] = [
    {
      icon: '⚖️',
      iconBg: 'bg-ink',
      accent: 'bg-ink',
      title: 'New Case',
      desc: 'Register a matter — parties, fees, hearing dates and documents.',
      onClick: () => setShowNewCase(true),
    },
    {
      icon: '📄',
      iconBg: 'bg-blue-bg',
      accent: 'bg-blue',
      title: 'PDF Extractor',
      desc: 'Extract parties, dates and amounts. Q&A any court order or contract.',
      to: '/pdf',
    },
    {
      icon: '📋',
      iconBg: 'bg-green-bg',
      accent: 'bg-green',
      title: 'Case Synopsis',
      desc: 'Upload a judgment or petition. Get parties, facts, issues, held and citations.',
      to: '/synopsis',
    },
    {
      icon: '↩',
      iconBg: 'bg-amber-bg',
      accent: 'bg-amber',
      title: 'Smart Reply',
      desc: 'Upload a legal notice. Extract allegations, set stance and draft a complete reply.',
      to: '/reply',
    },
    {
      icon: '📅',
      iconBg: 'bg-ink',
      accent: 'bg-ink',
      title: 'Deadline Tracker',
      desc: 'Track hearings and limitations. WhatsApp reminders sent directly to your clients.',
      to: '/deadlines',
    },
    {
      icon: '🔍',
      iconBg: 'bg-blue-bg',
      accent: 'bg-blue',
      title: 'Judgment Search',
      desc: 'Search SC and P&H HC judgments. Source-backed, verified citations instantly.',
      to: '/search',
    },
  ]

  return (
    <div className="max-w-[1200px]">

      {/* Greeting */}
      <p className="font-serif text-[23px] tracking-[-0.3px] text-text-1 mb-[2px]">
        Hi, <em className="not-italic text-text-2">{firstName}.</em>
      </p>
      <p className="text-[12.5px] text-text-3 mb-6">
        {today}{firmName ? ` · ${firmName}` : ''}
      </p>

      {/* ── Live tools ─────────────────────────────────────────────────────── */}
      <div className="mb-7">
        <div className="text-[10px] font-bold tracking-[0.7px] uppercase text-text-3 mb-[9px]">
          Tools
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-[9px]">
          {liveCards.map(c => <LiveCardTile key={c.title} card={c} />)}
        </div>
      </div>

      {/* ── My Cases ───────────────────────────────────────────────────────── */}
      <div className="mb-7">
        <div className="flex items-center justify-between mb-[9px]">
          <div className="text-[10px] font-bold tracking-[0.7px] uppercase text-text-3">My Cases</div>
          <button
            onClick={() => navigate('/cases')}
            className="text-[11px] font-semibold text-text-3 hover:text-text-1 transition-colors"
          >
            View all →
          </button>
        </div>

        {activeCases.length === 0 ? (
          <div
            onClick={() => setShowNewCase(true)}
            className="bg-white border border-dashed border-border-2 rounded-DEFAULT px-[14px] py-[18px] flex items-center justify-center gap-[8px] cursor-pointer hover:border-ink hover:bg-surface-2 transition-colors"
          >
            <span className="text-[12px] text-text-3">No active cases —</span>
            <span className="text-[12px] font-semibold text-ink">Register your first case →</span>
          </div>
        ) : (
          <div className="flex flex-col gap-[6px]">
            {activeCases.map(c => <HomeCaseCard key={c.id} c={c} />)}
            {cases.filter(c => c.status === 'active').length > 3 && (
              <button
                onClick={() => navigate('/cases')}
                className="text-[11.5px] font-medium text-text-3 hover:text-text-1 transition-colors text-center py-[6px]"
              >
                +{cases.filter(c => c.status === 'active').length - 3} more active cases
              </button>
            )}
          </div>
        )}
      </div>

      {/* ── Coming soon ────────────────────────────────────────────────────── */}
      <div>
        <div className="text-[10px] font-bold tracking-[0.7px] uppercase text-text-3 mb-[9px]">
          Coming Soon
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-[9px]">
          {SOON_CARDS.map(c => <SoonCardTile key={c.title} card={c} />)}
        </div>
      </div>

      <NewCaseModal
        open={showNewCase}
        onClose={() => setShowNewCase(false)}
        onCreated={(id) => { setShowNewCase(false); navigate(`/cases/${id}`) }}
      />
    </div>
  )
}
