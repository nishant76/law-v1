import { createFileRoute } from "@tanstack/react-router";
import { AppTopbar } from "@/components/app/AppTopbar";
import { useState } from "react";
import {
  unifiedSearch,
  openJudgmentPdf,
  downloadJudgmentPdf,
  getCitationSummary,
} from "@/api/search";
import type { PublicJudgmentResult, OwnFileResult } from "@/types";
import {
  Search,
  Filter,
  BookOpen,
  FileText,
  Loader2,
  ChevronDown,
  Download,
  ExternalLink,
} from "lucide-react";

export const Route = createFileRoute("/app/research")({
  head: () => ({ meta: [{ title: "Research — SuperAdvocate.Ai" }] }),
  component: Research,
});

const PAGE_SIZE = 10;

// ── helpers ───────────────────────────────────────────────────────────────────

function normaliseCourt(court: string): string {
  const c = court.toLowerCase();
  if (c.includes("supreme")) return "Supreme Court";
  if (
    c.includes("p&h") ||
    (c.includes("punjab") && c.includes("haryana")) ||
    c.includes("phhc")
  )
    return "P&H High Court";
  if (c.includes("high court")) return "High Court";
  if (c.includes("district")) return "District Court";
  return court;
}

// ── Research page ─────────────────────────────────────────────────────────────

