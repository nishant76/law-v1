import { useLocation, useNavigate } from 'react-router-dom'

const PAGE_TITLES: Record<string, string> = {
  '/': 'Good morning',
  '/draft': 'Draft a Filing',
  '/search': 'Judgment Search',
  '/pdf': 'PDF Extractor',
  '/synopsis': 'Case Synopsis',
  '/reply': 'Reply Generator',
  '/legal-process': 'Legal Process Guide',
  '/deadlines': 'Deadline Tracker',
}

const PAGE_ACTIONS: Record<string, React.ReactNode> = {}

interface Props {
  onHamburger: () => void
  userName?: string
}

export default function Topbar({ onHamburger, userName }: Props) {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const title = pathname === '/' && userName
    ? `Good morning, ${userName}`
    : (PAGE_TITLES[pathname] ?? 'Nikhar')

  return (
    <header className="h-[50px] flex-shrink-0 bg-white border-b border-border-1 flex items-center px-5 gap-[10px]">
      <button
        onClick={onHamburger}
        className="md:hidden w-[30px] h-[30px] border border-border-1 rounded-sm bg-transparent flex items-center justify-center text-[15px] text-text-2 flex-shrink-0"
      >
        ☰
      </button>

      <div className="font-serif text-[15px] tracking-[-0.1px] text-text-1 flex-1">
        {title}
      </div>

      <div className="flex gap-[7px]">
        {pathname === '/' && (
          <button
            onClick={() => navigate('/draft')}
            className="text-[12px] font-semibold px-[13px] py-[6px] rounded-sm bg-ink text-white border border-ink hover:bg-[#2e2b27] transition-colors whitespace-nowrap flex items-center gap-[5px]"
          >
            + New Draft
          </button>
        )}
        {pathname === '/deadlines' && (
          <button className="text-[12px] font-semibold px-[13px] py-[6px] rounded-sm bg-ink text-white border border-ink hover:bg-[#2e2b27] transition-colors whitespace-nowrap">
            + Add
          </button>
        )}
        {PAGE_ACTIONS[pathname]}
      </div>
    </header>
  )
}
