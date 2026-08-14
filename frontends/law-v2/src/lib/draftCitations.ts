import type { PublicJudgmentResult } from '@/types'

/**
 * A judgment the lawyer has attached to a draft.
 *
 * Deliberately a narrow projection of PublicJudgmentResult: only fields that
 * end up on the page or in the .docx, so nothing speculative can leak into a
 * filing.
 */
export interface AttachedCitation {
  id: string
  case_name: string
  court: string
  year: number
  citation: string | null
  /** Authenticated API path to the certified copy. Required — see isAttachable. */
  judgment_url: string
  official_source_url?: string
}

/**
 * LINK INTEGRITY (CLAUDE.md, non-negotiable): a citation may only be put into a
 * draft when we can resolve the actual judgment PDF. A case name with no
 * retrievable copy is exactly the "plausible-looking fake" the launch-quality
 * mandate forbids — a lawyer who cites it and cannot produce it is worse off
 * than if we had shown nothing.
 */
export function isAttachable(r: PublicJudgmentResult): boolean {
  return Boolean(r.judgment_url) && r.link_status !== 'dead'
}

export function toAttached(r: PublicJudgmentResult): AttachedCitation {
  return {
    id: r.id,
    case_name: r.case_name,
    court: r.court,
    year: r.year,
    citation: r.primary_citation ?? null,
    // Guarded by isAttachable at every call site.
    judgment_url: r.judgment_url as string,
    official_source_url: r.official_source_url ?? r.source_url,
  }
}

/**
 * "Ram Singh v. State of Punjab, (2019) 3 RCR 44 (Punjab & Haryana High Court)"
 *
 * The year is dropped from the parenthetical when the reporter citation already
 * carries it — "(2019) 3 RCR 44 (P&H High Court, 2019)" reads as a mistake.
 */
export function formatCitation(c: AttachedCitation): string {
  const parts = [c.case_name]
  if (c.citation) parts.push(c.citation)

  const yearShown = Boolean(c.citation && c.year && c.citation.includes(String(c.year)))
  const where = [c.court, !yearShown && c.year ? String(c.year) : '']
    .filter(Boolean)
    .join(', ')
  if (!where) return parts.join(', ')

  // The court parenthetical follows the citation directly, with no comma —
  // standard reporting style.
  return c.citation
    ? `${parts.join(', ')} (${where})`
    : `${c.case_name}, (${where})`
}

/**
 * The "LIST OF JUDGMENTS RELIED UPON" section appended to the draft.
 *
 * A real filing carries its authorities as a numbered list, so that is what we
 * produce — rather than trying to splice case names into the model's prose,
 * which would put unreviewed text inside the legal body.
 *
 * Returns "" when nothing is attached, so the draft is unchanged until the
 * lawyer actually adds something.
 */
export function authoritiesMarkdown(citations: AttachedCitation[]): string {
  if (citations.length === 0) return ''
  const lines = citations.map((c, i) => `${i + 1}. ${formatCitation(c)}`)
  return ['', '---', '', '## LIST OF JUDGMENTS RELIED UPON', '', ...lines, ''].join('\n')
}

/**
 * Seed query for the automatic suggestions.
 *
 * The brief is the lawyer's own description of the matter, so it is the best
 * available relevance signal. The detected filing type is prepended because it
 * carries the legal frame ("Anticipatory Bail Application") that the brief may
 * only imply. Capped because the search embeds the query.
 */
export function buildSuggestionQuery(brief: string, filingType?: string): string {
  const parts = [filingType?.trim(), brief.trim()].filter(Boolean)
  return parts.join('. ').slice(0, 400)
}
