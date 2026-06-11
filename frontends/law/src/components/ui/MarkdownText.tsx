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

// Returns true if a line is a markdown table row (starts and ends with |, or just starts with |)
function isTableRow(line: string) {
  return line.trim().startsWith('|')
}

// Returns true if a line is a separator row like |---|---|
function isSeparatorRow(line: string) {
  return isTableRow(line) && /^\|[\s\-:|]+\|/.test(line.trim())
}

function parseTableRow(line: string): string[] {
  return line.trim()
    .replace(/^\|/, '').replace(/\|$/, '')
    .split('|')
    .map(cell => cell.trim())
}

function TableBlock({ rows }: { rows: string[] }) {
  const dataRows = rows.filter(r => !isSeparatorRow(r))
  if (dataRows.length === 0) return null
  const headers = parseTableRow(dataRows[0])
  const body = dataRows.slice(1)

  return (
    <div className="my-[10px] overflow-x-auto">
      <table className="w-full text-[12px] border-collapse">
        <thead>
          <tr className="bg-surface-2">
            {headers.map((h, i) => (
              <th key={i} className="text-left px-[10px] py-[7px] border border-border-1 font-semibold text-text-1 whitespace-nowrap">
                {renderInline(h)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {body.map((row, ri) => (
            <tr key={ri} className={ri % 2 === 0 ? 'bg-white' : 'bg-surface-2'}>
              {parseTableRow(row).map((cell, ci) => (
                <td key={ci} className="px-[10px] py-[7px] border border-border-1 text-text-1 leading-[1.5]">
                  {renderInline(cell)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function MarkdownText({ text, className = '', lineClassName = '' }: Props) {
  // Group lines into blocks: table blocks and non-table lines
  const lines = text.split('\n')
  const blocks: Array<{ type: 'table'; rows: string[] } | { type: 'line'; content: string; index: number }> = []

  let i = 0
  while (i < lines.length) {
    if (isTableRow(lines[i])) {
      const tableRows: string[] = []
      while (i < lines.length && isTableRow(lines[i])) {
        tableRows.push(lines[i])
        i++
      }
      blocks.push({ type: 'table', rows: tableRows })
    } else {
      blocks.push({ type: 'line', content: lines[i], index: i })
      i++
    }
  }

  return (
    <div className={`text-[12.5px] leading-[1.75] text-text-1 ${className}`}>
      {blocks.map((block, bi) => {
        if (block.type === 'table') {
          return <TableBlock key={bi} rows={block.rows} />
        }

        const { content: line, index } = block

        // Blank line → spacer
        if (!line.trim()) {
          return <div key={index} className="h-[6px]" />
        }

        // Headings
        if (line.startsWith('### ')) {
          return (
            <p key={index} className={`font-bold text-[12.5px] text-text-1 mt-[6px] ${lineClassName}`}>
              {renderInline(line.slice(4))}
            </p>
          )
        }
        if (line.startsWith('## ') || line.startsWith('# ')) {
          const level = line.startsWith('## ') ? 3 : 2
          const content = line.replace(/^#+\s/, '')
          return (
            <p key={index} className={`font-bold text-[${level === 2 ? '13' : '12.5'}px] text-text-1 mt-[8px] ${lineClassName}`}>
              {renderInline(content)}
            </p>
          )
        }

        // Normal line
        return (
          <p key={index} className={lineClassName}>
            {renderInline(line)}
          </p>
        )
      })}
    </div>
  )
}