function Research() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [publicResults, setPublicResults] = useState<PublicJudgmentResult[]>([]);
  const [ownResults, setOwnResults] = useState<OwnFileResult[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    setSearched(true);
    setVisibleCount(PAGE_SIZE);
    try {
      const res = await unifiedSearch(query, 50);
      setPublicResults(res.data.from_public_judgments ?? []);
      setOwnResults(res.data.from_your_files ?? []);
    } catch {
      setError("Search failed. Please check your connection and try again.");
    } finally {
      setLoading(false);
    }
  };

  const visiblePublic = publicResults.slice(0, visibleCount);
  const remaining = publicResults.length - visibleCount;

  return (
    <>
      <AppTopbar eyebrow="AI · Research" title="Judgments & citations" />
      <div className="flex-1 overflow-y-auto px-6 py-8 lg:px-10">
        {/* Search box */}
        <form
          onSubmit={handleSearch}
          className="hairline mx-auto flex max-w-5xl items-center gap-3 rounded-xl bg-card p-3"
        >
          <Search className="ml-3 h-5 w-5 text-muted-foreground" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder='Search judgments, e.g. "bail section 438 Punjab"'
            className="flex-1 bg-transparent py-3 text-sm focus:outline-none"
          />
          <button
            type="submit"
            disabled={loading}
            className="inline-flex h-10 items-center gap-2 rounded-md bg-amber-accent px-5 text-sm text-amber-accent-fg disabled:opacity-50"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Search"}
          </button>
        </form>

        {/* Court filter chips (static UI — query does the filtering for now) */}
        <div className="mx-auto mt-4 flex max-w-5xl flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <Filter className="h-3 w-3" />
          {["All courts", "Supreme Court", "High Courts", "Tribunals", "My files"].map(
            (f, i) => (
              <button
                key={f}
                className={`hairline rounded-full px-3 py-1 ${
                  i === 0 ? "bg-amber-accent text-amber-accent-fg" : "bg-card"
                }`}
              >
                {f}
              </button>
            )
          )}
        </div>

        {error && (
          <p className="mx-auto mt-6 max-w-5xl rounded-md bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {error}
          </p>
        )}

        {!searched && !loading && (
          <p className="mx-auto mt-10 max-w-5xl text-center text-sm text-muted-foreground">
            Search across P&H HC and Punjab district court judgments.
          </p>
        )}

        {searched && !loading && publicResults.length === 0 && ownResults.length === 0 && !error && (
          <p className="mx-auto mt-10 max-w-5xl text-center text-sm text-muted-foreground">
            No results found. Try rephrasing your query.
          </p>
        )}

        {(publicResults.length > 0 || ownResults.length > 0) && (
          <div className="mx-auto mt-8 max-w-5xl">
            {/* Own files */}
            {ownResults.length > 0 && (
              <div className="mb-6">
                <div className="mb-3 text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
                  From your files ({ownResults.length})
                </div>
                <div className="grid gap-px overflow-hidden rounded-xl bg-border">
                  {ownResults.map((r) => (
                    <article
                      key={r.document_id}
                      className="bg-card p-5 transition-colors hover:bg-sand/60"
                    >
                      <div className="flex items-start gap-4">
                        <FileText className="mt-1 h-4 w-4 shrink-0 text-accent-foreground" />
                        <div className="flex-1 min-w-0">
                          <h3 className="font-serif text-base text-foreground">
                            {r.document_name}
                          </h3>
                          {r.page && (
                            <div className="mt-1 text-xs text-muted-foreground">
                              Page {r.page} · Confidence {r.confidence}/10
                            </div>
                          )}
                          <p className="mt-2 text-sm leading-relaxed text-foreground/85">
                            {r.excerpt}
                          </p>
                        </div>
                      </div>
                    </article>
                  ))}
                </div>
              </div>
            )}

            {/* Public judgments */}
            {publicResults.length > 0 && (
              <div>
                <div className="mb-3 text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
                  From public judgments ({publicResults.length})
                </div>
                <div className="grid gap-px overflow-hidden rounded-xl bg-border">
                  {visiblePublic.map((r) => (
                    <JudgmentCard key={r.id} result={r} />
                  ))}
                </div>

                {remaining > 0 && (
                  <button
                    onClick={() => setVisibleCount((v) => v + PAGE_SIZE)}
                    className="hairline mt-2 w-full rounded-xl bg-card py-3 text-sm text-muted-foreground transition-colors hover:bg-sand/60"
                  >
                    Load {Math.min(PAGE_SIZE, remaining)} more
                    <span className="ml-2 text-xs opacity-60">({remaining} remaining)</span>
                  </button>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </>
  );
}

// ── Judgment card ─────────────────────────────────────────────────────────────

function JudgmentCard({ result }: { result: PublicJudgmentResult }) {
  const [expanded, setExpanded] = useState(false);
  const [summary, setSummary] = useState<string | null>(
    result.enrichment?.facts ||
      result.enrichment?.relevance ||
      result.summary ||
      null
  );
  const [summaryState, setSummaryState] = useState<
    "idle" | "loading" | "done" | "error"
  >("idle");
  const [opening, setOpening] = useState(false);
  const [downloading, setDownloading] = useState(false);

  const judgmentUrl = result.judgment_url;
  const officialUrl = result.official_source_url || result.source_url;
  const safeFilename =
    (result.citation_key || result.id).replace(/[^a-z0-9-]/gi, "-") + ".pdf";

  const handleExpand = async () => {
    const nowExpanded = !expanded;
    setExpanded(nowExpanded);
    if (nowExpanded && !summary && summaryState === "idle") {
      setSummaryState("loading");
      try {
        const res = await getCitationSummary(result.id);
        setSummary(res.data.summary);
        setSummaryState("done");
      } catch {
        setSummaryState("error");
      }
    }
  };

  const handleView = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!judgmentUrl || opening) return;
    setOpening(true);
    await openJudgmentPdf(judgmentUrl);
    setOpening(false);
  };

  const handleDownload = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!judgmentUrl || downloading) return;
    setDownloading(true);
    await downloadJudgmentPdf(judgmentUrl, safeFilename);
    setDownloading(false);
  };

  return (
    <article
      className={`bg-card transition-colors ${expanded ? "" : "cursor-pointer hover:bg-sand/60"}`}
      onClick={!expanded ? handleExpand : undefined}
    >
      {/* ── Collapsed header ───────────────────────────────────────────── */}
      <div
        className="flex items-start gap-4 p-5"
        onClick={expanded ? handleExpand : undefined}
        style={{ cursor: "pointer" }}
      >
        <BookOpen className="mt-1 h-4 w-4 shrink-0 text-amber-accent" />
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-baseline gap-3">
            <h3 className="font-serif text-base text-foreground leading-snug">
              {result.case_name}
            </h3>
            {result.primary_citation && (
              <span className="font-mono text-xs text-muted-foreground">
                {result.primary_citation}
              </span>
            )}
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span>{normaliseCourt(result.court)}</span>
            <span>·</span>
            <span>{result.year}</span>
            {result.matter_type && (
              <>
                <span>·</span>
                <span className="rounded-full bg-sand px-2 py-0.5">
                  {result.matter_type}
                </span>
              </>
            )}
            {result.outcome && (
              <>
                <span>·</span>
                <span className="capitalize">{result.outcome.replace(/_/g, " ")}</span>
              </>
            )}
          </div>
          {!expanded && (
            <p className="mt-1.5 text-[11px] text-muted-foreground/60 italic">
              Click to read summary and open PDF
            </p>
          )}
        </div>
        <ChevronDown
          className={`mt-1 h-4 w-4 shrink-0 text-muted-foreground transition-transform ${
            expanded ? "rotate-180" : ""
          }`}
        />
      </div>

      {/* ── Expanded panel ─────────────────────────────────────────────── */}
      {expanded && (
        <div
          className="border-t border-border px-5 pb-5 pt-4"
          onClick={(e) => e.stopPropagation()}
        >
          {/* AI Summary */}
          <div className="mb-4">
            <div className="mb-2 text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
              AI Summary
            </div>

            {summaryState === "loading" && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                Generating summary…
              </div>
            )}

            {summaryState !== "loading" && summary && (
              <p className="text-sm leading-relaxed text-foreground/85">{summary}</p>
            )}

            {(summaryState === "error" || (summaryState === "done" && !summary)) && (
              <p className="text-xs italic text-muted-foreground">
                Summary not available for this judgment.
              </p>
            )}
          </div>

          {/* Action buttons */}
          <div className="flex flex-wrap items-center gap-2">
            {judgmentUrl && (
              <button
                onClick={handleView}
                disabled={opening}
                className="inline-flex items-center gap-1.5 rounded-md bg-amber-accent px-4 py-2 text-xs font-semibold text-amber-accent-fg disabled:opacity-50 hover:opacity-90 transition-opacity"
              >
                <FileText className="h-3.5 w-3.5" />
                {opening ? "Opening…" : "View PDF"}
              </button>
            )}

            {judgmentUrl && (
              <button
                onClick={handleDownload}
                disabled={downloading}
                className="hairline inline-flex items-center gap-1.5 rounded-md bg-card px-4 py-2 text-xs font-semibold text-foreground disabled:opacity-50 hover:bg-sand/60 transition-colors"
              >
                <Download className="h-3.5 w-3.5" />
                {downloading ? "Downloading…" : "Download"}
              </button>
            )}

            {officialUrl && (
              <a
                href={officialUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-xs text-muted-foreground underline hover:text-foreground transition-colors"
                onClick={(e) => e.stopPropagation()}
              >
                Official source
                <ExternalLink className="h-3 w-3" />
              </a>
            )}
          </div>
        </div>
      )}
    </article>
  );
}
