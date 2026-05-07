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

interface NavItem {
  to: string
  icon: string
  label: string
  exact?: boolean
  badge?: string
}

const BASE_NAV: NavItem[] = [
  { to: '/',         icon: '🏠', label: 'Home',           exact: true },
  { to: '/cases',    icon: '⚖️', label: 'My Cases' },
  { to: '/draft',    icon: '✍️', label: 'Draft' },
  { to: '/search',   icon: '🔍', label: 'Search' },
  { to: '/pdf',      icon: '📄', label: 'PDF Extractor' },
  { to: '/synopsis', icon: '📋', label: 'Synopsis' },
  { to: '/reply',    icon: '📩', label: 'Reply Generator' },
  { to: '/deadlines',icon: '📅', label: 'Deadlines' },
]

interface Props {
  open: boolean
  onClose: () => void
}

export default function Sidebar({ open, onClose }: Props) {
  const { user, logout: clearAuth } = useAuthStore()
  const navigate = useNavigate()
  const deadlineBadge = useDeadlineBadge()

  const NAV = BASE_NAV.map(item =>
    item.to === '/deadlines' ? { ...item, badge: deadlineBadge } : item
  )

  const handleLogout = async () => {
    try { await logout() } catch { /* ignore */ }
    clearAuth()
    navigate('/login')
    toast('Logged out')
  }

  return (
    <>
      {/* Mobile overlay */}
      {open && (
        <div
          className="fixed inset-0 bg-black/40 z-[150] md:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={[
          'w-[216px] flex-shrink-0 bg-white border-r border-border-1 flex flex-col z-[200]',
          'transition-transform duration-[250ms]',
          'fixed md:static top-0 left-0 bottom-0',
          open ? 'translate-x-0' : '-translate-x-full md:translate-x-0',
        ].join(' ')}
      >
        {/* Logo */}
        <div className="px-[14px] py-4 border-b border-border-1 flex items-center gap-[9px]">
          <div className="w-7 h-7 bg-ink rounded-[7px] flex items-center justify-center flex-shrink-0">
            <svg viewBox="0 0 14 14" fill="none" className="w-[14px] h-[14px]">
              <rect x="2" y="1" width="8" height="11" rx="1.5" stroke="white" strokeWidth="1.2"/>
              <path d="M4 5h5M4 7.5h3.5M4 10h2" stroke="white" strokeWidth="1" strokeLinecap="round"/>
              <path d="M8 1v3h3" stroke="white" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <span className="font-serif text-[16px] tracking-[-0.2px] text-text-1">Nikhar</span>
        </div>

        {/* Profile */}
        <div className="mx-[10px] mt-[10px] mb-[6px] px-[10px] py-[9px] bg-surface-2 rounded-sm flex items-center gap-2 cursor-pointer hover:bg-surface-3 transition-colors border border-transparent">
          <div className="w-[26px] h-[26px] rounded-full bg-ink text-white flex items-center justify-center text-[9px] font-bold flex-shrink-0">
            {user?.initials ?? '??'}
          </div>
          <div>
            <div className="text-[11.5px] font-bold text-text-1 leading-tight">{user?.full_name ?? 'Loading…'}</div>
            <div className="text-[10px] text-text-3 leading-tight">{user?.plan ?? ''}</div>
          </div>
        </div>

        {/* Section label */}
        <div className="px-[14px] pt-2 pb-[3px] text-[9px] font-bold tracking-[0.8px] uppercase text-text-3">
          Workspace
        </div>

        {/* Nav */}
        <nav className="flex-1 px-2 py-[2px] overflow-y-auto">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.exact}
              onClick={onClose}
              className={({ isActive }) =>
                [
                  'flex items-center gap-[7px] px-2 py-[7px] rounded-sm cursor-pointer text-[12.5px] font-medium mb-[1px] transition-all select-none',
                  isActive
                    ? 'bg-surface-2 text-text-1 font-semibold'
                    : 'text-text-2 hover:bg-surface-2 hover:text-text-1',
                ].join(' ')
              }
            >
              {({ isActive }) => (
                <>
                  <span className={['w-[26px] h-[26px] rounded-icon flex items-center justify-center text-[13px] flex-shrink-0', isActive ? 'bg-border-1' : ''].join(' ')}>
                    {item.icon}
                  </span>
                  <span className="flex-1 truncate">{item.label}</span>
                  {item.badge && (
                    <span className="text-[9.5px] font-bold bg-ink text-white px-[7px] py-[1px] rounded-full">
                      {item.badge}
                    </span>
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Footer — AI usage meter */}
        <div className="p-[10px] border-t border-border-1">
          <div className="px-[6px] py-1">
            <div className="flex justify-between text-[10px] text-text-3 mb-1 font-medium">
              <span>AI Usage</span><span>68% used</span>
            </div>
            <div className="h-[3px] bg-surface-3 rounded-full overflow-hidden">
              <div className="h-full bg-ink rounded-full" style={{ width: '68%' }} />
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full mt-2 text-[11px] font-medium text-text-3 hover:text-text-1 transition-colors py-1 text-left px-[6px] rounded-sm hover:bg-surface-2"
          >
            Sign out
          </button>
        </div>
      </aside>
    </>
  )
}
