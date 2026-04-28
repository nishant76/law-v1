import { NavLink } from 'react-router-dom'

const ITEMS = [
  { to: '/', icon: '🏠', label: 'Home', exact: true },
  { to: '/draft', icon: '✍️', label: 'Draft' },
  { to: '/pdf', icon: '📄', label: 'PDF' },
  { to: '/deadlines', icon: '📅', label: 'Deadlines', dot: true },
]

export default function BottomNav() {
  return (
    <nav className="md:hidden h-14 flex-shrink-0 bg-white border-t border-border-1 flex">
      {ITEMS.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.exact}
          className={({ isActive }) =>
            ['flex-1 flex flex-col items-center justify-center gap-[2px] relative transition-colors',
              isActive ? 'text-text-1' : 'text-text-3',
            ].join(' ')
          }
        >
          {({ isActive }) => (
            <>
              {isActive && (
                <span className="absolute top-0 left-[20%] right-[20%] h-[2px] bg-ink rounded-b-[4px]" />
              )}
              {item.dot && (
                <span className="absolute top-[7px] right-[calc(50%-12px)] w-[6px] h-[6px] rounded-full bg-red border-2 border-white" />
              )}
              <span className="text-[17px]">{item.icon}</span>
              <span className="text-[9px] font-bold tracking-[0.3px] uppercase">{item.label}</span>
            </>
          )}
        </NavLink>
      ))}
    </nav>
  )
}
