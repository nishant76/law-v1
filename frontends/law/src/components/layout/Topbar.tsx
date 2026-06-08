import { useLocation, useNavigate } from 'react-router-dom'

const PAGE_TITLES: Record<string, string> = {
  '/': 'Good morning',
  '/cases': 'My Cases',
  '/draft': 'Draft a Filing',
  '/search': 'Find Judgments',
  '/pdf': 'Read a Document',
  '/synopsis': 'Summarise Case',
  '/reply': 'Reply to Notice',
  '/legal-process': 'Legal Process Guide',
  '/deadlines': 'Hearings & Dates',
}

interface Props {
  onHamburger: () => void
  userName?: string
}

export default function Topbar({ onHamburger, userName }: Props) {
  const { pathname } = useLocation()
  const navigate = useNavigate()

  // strip /cases/:id suffix so /cases/* resolves to "My Cases"
  const basePath = '/' + pathname.split('/')[1]
  const title = basePath === '/' && userName
    ? `Good morning, ${userName}`
    : (PAGE_TITLES[basePath] ?? 'Nikhar')

  return (
    <header className="h-[48px] flex-shrink-0 bg-paper border-b border-border-1 flex items-center px-5 gap-[10px]">
      {/* Mobile hamburger */}
      <button
        onClick={onHamburger}
        className="md:hidden w-[30px] h-[30px] border border-border-1 rounded-sm bg-transparent flex items-center justify-center text-[15px] text-text-2 flex-shrink-0"
      >
        ☰
      </button>

      <div className="font-serif text-[14px] tracking-[-0.1px] text-text-1 flex-1">{title}</div>

      <div className="flex gap-[7px]">
        {basePath === '/' && (
          <button
            onClick={() => navigate('/draft')}
            className="text-[11.5px] font-semibold px-[12px] py-[5px] rounded-sm bg-ink text-white hover:bg-[#2e2b27] transition-colors whitespace-nowrap"
          >
            + New Draft
          </button>
        )}
        {basePath === '/deadlines' && (
          <button className="text-[11.5px] font-semibold px-[12px] py-[5px] rounded-sm bg-ink text-white hover:bg-[#2e2b27] transition-colors whitespace-nowrap">
            + Add
          </button>
        )}
      </div>
    </header>
  )
}
