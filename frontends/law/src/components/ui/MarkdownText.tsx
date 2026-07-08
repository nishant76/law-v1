import React, { useState } from 'react'

/**
 * Lightweight markdown renderer for LLM output.
 * Handles: **bold**, *italic*, # headings, blockquotes, tables, bullet lists.
 * Special: ## Authorities section is collapsible.
 */

export function renderInline(line: string): React.ReactNode[] {
  // ⟦Label⟧ = an unfilled template key-detail blank → render as a highlighted chip.
  const parts = line.split(/(\*\*[^*]+\*\*|\*[^*]+\*|⟦[^⟧]+⟧)/g)
  return parts.map((part, i) => {
    if (part.startsWith('⟦') && part.endsWith('⟧') && part.length > 2) {
      return (
        <span
          key={i}
          className="inline-flex items-center px-[6px] py-[1px] mx-[1px] rounded-[4px] bg-gold-muted text-ink text-[0.92em] font-semibold border border-gold/40 align-baseline"
        >
          {part.slice(1, -1)}
        </span>
      )
    }
    if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
      return <strong key={i} className="font-semibold text-text-1">{part.slice(2, -2)}</strong>
    }
    if (part.startsWith('*') && part.endsWith('*') && part.length > 2) {
      return <em key={i}>{part.slice(1, -1)}</em>
    }
    return part
  })
}

// Icons for known ## section headings
const SECTION_ICONS: Record<string, string> = {
  'result':                   '⚖',
  'core issue':               '🔍',
  'key facts':                '📋',
  "court's reasoning":        '🧠',
  'authorities relied upon':  '📚',
  'judgements relied upon':   '📚',
  'what this case means':     '💡',
  'operative directions':     '📌',
  'deadlines':                '📅',
  'immediate next steps':     '▶',
  'executive brief':          '📄',
  'detailed analysis':        '🔬',
}

function headingIcon(text: string): string {
  const lc = text.toLowerCase()
  for (const [key, icon] of Object.entries(SECTION_ICONS)) {
    if (lc.includes(key)) return icon
  }
  return ''
}

// ── Table ──────────────────────────────────────────────────────────────────────

function isTableRow(line: string) { return line.trim().startsWith('|') }
function isSeparatorRow(line: string) { return isTableRow(line) && /^\|[\s\-:|]+\|/.test(line.trim()) }

function parseTableRow(line: string): string[] {
  return line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map(c => c.trim())
}

