import type { ButtonHTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'primary' | 'ghost'
  size?: 'sm' | 'md' | 'lg'
}

export default function Button({ variant = 'default', size = 'md', className, children, ...props }: Props) {
  return (
    <button
      className={cn(
        'font-sans font-semibold rounded-sm cursor-pointer transition-all border whitespace-nowrap inline-flex items-center gap-[5px] disabled:opacity-50 disabled:cursor-not-allowed',
        size === 'sm' && 'text-[10px] px-[9px] py-1',
        size === 'md' && 'text-[12px] px-[13px] py-[6px]',
        size === 'lg' && 'text-[13px] px-4 py-[10px] rounded-DEFAULT justify-center w-full',
        variant === 'default' && 'bg-white text-text-2 border-border-2 hover:bg-surface-2 hover:text-text-1',
        variant === 'primary' && 'bg-ink text-white border-ink hover:bg-[#2e2b27]',
        variant === 'ghost' && 'bg-transparent text-text-2 border-transparent hover:bg-surface-2 hover:text-text-1',
        className
      )}
      {...props}
    >
      {children}
    </button>
  )
}
