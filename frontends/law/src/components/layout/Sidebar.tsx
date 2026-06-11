import { NavLink, useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { useDeadlineStore } from '@/store/deadlineStore'
import { logout } from '@/api/auth'
import { toast } from '@/store/toastStore'
import dayjs from 'dayjs'

function useDeadlineBadge() {
  const deadlines = useDeadlineStore(s => s.deadlines)
  const urgent = deadlines.filter(d => {
    const diff = dayjs(d.due_date).diff(dayjs().startOf('day'), 'day')
    return diff <= 7
  })
  return urgent.length > 0 ? String(urgent.length) : undefined
}

// ── SVG icons ─────────────────────────────────────────────────────────────────

const Icons: Record<string, React.ReactNode> = {
  overview: (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-[14px] h-[14px]">
      <rect x="1.5" y="1.5" width="5.5" height="5.5" rx="1.2"/>
      <rect x="9" y="1.5" width="5.5" height="5.5" rx="1.2"/>
      <rect x="1.5" y="9" width="5.5" height="5.5" rx="1.2"/>
      <rect x="9" y="9" width="5.5" height="5.5" rx="1.2"/>
    </svg>
  ),
  cases: (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-[14px] h-[14px]">
      <path d="M2 4h12M2 7.5h9M2 11h10.5"/>
    </svg>
  ),
  draft: (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-[14px] h-[14px]">
      <path d="M3 2h6.5l3.5 3.5V14H3V2z"/>
      <path d="M9 2v4h4M5.5 8.5h5M5.5 11h3.5"/>
    </svg>
  ),
  search: (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-[14px] h-[14px]">
      <circle cx="6.5" cy="6.5" r="4"/>
      <path d="M10 10l3.5 3.5"/>
    </svg>
  ),
  pdf: (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-[14px] h-[14px]">
      <path d="M3 1.5h7l3 3V14.5H3V1.5z"/>
      <path d="M10 1.5v4h3"/>
      <circle cx="8" cy="10" r="1.5"/>
      <path d="M4.5 10h2M9.5 10h2"/>
    </svg>
  ),
  synopsis: (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-[14px] h-[14px]">
      <path d="M3 2.5h10M3 6h7M3 9.5h8M3 13h5"/>
      <path d="M13 9l1.5 1.5L13 12" strokeLinecap="round"/>
    </svg>
  ),
  reply: (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-[14px] h-[14px]">
      <path d="M5.5 4.5L2 8l3.5 3.5"/>
      <path d="M2 8h7.5a3 3 0 013 3v1"/>
    </svg>
  ),
  deadlines: (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-[14px] h-[14px]">
      <rect x="1.5" y="3" width="13" height="11.5" rx="1.5"/>
      <path d="M5 1.5v3M11 1.5v3M1.5 7.5h13"/>
    </svg>
  ),
}

// ── Nav structure ─────────────────────────────────────────────────────────────

interface NavItem {
  to: string
  iconKey: string
  label: string
  exact?: boolean
  badge?: string
}

const WORKSPACE_NAV: NavItem[] = [
  { to: '/',      iconKey: 'overview', label: 'Overview',   exact: true },
  { to: '/cases', iconKey: 'cases',    label: 'My Cases' },
]

const DO_NAV: NavItem[] = [
  { to: '/draft',    iconKey: 'draft',    label: 'Draft a Filing' },
  { to: '/search',   iconKey: 'search',   label: 'Find Judgments' },
  { to: '/pdf',      iconKey: 'pdf',      label: 'Read a Document' },
  { to: '/synopsis', iconKey: 'synopsis', label: 'Summarise Case' },
  { to: '/reply',    iconKey: 'reply',    label: 'Reply to Notice' },
]

const TRACK_NAV: NavItem[] = [
  { to: '/deadlines', iconKey: 'deadlines', label: 'Hearings & Dates' },
]

interface Props {
  open: boolean
  onClose: () => void
}

// ── Nav item component ────────────────────────────────────────────────────────

function SideNavItem({ item, onClick }: { item: NavItem; onClick: () => void }) {
  return (
    <NavLink
      to={item.to}
      end={item.exact}
      onClick={onClick}
      className={({ isActive }) =>
        [
          'relative flex items-center gap-[9px] px-[10px] py-[7px] rounded-[7px] cursor-pointer',
          'text-[12px] font-medium mb-[1px] transition-all select-none',
          isActive
            ? 'bg-gold-muted text-gold font-semibold'
            : 'text-white/50 hover:bg-white/[0.06] hover:text-white/80',
        ].join(' ')
      }
    >
      {({ isActive }) => (
        <>
          {/* Gold left border when active */}
          {isActive && (
            <span className="absolute left-0 top-[6px] bottom-[6px] w-[3px] bg-gold rounded-r-[3px]" />
          )}
          <span className={['flex-shrink-0 transition-opacity', isActive ? 'opacity-100' : 'opacity-60'].join(' ')}>
            {Icons[item.iconKey]}
          </span>
          <span className="flex-1 truncate">{item.label}</span>
          {item.badge && (
            <span className="text-[9px] font-bold bg-amber text-white px-[6px] py-[1px] rounded-full flex-shrink-0">
              {item.badge}
            </span>
          )}
        </>
      )}
    </NavLink>
  )
}

// ── Sidebar ───────────────────────────────────────────────────────────────────

export default function Sidebar({ open, onClose }: Props) {
  const { user, logout: clearAuth } = useAuthStore()
  const navigate = useNavigate()
  const deadlineBadge = useDeadlineBadge()

  const trackNav = TRACK_NAV.map(item =>
    item.to === '/deadlines' ? { ...item, badge: deadlineBadge } : item
  )

  const handleLogout = async () => {
    try { await logout() } catch { /* ignore */ }
    clearAuth()
    navigate('/login')
    toast('Logged out')
  }

  const initials = user?.initials ?? '??'
  const fullName = user?.full_name ?? 'Loading…'
  const plan = user?.plan ?? ''

  return (
    <>
      {/* Mobile overlay */}
      {open && (
        <div
          className="fixed inset-0 bg-black/50 z-[150] md:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={[
          'w-[210px] min-w-[210px] flex-shrink-0 bg-sidebar flex flex-col z-[200] h-full',
          'transition-transform duration-[250ms]',
          'fixed md:static top-0 left-0 bottom-0',
          open ? 'translate-x-0' : '-translate-x-full md:translate-x-0',
        ].join(' ')}
      >
        {/* ── Logo ── */}
        <div className="px-[16px] py-[18px] flex items-center gap-[9px] border-b border-white/[0.07]">
          <div className="w-[28px] h-[28px] bg-gold rounded-[7px] flex items-center justify-center flex-shrink-0">
            <svg viewBox="0 0 14 14" fill="none" className="w-[14px] h-[14px]">
              <rect x="2" y="1" width="8" height="11" rx="1.5" stroke="#111827" strokeWidth="1.2"/>
              <path d="M4 5h5M4 7.5h3.5M4 10h2" stroke="#111827" strokeWidth="1" strokeLinecap="round"/>
              <path d="M8 1v3h3" stroke="#111827" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <span className="font-serif text-[17px] text-white tracking-[-0.2px]">SuperAdvocate</span>
        </div>

        {/* ── Nav ── */}
        <nav className="flex-1 overflow-y-auto px-[8px] py-[10px] space-y-[18px]">

          {/* Workspace */}
          <div>
            <div className="px-[10px] mb-[4px] text-[9px] font-bold tracking-[1px] uppercase text-white/25">
              Workspace
            </div>
            {WORKSPACE_NAV.map(item => (
              <SideNavItem key={item.to} item={item} onClick={onClose} />
            ))}
          </div>

          {/* Do */}
          <div>
            <div className="px-[10px] mb-[4px] text-[9px] font-bold tracking-[1px] uppercase text-white/25">
              Do
            </div>
            {DO_NAV.map(item => (
              <SideNavItem key={item.to} item={item} onClick={onClose} />
            ))}
          </div>

          {/* Track */}
          <div>
            <div className="px-[10px] mb-[4px] text-[9px] font-bold tracking-[1px] uppercase text-white/25">
              Track
            </div>
            {trackNav.map(item => (
              <SideNavItem key={item.to} item={item} onClick={onClose} />
            ))}
          </div>

        </nav>

        {/* ── Footer ── */}
        <div className="border-t border-white/[0.07] px-[8px] pt-[10px] pb-[12px] space-y-[6px]">

          {/* AI usage */}
          <div className="px-[10px] py-[6px]">
            <div className="flex justify-between items-center mb-[5px]">
              <span className="text-[10px] font-medium text-white/35">AI Usage</span>
              <span className="text-[10px] text-white/25">68%</span>
            </div>
            <div className="h-[3px] bg-white/10 rounded-full overflow-hidden">
              <div className="h-full bg-gold rounded-full" style={{ width: '68%' }} />
            </div>
          </div>

          {/* User card */}
          <div className="flex items-center gap-[9px] px-[10px] py-[8px] rounded-[8px] hover:bg-white/[0.06] transition-colors group">
            <div className="w-[28px] h-[28px] rounded-full bg-gold flex items-center justify-center text-[10px] font-bold text-sidebar flex-shrink-0 ring-2 ring-gold/30">
              {initials}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-[12px] font-semibold text-white/85 truncate leading-tight">{fullName}</div>
              <div className="text-[10px] text-white/30 leading-tight capitalize">{plan} plan</div>
            </div>
            {/* Sign out — always visible */}
            <button
              onClick={handleLogout}
              className="flex-shrink-0 text-white/35 hover:text-white/80 transition-colors p-[4px] rounded-[5px] hover:bg-white/[0.08]"
              title="Sign out"
            >
              <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-[14px] h-[14px]">
                <path d="M6 2H3a1 1 0 00-1 1v10a1 1 0 001 1h3" strokeLinecap="round"/>
                <path d="M10.5 11l3-3-3-3" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M13.5 8H6.5" strokeLinecap="round"/>
              </svg>
            </button>
          </div>

        </div>
      </aside>
    </>
  )
}
