import { useRef } from 'react'
import { cn } from '@/lib/utils'

interface Props {
  onFile: (file: File) => void
  accept?: string
  children?: React.ReactNode
  className?: string
}

export default function DropZone({ onFile, accept = '.pdf,.docx,.doc,.jpg,.jpeg,.png', children, className }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (file) onFile(file)
  }

  return (
    <div
      onDrop={handleDrop}
      onDragOver={(e) => e.preventDefault()}
      onClick={() => inputRef.current?.click()}
      className={cn(
        'border-2 border-dashed border-border-1 rounded-DEFAULT p-11 text-center cursor-pointer bg-surface-2 hover:border-border-2 hover:bg-surface-3 transition-all flex flex-col items-center gap-[9px]',
        className
      )}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f) }}
      />
      {children ?? (
        <>
          <span className="text-[30px] opacity-55">📤</span>
          <span className="font-serif text-[15px] text-text-1">Drop your document here</span>
          <span className="text-[11.5px] text-text-3 max-w-[180px]">PDF or Word · up to 50MB</span>
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); inputRef.current?.click() }}
            className="mt-1 text-[12px] font-semibold px-[13px] py-[6px] rounded-sm bg-ink text-white border border-ink hover:bg-[#2e2b27] transition-colors"
          >
            Browse files
          </button>
        </>
      )}
    </div>
  )
}
