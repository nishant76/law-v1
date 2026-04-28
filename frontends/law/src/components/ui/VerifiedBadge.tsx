import { cn } from '@/lib/utils'

type Status = 'verified' | 'unverified' | 'fabricated'

const config = {
  verified: { cls: 'bg-green-bg text-green border-green/20', label: '✓ Verified' },
  unverified: { cls: 'bg-amber-bg text-amber border-amber/20', label: '⚠ Verify before filing' },
  fabricated: { cls: 'bg-red-bg text-red border-red/20', label: '✗ Fabricated' },
}

interface Props {
  status: Status
  source?: string
  className?: string
}

export default function VerifiedBadge({ status, source, className }: Props) {
  const { cls, label } = config[status]
  return (
    <span className={cn('text-[9.5px] font-bold px-[6px] py-[1px] rounded-[4px] border', cls, className)}>
      {label}{source ? ` — ${source}` : ''}
    </span>
  )
}
