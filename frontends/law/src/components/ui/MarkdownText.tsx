import React from 'react'

/**
 * Lightweight markdown renderer for LLM output.
 * Handles: **bold**, *italic*, # headings, blank-line paragraph breaks.
 * No external dependency — covers everything the LLM actually produces.
 */

export function renderInline(line: string): React.ReactNode[] {
  // Split on **bold** and *italic* markers
  const parts = line.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g)
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
      return <strong key={i} className="font-semibold text-text-1">{part.slice(2, -2)}</strong>
    }
    if (part.startsWith('*') && part.endsWith('*') && part.length > 2) {
      return <em key={i}>{part.slice(1, -1)}</em>
    }
    return part
  })
}

interface Props {
  text: string
  className?: string
  lineClassName?: string
}

export default function MarkdownText({ text, className = '', lineClassName = '' }: Props) {
  const lines = text.split('\n')

  return (
    <div className={`text-[12.5px] leading-[1.75] text-text-2 ${className}`}>
      {lines.map((line, i) => {
        // Blank line → spacer
        if (!line.trim()) {
          return <div key={i} className="h-[6px]" />
        }

        // Headings
        if (line.startsWith('### ')) {
          return (
            <p key={i} className={`font-bold text-[12.5px] text-text-1 mt-[6px] ${lineClassName}`}>
              {renderInline(line.slice(4))}
            </p>
          )
        }
        if (line.startsWith('## ') || line.startsWith('# ')) {
          const level = line.startsWith('## ') ? 3 : 2
          const content = line.replace(/^#+\s/, '')
          return (
            <p key={i} className={`font-bold text-[${level === 2 ? '13' : '12.5'}px] text-text-1 mt-[8px] ${lineClassName}`}>
              {renderInline(content)}
            </p>
          )
        }

        // Normal line
        return (
          <p key={i} className={lineClassName}>
            {renderInline(line)}
          </p>
        )
      })}
    </div>
  )
}
