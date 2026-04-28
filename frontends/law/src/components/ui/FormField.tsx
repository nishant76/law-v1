import type { InputHTMLAttributes, TextareaHTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

const inputCls = 'w-full px-[10px] py-[7px] border border-border-1 rounded-sm bg-surface-2 text-text-1 font-sans text-[12.5px] outline-none resize-none transition-all mb-[11px] focus:border-border-2 focus:bg-white'

interface LabelProps { label: string; className?: string }

export function FieldLabel({ label, className }: LabelProps) {
  return (
    <label className={cn('block text-[10px] font-bold tracking-[0.5px] uppercase text-text-3 mb-1', className)}>
      {label}
    </label>
  )
}

interface InputProps extends InputHTMLAttributes<HTMLInputElement> { label?: string }

export function Input({ label, className, ...props }: InputProps) {
  return (
    <div>
      {label && <FieldLabel label={label} />}
      <input className={cn(inputCls, className)} {...props} />
    </div>
  )
}

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> { label?: string; minRows?: number }

export function Textarea({ label, className, minRows = 4, ...props }: TextareaProps) {
  return (
    <div>
      {label && <FieldLabel label={label} />}
      <textarea
        rows={minRows}
        className={cn(inputCls, 'leading-[1.6]', className)}
        {...props}
      />
    </div>
  )
}