function TableBlock({ rows }: { rows: string[] }) {
  const dataRows = rows.filter(r => !isSeparatorRow(r))
  if (!dataRows.length) return null
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

// ── Collapsible Authorities ────────────────────────────────────────────────────

interface Authority { header: string; details: string[] }

function parseAuthorities(lines: string[]): Authority[] {
  const result: Authority[] = []
  let cur: Authority | null = null

  for (const raw of lines) {
    const line = raw.trim()
    if (!line) { if (cur) { result.push(cur); cur = null } continue }
    if (!line.startsWith('-') && !line.startsWith('*')) continue
    const content = line.replace(/^[-*]\s+/, '').trim()
    // A new authority starts when the bullet begins with bold text (case name)
    // or when there is no current entry yet.
    const isCaseName = content.startsWith('**') || !cur
    if (isCaseName) {
      if (cur) result.push(cur)
      cur = { header: content, details: [] }
    } else {
      cur!.details.push(content)
    }
  }
  if (cur) result.push(cur)
  return result
}

function AuthoritiesBlock({ lines }: { lines: string[] }) {
  const authorities = parseAuthorities(lines)
  const [openIdx, setOpenIdx] = useState<number | null>(null)

  if (!authorities.length) return null

  return (
    <div className="space-y-[4px]">
      {authorities.map((auth, i) => {
        const isOpen = openIdx === i
        const hasDetails = auth.details.length > 0

        // No sub-details (e.g. the model emitted the judgement as a single line):
        // render a plain, non-collapsible row so the expand arrow never reveals
        // an empty panel.
        if (!hasDetails) {
          return (
            <div key={i} className="border border-border-1 rounded-sm px-[12px] py-[8px] bg-surface-2">
              <span className="text-[12px] font-medium text-text-1 leading-[1.4]">
                {renderInline(auth.header)}
              </span>
            </div>
          )
        }

        return (
          <div key={i} className="border border-border-1 rounded-sm overflow-hidden">
            <button
              onClick={() => setOpenIdx(isOpen ? null : i)}
              className="w-full flex items-center gap-[8px] px-[12px] py-[8px] bg-surface-2 hover:bg-surface-3 transition-colors text-left"
            >
              <span className="text-[10px] text-text-3 flex-shrink-0 transition-transform" style={{ transform: isOpen ? 'rotate(90deg)' : 'none' }}>▶</span>
              <span className="text-[12px] font-medium text-text-1 leading-[1.4] flex-1 min-w-0">
                {renderInline(auth.header)}
              </span>
            </button>
            {isOpen && (
              <div className="px-[12px] py-[10px] border-t border-border-1 space-y-[6px] bg-white">
                {auth.details.map((d, di) => (
                  <p key={di} className="text-[12px] text-text-2 leading-[1.55]">
                    {renderInline(d)}
                  </p>
                ))}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

// ── Block grouping types ────────────────────────────────────────────────────────

type Block =
  | { type: 'table'; rows: string[] }
  | { type: 'authorities'; headingText: string; lines: string[] }
  | { type: 'line'; content: string; index: number }

interface Props {
  text: string
  className?: string
  lineClassName?: string
}

// Drop any "## " section whose body (up to the next "## "/"# " heading) has no real
// content — only blank lines or placeholder phrases. Guarantees an unavailable
// section is never shown as a bare heading or a "Not specified" stub.
const PLACEHOLDER_RE = /^(not specified.*|not applicable\.?|n\/?a|none\.?)$/i

function isEmptyOrPlaceholder(line: string): boolean {
  const t = line.replace(/^[>\s]*[-*]?\s*/, '').replace(/\*\*/g, '').trim()
  if (!t) return true
  return PLACEHOLDER_RE.test(t)
}

function stripEmptySections(text: string): string {
  const lines = text.split('\n')
  const keep = new Array<boolean>(lines.length).fill(true)
  for (let i = 0; i < lines.length; i++) {
    if (!lines[i].startsWith('## ')) continue
    let j = i + 1
    let hasContent = false
    for (; j < lines.length; j++) {
      const l = lines[j]
      if (l.startsWith('## ') || l.startsWith('# ')) break
      if (!isEmptyOrPlaceholder(l)) hasContent = true
    }
    if (!hasContent) {
      for (let k = i; k < j; k++) keep[k] = false
    }
  }
  return lines.filter((_, idx) => keep[idx]).join('\n')
}

export default function MarkdownText({ text, className = '', lineClassName = '' }: Props) {
  const lines = stripEmptySections(text).split('\n')
  const blocks: Block[] = []

  let i = 0
  while (i < lines.length) {
    const line = lines[i]

    // Table block
    if (isTableRow(line)) {
      const rows: string[] = []
      while (i < lines.length && isTableRow(lines[i])) { rows.push(lines[i]); i++ }
      blocks.push({ type: 'table', rows })
      continue
    }

    // Authorities section — collect until next ## heading
    const headingText = line.startsWith('## ') ? line.slice(3).trim()
      : line.startsWith('### ') ? line.slice(4).trim() : null
    if (headingText && (headingText.toLowerCase().includes('authorities relied upon') || headingText.toLowerCase().includes('judgements relied upon'))) {
      const authLines: string[] = []
      i++
      while (i < lines.length) {
        const next = lines[i]
        if (next.startsWith('## ') || next.startsWith('# ')) break
        authLines.push(next)
        i++
      }
      blocks.push({ type: 'authorities', headingText, lines: authLines })
      continue
    }

    blocks.push({ type: 'line', content: line, index: i })
    i++
  }

  return (
    <div className={`text-[12.5px] leading-[1.75] text-text-1 ${className}`}>
      {blocks.map((block, bi) => {
        if (block.type === 'table') {
          return <TableBlock key={bi} rows={block.rows} />
        }

        if (block.type === 'authorities') {
          const count = parseAuthorities(block.lines).length
          const icon = headingIcon(block.headingText)
          return (
            <div key={bi} className="mt-[14px] mb-[8px]">
              <div className="flex items-center gap-[6px] mb-[8px]">
                {icon && <span className="text-[13px]">{icon}</span>}
                <span className="font-bold text-[13px] text-text-1">{block.headingText}</span>
                {count > 0 && (
                  <span className="text-[10px] font-semibold text-text-3 bg-surface-3 px-[6px] py-[1px] rounded-[4px]">
                    {count}
                  </span>
                )}
              </div>
              <AuthoritiesBlock lines={block.lines} />
            </div>
          )
        }

        const { content: line, index } = block

        if (!line.trim()) return <div key={index} className="h-[6px]" />

        if (line.startsWith('### ')) {
          const txt = line.slice(4)
          const icon = headingIcon(txt)
          return (
            <p key={index} className={`font-bold text-[12.5px] text-text-1 mt-[6px] flex items-center gap-[5px] ${lineClassName}`}>
              {icon && <span>{icon}</span>}
              {renderInline(txt)}
            </p>
          )
        }

        if (line.startsWith('## ') || line.startsWith('# ')) {
          const txt = line.replace(/^#+\s/, '')
          const icon = headingIcon(txt)
          const isH1 = line.startsWith('# ')
          return (
            <p key={index} className={`font-bold text-[${isH1 ? '14' : '13'}px] text-text-1 mt-[14px] mb-[2px] flex items-center gap-[6px] ${lineClassName}`}>
              {icon && <span className="text-[13px]">{icon}</span>}
              {renderInline(txt)}
            </p>
          )
        }

        // Empty blockquote line (">" or "> ") — some models emit one between
        // the two blockquotes. Skip it so it never renders as an empty box.
        if (line.trim() === '>' || line.trim() === '> ') {
          return <div key={index} className="h-[2px]" />
        }

        // Blockquote — colour-coded by type
        if (line.startsWith('> ')) {
          const content = line.slice(2)
          const lc = content.toLowerCase()
          const isWinning  = lc.includes('winning argument')
          const isTakeaway = lc.includes('key takeaway')
          const borderCls  = isWinning  ? 'border-amber'
                           : isTakeaway ? 'border-green'
                           : 'border-gold'
          const bgCls      = isWinning  ? 'bg-amber-bg'
                           : isTakeaway ? 'bg-green-bg'
                           : 'bg-gold-muted'
          const icon       = isWinning  ? '🏆 ' : isTakeaway ? '💡 ' : ''
          return (
            <div key={index} className={`border-l-[3px] ${borderCls} pl-[12px] py-[6px] my-[8px] ${bgCls} rounded-r-sm`}>
              <p className={`text-[12.5px] text-text-1 leading-[1.6] ${lineClassName}`}>
                {icon}{renderInline(content)}
              </p>
            </div>
          )
        }

        return (
          <p key={index} className={lineClassName}>
            {renderInline(line)}
          </p>
        )
      })}
    </div>
  )
}
