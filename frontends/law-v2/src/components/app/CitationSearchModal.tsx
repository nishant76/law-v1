import { useEffect, useRef, useState } from "react";
import { AlertTriangle, BookOpen, Check, Loader2, Plus, Search, X } from "lucide-react";

import { unifiedSearch } from "@/api/search";
import type { PublicJudgmentResult } from "@/types";
import {
  isAttachable,
  toAttached,
  type AttachedCitation,
} from "@/lib/draftCitations";

/**
 * Full search over public judgments, for attaching authorities to a draft.
 *
 * Opened from the draft's citations panel. Results are the same verified corpus
 * the Find Judgments page uses — a judgment with no retrievable certified copy
 * is listed but NOT addable, with the reason shown, rather than quietly hidden
 * or silently offered.
 */
export function CitationSearchModal({
  open,
  initialQuery,
  attached,
  onAdd,
  onRemove,
  onClose,
}: {
  open: boolean;
  initialQuery: string;
  attached: AttachedCitation[];
  onAdd: (c: AttachedCitation) => void;
  onRemove: (id: string) => void;
  onClose: () => void;
}) {
  const [query, setQuery] = useState(initialQuery);
  const [results, setResults] = useState<PublicJudgmentResult[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Plain async/await + a stale-response guard, never useMutation: TanStack
  // Query v5's AbortController cancels in-flight search in React Strict Mode
  // dev (CLAUDE.md, GAP-050).
  const searchIdRef = useRef(0);

  useEffect(() => {
    if (open) {
      setQuery(initialQuery);
      // Defer focus until the dialog has painted.
      const t = setTimeout(() => inputRef.current?.focus(), 40);
      return () => clearTimeout(t);
    }
  }, [open, initialQuery]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  const runSearch = async () => {
    const q = query.trim();
    if (!q || searching) return;
    const thisId = ++searchIdRef.current;
    setSearching(true);
    setError(null);
    try {
      const res = await unifiedSearch(q);
      if (thisId !== searchIdRef.current) return; // stale
      setResults(res.data.from_public_judgments ?? []);
    } catch {
      if (thisId !== searchIdRef.current) return;
      setError("Search failed. Please check your connection and try again.");
    } finally {
      if (thisId === searchIdRef.current) setSearching(false);
    }
  };

  const attachedIds = new Set(attached.map((c) => c.id));

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 p-4 lg:p-10"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Find judgments to cite"
        className="hairline w-full max-w-3xl rounded-lg bg-card shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header + search */}
        <div className="border-b border-border p-5">
          <div className="flex items-center justify-between">
            <h2 className="font-serif text-lg">Find judgments to cite</h2>
            <button
              onClick={onClose}
              aria-label="Close"
              className="rounded p-1 text-muted-foreground hover:bg-muted"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="mt-4 flex gap-2">
            <div className="relative flex-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <input
                ref={inputRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && runSearch()}
                placeholder="e.g. anticipatory bail commercial quantity NDPS section 37"
                className="hairline h-10 w-full rounded-md bg-background pl-9 pr-3 text-sm placeholder:text-muted-foreground"
              />
            </div>
            <button
              onClick={runSearch}
              disabled={searching || !query.trim()}
              className="inline-flex h-10 shrink-0 items-center gap-2 rounded-md bg-amber-accent px-4 text-sm font-medium text-amber-accent-fg disabled:opacity-50"
            >
              {searching ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
              Search
            </button>
          </div>

          <p className="mt-2 text-[11px] text-muted-foreground">
            Searches the verified public judgment database. Only judgments whose
            certified copy can be retrieved may be added to a draft.
          </p>
        </div>

        {/* Results */}
        <div className="max-h-[55vh] overflow-y-auto">
          {error && (
            <div className="m-5 flex items-center gap-2 rounded-md bg-destructive/10 px-4 py-3 text-sm text-destructive">
              <AlertTriangle className="h-4 w-4" /> {error}
            </div>
          )}

          {searching && !results && (
            <div className="flex flex-col items-center gap-3 py-14 text-sm text-muted-foreground">
              <Loader2 className="h-6 w-6 animate-spin" />
              Searching judgments…
            </div>
          )}

          {!searching && results?.length === 0 && (
            <p className="px-5 py-14 text-center text-sm text-muted-foreground">
              No judgments matched that search. Try different terms — the section
              number, the offence, or the legal question rather than party names.
            </p>
          )}

          {results && results.length > 0 && (
            <ul className="divide-y divide-border">
              {results.map((r) => {
                const canAdd = isAttachable(r);
                const added = attachedIds.has(r.id);
                return (
                  <li key={r.id} className="flex items-start gap-4 p-5">
                    <BookOpen className="mt-1 h-4 w-4 shrink-0 text-amber-accent" />
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                        <h3 className="font-serif text-sm leading-snug">{r.case_name}</h3>
                        {r.primary_citation && (
                          <span className="font-mono text-xs text-muted-foreground">
                            {r.primary_citation}
                          </span>
                        )}
                      </div>
                      <div className="mt-1 text-xs text-muted-foreground">
                        {r.court} · {r.year}
                        {r.outcome && ` · ${r.outcome.replace(/_/g, " ")}`}
                      </div>
                      {r.summary && (
                        <p className="mt-1.5 line-clamp-2 text-xs text-muted-foreground">
                          {r.summary}
                        </p>
                      )}
                      {!canAdd && (
                        <p className="mt-1.5 text-[11px] text-amber-700 dark:text-amber-500">
                          No certified copy available — cannot be added to a filing.
                        </p>
                      )}
                    </div>

                    {added ? (
                      <button
                        onClick={() => onRemove(r.id)}
                        className="inline-flex h-8 shrink-0 items-center gap-1.5 rounded-md bg-emerald-500/15 px-3 text-xs font-medium text-emerald-700 dark:text-emerald-400"
                      >
                        <Check className="h-3.5 w-3.5" /> Added
                      </button>
                    ) : (
                      <button
                        onClick={() => onAdd(toAttached(r))}
                        disabled={!canAdd}
                        title={canAdd ? "Add to draft" : "No certified copy available"}
                        className="hairline inline-flex h-8 shrink-0 items-center gap-1.5 rounded-md bg-background px-3 text-xs font-medium disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        <Plus className="h-3.5 w-3.5" /> Add
                      </button>
                    )}
                  </li>
                );
              })}
            </ul>
          )}

          {!results && !searching && !error && (
            <p className="px-5 py-14 text-center text-sm text-muted-foreground">
              Search by legal question, section, or offence to find authorities for
              this draft.
            </p>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-border px-5 py-3">
          <span className="text-xs text-muted-foreground">
            {attached.length} judgment{attached.length === 1 ? "" : "s"} attached to this draft
          </span>
          <button
            onClick={onClose}
            className="inline-flex h-9 items-center rounded-md bg-foreground px-4 text-sm text-background"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
