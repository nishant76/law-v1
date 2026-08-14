import { useCallback, useEffect, useRef, useState } from "react";
import { BookOpen, Check, ExternalLink, Loader2, Plus, RefreshCw, Search, X } from "lucide-react";

import { unifiedSearch, openJudgmentPdf } from "@/api/search";
import type { PublicJudgmentResult } from "@/types";
import { CitationSearchModal } from "./CitationSearchModal";
import {
  buildSuggestionQuery,
  isAttachable,
  toAttached,
  type AttachedCitation,
} from "@/lib/draftCitations";

const MAX_SUGGESTIONS = 5;

/**
 * Right-hand citations pane for a generated draft.
 *
 * Two ways in:
 *   1. Suggestions — searched automatically from the lawyer's own brief as soon
 *      as the draft exists, each addable in one click.
 *   2. The search box — a button that opens the full search modal (it is not a
 *      live input; a 25s judgment search does not belong on a keystroke).
 *
 * Attached judgments become a "LIST OF JUDGMENTS RELIED UPON" section in the
 * draft and the exported .docx.
 */
export function DraftCitationsPanel({
  brief,
  filingType,
  attached,
  onAdd,
  onRemove,
}: {
  brief: string;
  filingType?: string;
  attached: AttachedCitation[];
  onAdd: (c: AttachedCitation) => void;
  onRemove: (id: string) => void;
}) {
  const [suggestions, setSuggestions] = useState<PublicJudgmentResult[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);

  // Stale-response guard; no useMutation (CLAUDE.md, GAP-050).
  const runIdRef = useRef(0);

  const loadSuggestions = useCallback(async () => {
    const q = buildSuggestionQuery(brief, filingType);
    if (q.length < 15) return;
    const thisId = ++runIdRef.current;
    setLoading(true);
    setFailed(false);
    try {
      const res = await unifiedSearch(q, 12);
      if (thisId !== runIdRef.current) return;
      setSuggestions(res.data.from_public_judgments ?? []);
    } catch {
      if (thisId !== runIdRef.current) return;
      // Suggestions are an assist, not the feature. A failure leaves the manual
      // search fully usable rather than blocking the draft.
      setFailed(true);
    } finally {
      if (thisId === runIdRef.current) setLoading(false);
    }
  }, [brief, filingType]);

  useEffect(() => {
    void loadSuggestions();
  }, [loadSuggestions]);

  const attachedIds = new Set(attached.map((c) => c.id));
  // Only offer what can actually be cited, and never re-offer what is already in.
  const offerable = (suggestions ?? [])
    .filter((r) => isAttachable(r) && !attachedIds.has(r.id))
    .slice(0, MAX_SUGGESTIONS);

  return (
    <div className="hairline rounded-lg bg-card p-4">
      <div className="flex items-center justify-between">
        <div className="eyebrow">Authorities</div>
        {suggestions !== null && (
          <button
            onClick={() => void loadSuggestions()}
            disabled={loading}
            title="Refresh suggestions"
            className="rounded p-1 text-muted-foreground hover:bg-muted disabled:opacity-40"
          >
            <RefreshCw className={`h-3 w-3 ${loading ? "animate-spin" : ""}`} />
          </button>
        )}
      </div>

      {/* Search box — a button, so a click opens the modal */}
      <button
        onClick={() => setModalOpen(true)}
        className="hairline mt-3 flex h-9 w-full items-center gap-2 rounded-md bg-background px-3 text-left text-sm text-muted-foreground hover:bg-sand/60"
      >
        <Search className="h-3.5 w-3.5 shrink-0" />
        Search judgments…
      </button>

      {/* ── Attached ────────────────────────────────────────────────── */}
      {attached.length > 0 && (
        <div className="mt-4">
          <div className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
            In this draft ({attached.length})
          </div>
          <ul className="space-y-2">
            {attached.map((c) => (
              <li key={c.id} className="rounded-md bg-sand/60 p-2.5">
                <div className="flex items-start gap-2">
                  <div className="min-w-0 flex-1">
                    <div className="text-xs font-medium leading-snug">{c.case_name}</div>
                    <div className="mt-0.5 text-[11px] text-muted-foreground">
                      {c.citation ? `${c.citation} · ` : ""}
                      {c.court}, {c.year}
                    </div>
                  </div>
                  <button
                    onClick={() => onRemove(c.id)}
                    aria-label={`Remove ${c.case_name}`}
                    className="rounded p-0.5 text-muted-foreground hover:bg-muted"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
                <button
                  onClick={() => void openJudgmentPdf(c.judgment_url)}
                  className="mt-1.5 inline-flex items-center gap-1 text-[11px] text-amber-accent hover:underline"
                >
                  <ExternalLink className="h-3 w-3" /> View judgment
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ── Suggested ───────────────────────────────────────────────── */}
      <div className="mt-4 border-t border-border pt-3">
        <div className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
          Suggested for this matter
        </div>

        {loading && suggestions === null ? (
          <div className="flex items-center gap-2 py-4 text-[11px] text-muted-foreground">
            <Loader2 className="h-3 w-3 animate-spin" /> Finding relevant judgments…
          </div>
        ) : failed ? (
          <p className="py-3 text-[11px] text-muted-foreground">
            Couldn't load suggestions.{" "}
            <button onClick={() => void loadSuggestions()} className="underline">
              Retry
            </button>{" "}
            or search manually above.
          </p>
        ) : offerable.length === 0 ? (
          <p className="py-3 text-[11px] text-muted-foreground">
            {suggestions === null
              ? "Add more detail to your brief to get suggestions."
              : attached.length > 0
                ? "No further suggestions — search above for more."
                : "No verified judgments matched this brief. Search above with the section or legal question."}
          </p>
        ) : (
          <ul className="space-y-2">
            {offerable.map((r) => (
              <li key={r.id} className="rounded-md border border-border p-2.5">
                <div className="flex items-start gap-1.5">
                  <BookOpen className="mt-0.5 h-3 w-3 shrink-0 text-amber-accent" />
                  <div className="min-w-0 flex-1">
                    <div className="text-xs font-medium leading-snug">{r.case_name}</div>
                    <div className="mt-0.5 text-[11px] text-muted-foreground">
                      {r.primary_citation ? `${r.primary_citation} · ` : ""}
                      {r.court}, {r.year}
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => onAdd(toAttached(r))}
                  className="mt-2 inline-flex h-7 w-full items-center justify-center gap-1.5 rounded-md bg-amber-accent text-[11px] font-medium text-amber-accent-fg hover:opacity-90"
                >
                  <Plus className="h-3 w-3" /> Add to draft
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {attached.length > 0 && (
        <p className="mt-3 flex items-start gap-1.5 text-[10px] leading-relaxed text-muted-foreground">
          <Check className="mt-0.5 h-3 w-3 shrink-0 text-emerald-600" />
          Attached judgments appear as "List of Judgments Relied Upon" in the draft
          and the exported .docx.
        </p>
      )}

      <CitationSearchModal
        open={modalOpen}
        initialQuery={buildSuggestionQuery(brief, filingType).slice(0, 120)}
        attached={attached}
        onAdd={onAdd}
        onRemove={onRemove}
        onClose={() => setModalOpen(false)}
      />
    </div>
  );
}
