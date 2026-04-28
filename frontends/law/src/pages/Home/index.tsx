import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import Tag from '@/components/ui/Tag'
import dayjs from 'dayjs'

interface ActionCard {
  icon: string
  iconBg: string
  accent: string
  title: string
  desc: string
  to: string
}

const DRAFT_CARDS: ActionCard[] = [
  { icon: '✦', iconBg: 'bg-ink', accent: 'bg-ink', title: 'AI Legal Drafting', desc: 'Draft bail applications, writs and notices with research side by side.', to: '/draft' },
  { icon: '⚔️', iconBg: 'bg-blue-bg', accent: 'bg-blue', title: 'Arguments Generator', desc: 'Get arguments and counter-arguments based on the facts of your case.', to: '/draft' },
  { icon: '🔍', iconBg: 'bg-green-bg', accent: 'bg-green', title: 'Review Your Draft', desc: 'Upload a completed draft and get compliance checks and issue spotting.', to: '/pdf' },
  { icon: '📤', iconBg: 'bg-amber-bg', accent: 'bg-amber', title: 'Upload Your Draft', desc: 'Upload an existing draft and continue editing with AI research alongside.', to: '/pdf' },
]

const RESEARCH_CARDS: ActionCard[] = [
  { icon: '⚖️', iconBg: 'bg-blue-bg', accent: 'bg-blue', title: 'Judgment Search', desc: 'Search SC and P&H HC judgments. Source-backed, verified citations.', to: '/search' },
  { icon: '💬', iconBg: 'bg-green-bg', accent: 'bg-green', title: 'Chat with PDF', desc: 'Upload any court order or contract. Ask questions, extract key dates and facts.', to: '/pdf' },
  { icon: '📊', iconBg: 'bg-amber-bg', accent: 'bg-amber', title: 'Extract Key Points', desc: 'Auto-extract parties, amounts, dates and conditions from any document.', to: '/pdf' },
  { icon: '⏰', iconBg: 'bg-ink', accent: 'bg-ink', title: 'Deadline Tracker', desc: 'Track hearings and limitations. WhatsApp reminders to your clients.', to: '/deadlines' },
]

const RECENT = [
  { icon: '⚖️', title: 'Gurnam Singh v. State of Punjab — Anticipatory Bail NDPS S.21', meta: 'AI Legal Drafting · 2 hours ago', tag: { label: 'Draft', variant: 'amber' as const }, to: '/draft' },
  { icon: '📋', title: 'Kapoor_Lease_Agreement.pdf — 9 fields extracted', meta: 'PDF Extractor · Yesterday', tag: { label: 'Extracted', variant: 'blue' as const }, to: '/pdf' },
  { icon: '📜', title: 'Sharma v. Municipal Corporation — Writ Petition Art. 226', meta: 'AI Legal Drafting · 2 days ago', tag: { label: 'Complete', variant: 'green' as const }, to: '/draft' },
]

function ActionCard({ card }: { card: ActionCard }) {
  const navigate = useNavigate()
  return (
    <div
      onClick={() => navigate(card.to)}
      className="bg-white border border-border-1 rounded-DEFAULT p-[15px] cursor-pointer transition-all hover:border-border-2 hover:shadow-[0_2px_12px_rgba(0,0,0,0.07)] flex flex-col gap-[9px] relative overflow-hidden group"
    >
      <div className={`absolute left-0 top-0 bottom-0 w-[3px] rounded-l-DEFAULT opacity-0 group-hover:opacity-100 transition-opacity ${card.accent}`} />
      <div className={`w-8 h-8 rounded-icon flex items-center justify-center text-[15px] flex-shrink-0 ${card.iconBg}`}>
        <span className={card.iconBg === 'bg-ink' ? 'text-white' : ''}>{card.icon}</span>
      </div>
      <div>
        <div className="text-[12.5px] font-bold text-text-1 leading-[1.3]">{card.title}</div>
        <div className="text-[11px] text-text-3 leading-[1.5] mt-[-1px]">{card.desc}</div>
      </div>
    </div>
  )
}

export default function HomePage() {
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const firstName = user?.full_name?.split(' ')[0] ?? 'Advocate'
  const today = dayjs().format('dddd, D MMMM YYYY')
  const firmName = user ? `${user.firm_name ?? 'Your Firm'}` : ''

  return (
    <div className="max-w-[1200px]">
      <p className="font-serif text-[23px] tracking-[-0.3px] text-text-1 mb-[2px]">
        Hi, <em className="not-italic text-text-2">{firstName}.</em>
      </p>
      <p className="text-[12.5px] text-text-3 mb-6">
        {today}{firmName ? ` · ${firmName}` : ''}
      </p>

      {/* Draft section */}
      <div className="mb-6">
        <div className="text-[10px] font-bold tracking-[0.7px] uppercase text-text-3 mb-[9px]">Draft</div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-[9px]">
          {DRAFT_CARDS.map((c) => <ActionCard key={c.title} card={c} />)}
        </div>
      </div>

      {/* Research section */}
      <div className="mb-6">
        <div className="text-[10px] font-bold tracking-[0.7px] uppercase text-text-3 mb-[9px]">Research & Documents</div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-[9px]">
          {RESEARCH_CARDS.map((c) => <ActionCard key={c.title} card={c} />)}
        </div>
      </div>

      {/* Recent sessions */}
      <div>
        <div className="text-[10px] font-bold tracking-[0.7px] uppercase text-text-3 mb-[9px]">Recent Sessions</div>
        <div className="flex flex-col gap-[6px]">
          {RECENT.map((item) => (
            <div
              key={item.title}
              onClick={() => navigate(item.to)}
              className="bg-white border border-border-1 rounded-DEFAULT px-[14px] py-[11px] flex items-center gap-[11px] cursor-pointer transition-all hover:border-border-2 hover:shadow-[0_1px_8px_rgba(0,0,0,0.05)]"
            >
              <div className="w-[30px] h-[30px] rounded-[7px] bg-surface-2 border border-border-1 flex items-center justify-center text-[13px] flex-shrink-0">
                {item.icon}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-[12.5px] font-semibold text-text-1 truncate">{item.title}</div>
                <div className="text-[11px] text-text-3 mt-[1px]">{item.meta}</div>
              </div>
              <Tag variant={item.tag.variant}>{item.tag.label}</Tag>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
