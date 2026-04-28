import { cn } from '@/lib/utils'

type Variant = 'green' | 'amber' | 'red' | 'blue' | 'neutral'

const styles: Record<Variant, string> = {
  green: 'bg-green-bg text-green border border-green/15',
  amber: 'bg-amber-bg text-amber border border-amber/15',
  red: 'bg-red-bg text-red border border-red/15',
  blue: 'bg-blue-bg text-blue border border-blue/15',
  neutral: 'bg-surface-3 text-text-2 border border-border-1',
}

interface Props {
  variant?: Variant
  children: React.ReactNode
  className?: string
}

export default function Tag({ variant = 'neutral', children, className }: Props) {
  return (
    <span className={cn('text-[10px] font-bold px-2 py-[2px] rounded-full flex-shrink-0', styles[variant], className)}>
      {children}
    </span>
  )
}
