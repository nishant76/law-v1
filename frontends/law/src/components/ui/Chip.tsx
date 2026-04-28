import { cn } from '@/lib/utils'

interface Props {
  selected?: boolean
  onClick?: () => void
  children: React.ReactNode
  className?: string
}

export default function Chip({ selected, onClick, children, className }: Props) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'text-[11px] font-semibold px-[10px] py-1 rounded-full border cursor-pointer transition-all',
        selected
          ? 'bg-ink text-white border-ink'
          : 'bg-surface-2 text-text-2 border-border-1 hover:bg-ink hover:text-white hover:border-ink',
        className
      )}
    >
      {children}
    </button>
  )
}
