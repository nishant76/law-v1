import { createFileRoute } from "@tanstack/react-router";
import { AppTopbar } from "@/components/app/AppTopbar";
import { useState, useRef, useEffect, useMemo } from "react";
import { generateFilingTemplate, generateFilingTemplateFromFile, exportFilingTemplate, checkBrief } from "@/api/filing";
import type { FilingTemplateResponse, BriefCheckResponse, BriefQuestion } from "@/api/filing";
import { FileText, Sparkles, Upload, Download, Loader2, Pencil, Check, X, CircleCheck, CircleDashed } from "lucide-react";
import MarkdownText from "@/components/ui/MarkdownText";
import { analyzeBriefLocally, type BriefDimensionResult } from "@/lib/briefStrength";
import { DraftCitationsPanel } from "@/components/app/DraftCitationsPanel";
import { authoritiesMarkdown, type AttachedCitation } from "@/lib/draftCitations";

export const Route = createFileRoute("/app/drafting")({
  head: () => ({ meta: [{ title: "Drafting — SuperAdvocate.Ai" }] }),
  component: Drafting,
});

// Substitutes {{key}} tokens with the lawyer's typed value (live-fill). In "preview" mode every
// field — filled or not — renders as a ⟦highlighted chip⟧ (MarkdownText's existing chip syntax)
// so blanks stay visually obvious in the draft. In "export" mode chips are stripped to plain
// text so the .docx never contains literal "{{token}}" or "⟦⟧" markup.
function fillTemplate(
  template: string,
  keyFields: FilingTemplateResponse["key_fields"],
  values: Record<string, string>,
  mode: "preview" | "export"
): string {
  let out = template;
  for (const f of keyFields) {
    const typed = values[f.key]?.trim();
    const display = typed
      ? (mode === "preview" ? `⟦${typed}⟧` : typed)
      : (mode === "preview" ? `⟦${f.label}⟧` : `[${f.label.toUpperCase()}]`);
    out = out.replaceAll(`{{${f.key}}}`, display);
  }
  return out;
}

function Drafting() {
  // Optional filing-type hint. Empty for the first pass (the model classifies the
  // type from the brief). Set only when the lawyer corrects the detected-type chip,
  // in which case it's prepended to the brief on regeneration to steer the type +
  // precedent routing. Replaces the old mandatory Document Type dropdown.
  const [typeOverride, setTypeOverride] = useState("");
  const [editingType, setEditingType] = useState(false);
  const [typeDraft, setTypeDraft] = useState("");
  const [brief, setBrief] = useState("");
  const [court, setCourt] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<FilingTemplateResponse | null>(null);
  const [fieldValues, setFieldValues] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [briefModalOpen, setBriefModalOpen] = useState(false);
  // Judgments the lawyer has attached from the Authorities pane. Kept out of
  // `result` so regenerating the draft does not silently drop them.
  const [citations, setCitations] = useState<AttachedCitation[]>([]);
  const fileRef = useRef<HTMLInputElement>(null);

  const addCitation = (c: AttachedCitation) =>
    setCitations((prev) => (prev.some((x) => x.id === c.id) ? prev : [...prev, c]));
  const removeCitation = (id: string) =>
    setCitations((prev) => prev.filter((c) => c.id !== id));

  // Brief strength. The METER + CHECKLIST come from a local, zero-network heuristic
  // (analyzeBriefLocally) recomputed synchronously on every keystroke → fully realtime.
  // The AI pass (debounced) is used ONLY to sharpen the clarifying questions + filing-type
  // label; if it 401s / fails / is slow, the local result stands and nothing breaks.
  const local = useMemo(() => analyzeBriefLocally(brief, court), [brief, court]);

  // Plain async/await + a stale-response guard rather than useMutation/useQuery — TanStack
  // Query v5 cancels in-flight calls in React Strict Mode dev (see CLAUDE.md).
  const [analysis, setAnalysis] = useState<BriefCheckResponse | null>(null);
  const [analysisKey, setAnalysisKey] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const analysisIdRef = useRef(0);

  // Key identifying the exact input an AI result belongs to, so a stale result never
  // masquerades as fresh once the lawyer keeps typing.
  const currentKey = `${brief.trim()}|${court}|${typeOverride}`;

  useEffect(() => {
    const b = brief.trim();
    if (b.length < 25) {
      setAnalyzing(false);
      return;
    }
    setAnalyzing(true);
    const thisId = ++analysisIdRef.current;
    const key = currentKey;
    const t = setTimeout(async () => {
      try {
        const res = await checkBrief({ brief: b, court: court || undefined, type_hint: typeOverride || undefined });
        if (thisId !== analysisIdRef.current) return; // ignore stale
        setAnalysis(res.data);
        setAnalysisKey(key);
      } catch {
        // silent — local heuristic already drives the meter; AI only augments questions
      } finally {
        if (thisId === analysisIdRef.current) setAnalyzing(false);
      }
    }, 900);
    return () => clearTimeout(t);
  }, [brief, court, typeOverride, currentKey]);

  // Prefer the AI's sharper questions/type only while they match the current text; otherwise
  // fall back to the local heuristic so everything shown stays consistent with the brief.
  const aiFresh = !!analysis && analysisKey === currentKey;
  const questions: BriefQuestion[] =
    aiFresh && analysis!.questions.length > 0 ? analysis!.questions : local.questions;
  const filingType = (aiFresh && analysis!.detected_filing_type) || local.detected_filing_type;

  // Fold answered clarifying questions into the brief so the draft actually uses them.
  const buildEnrichedBrief = () => {
    const extras = questions
      .map((q) => ({ q: q.question, a: (answers[q.id] ?? "").trim() }))
      .filter((x) => x.a);
    if (extras.length === 0) return brief;
    const block = extras.map((x) => `- ${x.q} ${x.a}`).join("\n");
    return `${brief}\n\nAdditional details:\n${block}`;
  };

  const applyResult = (data: FilingTemplateResponse) => {
    setResult(data);
    const initial: Record<string, string> = {};
    for (const f of data.key_fields) initial[f.key] = f.value ?? "";
    setFieldValues(initial);
  };

  const handleGenerate = async (overrideType?: string) => {
    if (!brief.trim()) return;
    const hint = (overrideType ?? typeOverride).trim();
    setLoading(true);
    setError(null);
    setEditingType(false);
    try {
      const enriched = buildEnrichedBrief();
      const input_text = hint ? `${hint}\n\n${enriched}` : enriched;
      const res = await generateFilingTemplate({ input_text, court: court || undefined });
      applyResult(res.data);
      setBriefModalOpen(false);
    } catch {
      setError("Failed to generate draft. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  // Lawyer corrected the detected filing type → prepend it and regenerate so the
  // type hint + precedent routing use the corrected value.
  const applyTypeCorrection = () => {
    const next = typeDraft.trim();
    if (!next) return;
    setTypeOverride(next);
    void handleGenerate(next);
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const res = await generateFilingTemplateFromFile(file, { court: court || undefined });
      applyResult(res.data);
      setBriefModalOpen(false);
    } catch {
      setError("Failed to process file. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  // The draft body plus the attached authorities. One helper so the preview and
  // the .docx can never drift apart — only the token rendering differs.
  const composeDraft = (mode: "preview" | "export") =>
    fillTemplate(result!.template_markdown, result!.key_fields, fieldValues, mode) +
    authoritiesMarkdown(citations);

  const handleExport = async () => {
    if (!result) return;
    setExporting(true);
    try {
      const res = await exportFilingTemplate({
        title: result.title,
        filled_markdown: composeDraft("export"),
        court: court || undefined,
      });
      const url = URL.createObjectURL(res.data as Blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${result.title.replace(/\s+/g, "_")}.docx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setError("Export failed. Please try again.");
    } finally {
      setExporting(false);
    }
  };

  const step1Form = (
    <>
      <div className="eyebrow">Step 1</div>
      <h2 className="mt-2 font-serif text-xl">Describe your matter.</h2>
      <p className="mt-2 text-[13px] leading-relaxed text-muted-foreground">
        Write in plain language — we'll identify the filing type for you and you can
        correct it after.
      </p>

      <label className="eyebrow mt-6 mb-2 block">Brief description</label>
      <textarea
        rows={8}
        value={brief}
        onChange={(e) => setBrief(e.target.value)}
        placeholder="Describe the facts, parties, reliefs sought, and any relevant legal provisions or citations…"
        className="hairline w-full rounded-md bg-card p-3 text-sm leading-relaxed"
      />

      <BriefStrength
        score={local.completeness_score}
        band={local.score_band}
        dimensions={local.dimensions}
        filingType={filingType}
        questions={questions}
        refining={analyzing && !aiFresh}
        briefLength={brief.trim().length}
        answers={answers}
        onAnswer={(id, v) => setAnswers((prev) => ({ ...prev, [id]: v }))}
      />

      <div className="mt-5">
        <div className="eyebrow mb-2">Or attach an existing draft</div>
        <input ref={fileRef} type="file" accept=".pdf,.docx" className="hidden" onChange={handleFileUpload} />
        <button
          onClick={() => fileRef.current?.click()}
          className="hairline flex w-full items-center justify-center gap-2 rounded-md bg-card py-6 text-sm text-muted-foreground hover:bg-background"
        >
          <Upload className="h-4 w-4" /> Upload .docx or .pdf
        </button>
      </div>

      {error && <p className="mt-4 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>}

      <button
        onClick={() => handleGenerate()}
        disabled={loading || !brief.trim()}
        className="mt-8 inline-flex h-11 w-full items-center justify-center gap-2 rounded-md bg-amber-accent text-sm font-medium text-amber-accent-fg hover:opacity-90 disabled:opacity-50"
      >
        {loading ? <><Loader2 className="h-4 w-4 animate-spin" /> Generating…</> : <><Sparkles className="h-4 w-4" /> Generate draft</>}
      </button>
    </>
  );

  if (!result) {
    return (
      <>
        <AppTopbar eyebrow="AI · Drafting" title="New court filing draft" />
        <div className="flex min-h-0 flex-1 justify-center overflow-y-auto bg-sand/60 p-6 lg:p-10">
          <div className="w-full max-w-2xl">
            {step1Form}
            {loading && (
              <div className="mt-8 flex items-center justify-center text-sm text-muted-foreground">
                <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Generating your draft… this may take up to 60 seconds.
              </div>
            )}
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <AppTopbar eyebrow="AI · Drafting" title="New court filing draft" />
      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto bg-background">
        {/* Compact brief bar */}
        <div className="sticky top-0 z-10 flex items-center justify-between gap-4 border-b border-border bg-card px-6 py-3 shadow-sm lg:px-10">
          <div className="min-w-0 truncate text-sm text-foreground">
            <span className="font-semibold">Brief description: </span>
            <span className="text-muted-foreground">{brief}</span>
          </div>
          <button
            onClick={() => { setTypeDraft(""); setBriefModalOpen(true); }}
            className="inline-flex shrink-0 items-center gap-1.5 rounded-md bg-amber-accent px-3 py-1.5 text-xs font-medium text-amber-accent-fg hover:opacity-90"
          >
            <Pencil className="h-3.5 w-3.5" /> Edit
          </button>
        </div>

        {briefModalOpen && (
          <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 p-6 lg:p-10">
            <div className="hairline w-full max-w-2xl rounded-lg bg-sand/95 p-6 shadow-xl lg:p-8">
              <div className="flex items-center justify-between">
                <div className="eyebrow">Edit brief</div>
                <button
                  onClick={() => setBriefModalOpen(false)}
                  className="rounded p-1 text-muted-foreground hover:bg-muted"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              {step1Form}
            </div>
          </div>
        )}

        {/* Document */}
        <section className="overflow-y-auto bg-background p-6 lg:p-10">
          {result && (
            <div className="mx-auto flex max-w-[1500px] items-start gap-6">
              <div className="min-w-0 max-w-5xl flex-1">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3 text-sm text-muted-foreground">
                    <FileText className="h-4 w-4" />
                    <span>{result.title}</span>
                  </div>
                  <button
                    onClick={handleExport}
                    disabled={exporting}
                    className="inline-flex h-9 items-center gap-2 rounded-md bg-amber-accent px-4 text-sm text-amber-accent-fg disabled:opacity-50"
                  >
                    {exporting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
                    Export .docx
                  </button>
                </div>

                {result.detected_document_type && (
                  <div className="mt-3 flex items-center gap-2 text-xs">
                    <span className="text-muted-foreground">Filing type:</span>
                    {editingType ? (
                      <span className="inline-flex items-center gap-1">
                        <input
                          autoFocus
                          value={typeDraft}
                          onChange={(e) => setTypeDraft(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") applyTypeCorrection();
                            if (e.key === "Escape") setEditingType(false);
                          }}
                          className="hairline h-7 w-64 rounded-md bg-card px-2 text-xs"
                        />
                        <button
                          onClick={applyTypeCorrection}
                          title="Regenerate as this type"
                          className="rounded p-1 text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-900/30"
                        >
                          <Check className="h-3.5 w-3.5" />
                        </button>
                        <button
                          onClick={() => setEditingType(false)}
                          title="Cancel"
                          className="rounded p-1 text-muted-foreground hover:bg-muted"
                        >
                          <X className="h-3.5 w-3.5" />
                        </button>
                      </span>
                    ) : (
                      <button
                        onClick={() => { setTypeDraft(result.detected_document_type); setEditingType(true); }}
                        title="Wrong type? Click to correct it and regenerate."
                        className="inline-flex items-center gap-1.5 rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 font-medium text-amber-800 hover:bg-amber-100 dark:border-amber-800/40 dark:bg-amber-900/20 dark:text-amber-300"
                      >
                        {result.detected_document_type}
                        <Pencil className="h-3 w-3 opacity-60" />
                      </button>
                    )}
                  </div>
                )}

                {result.strategy_notes && (
                  <div className={`mt-4 rounded-md px-4 py-3 text-xs ${result.strategy_notes.toLowerCase().includes("inferred") ? "border border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-800/40 dark:bg-amber-900/20 dark:text-amber-300" : "bg-sand text-muted-foreground"}`}>
                    <strong className="font-semibold">{result.strategy_notes.toLowerCase().includes("inferred") ? "Court auto-selected — " : "Strategy note — "}</strong>
                    {result.strategy_notes}
                  </div>
                )}

                {/* Facts the draft needs but the brief did not supply. Shown
                    prominently and above the draft: a statutory bar the model
                    could not verify (e.g. the seized quantity that decides
                    whether NDPS s.37 applies) must never be buried. */}
                {result.missing_facts?.length > 0 && (
                  <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-800 dark:border-amber-800/40 dark:bg-amber-900/20 dark:text-amber-300">
                    <strong className="font-semibold">
                      Verify before filing — {result.missing_facts.length} detail
                      {result.missing_facts.length === 1 ? "" : "s"} missing from your brief:
                    </strong>
                    <ul className="mt-1.5 list-disc space-y-0.5 pl-4">
                      {result.missing_facts.map((f, i) => (
                        <li key={i}>{f}</li>
                      ))}
                    </ul>
                  </div>
                )}

                <article className="hairline mt-4 rounded-lg bg-card p-10 font-serif text-foreground">
                  <MarkdownText text={composeDraft("preview")} className="text-[15px] leading-[1.9]" />
                </article>

                {result.citations_used.length > 0 && (
                  <div className="mt-6 rounded-md bg-sand p-4">
                    <div className="eyebrow mb-2">Citations used</div>
                    <ul className="space-y-1 text-sm">
                      {result.citations_used.map((c) => <li key={c} className="font-mono text-xs">{c}</li>)}
                    </ul>
                  </div>
                )}
              </div>

              <aside className="sticky top-6 w-[280px] shrink-0 space-y-4">
                {result.key_fields.length > 0 && (
                  <div className="hairline rounded-lg bg-card p-4">
                    <div className="eyebrow mb-1">Key details</div>
                    <p className="mb-4 text-xs text-muted-foreground">Fill these in — the draft updates as you type.</p>
                    <div className="space-y-3">
                      {result.key_fields.map((f) => (
                        <div key={f.key}>
                          <label className="eyebrow mb-1 block text-[10px]">{f.label}</label>
                          <input
                            value={fieldValues[f.key] ?? ""}
                            onChange={(e) => setFieldValues((prev) => ({ ...prev, [f.key]: e.target.value }))}
                            placeholder={f.example ?? ""}
                            className="hairline h-9 w-full rounded-md bg-card px-3 text-sm placeholder:text-muted-foreground"
                          />
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <DraftCitationsPanel
                  brief={brief}
                  filingType={result.detected_document_type}
                  attached={citations}
                  onAdd={addCitation}
                  onRemove={removeCitation}
                />
              </aside>
            </div>
          )}
        </section>
      </div>
    </>
  );
}

// Live "brief strength" panel. The meter + checklist are driven by the local heuristic
// (realtime, always shown — even for a blank brief). `refining` shows a subtle spinner while
// the AI sharpens the questions. Advisory only; never blocks Generate.
function BriefStrength({
  score,
  band,
  dimensions,
  filingType,
  questions,
  refining,
  briefLength,
  answers,
  onAnswer,
}: {
  score: number;
  band: string;
  dimensions: BriefDimensionResult[];
  filingType: string;
  questions: BriefQuestion[];
  refining: boolean;
  briefLength: number;
  answers: Record<string, string>;
  onAnswer: (id: string, value: string) => void;
}) {
  const empty = briefLength === 0;
  // Colour the meter + score by band.
  const tone =
    band === "Strong"
      ? { bar: "bg-emerald-500", text: "text-emerald-600 dark:text-emerald-400" }
      : band === "Workable"
        ? { bar: "bg-amber-500", text: "text-amber-600 dark:text-amber-500" }
        : band === "Thin"
          ? { bar: "bg-rose-500", text: "text-rose-600 dark:text-rose-400" }
          : { bar: "bg-muted-foreground/30", text: "text-muted-foreground" };

  return (
    <div className="hairline mt-5 rounded-md bg-card p-4">
      <div className="flex items-center justify-between">
        <div className="eyebrow">Brief strength</div>
        <span className={`text-sm font-semibold ${tone.text}`}>
          {score}%{!empty && ` · ${band}`}
        </span>
      </div>

      {/* Meter */}
      <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-muted">
        <div
          className={`h-full rounded-full transition-all duration-300 ${tone.bar}`}
          style={{ width: `${score}%` }}
        />
      </div>

      {empty ? (
        <p className="mt-2 text-[11px] text-muted-foreground">
          Start typing your brief — we'll check it live as you go.
        </p>
      ) : (
        filingType && (
          <p className="mt-2 text-[11px] text-muted-foreground">
            Reading this as: <span className="font-medium text-foreground">{filingType}</span>
          </p>
        )
      )}

      {/* Six-dimension checklist (always shown so the lawyer sees what's needed) */}
      <ul className="mt-3 space-y-1.5">
        {dimensions.map((d) => (
          <li key={d.key} className="flex items-start gap-2 text-xs">
            {d.present ? (
              <CircleCheck className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-600 dark:text-emerald-400" />
            ) : (
              <CircleDashed className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground/50" />
            )}
            <span className={d.present ? "text-foreground" : "text-muted-foreground"}>
              {d.label}
              {!d.present && d.note && <span className="text-muted-foreground/70"> — {d.note}</span>}
            </span>
          </li>
        ))}
      </ul>

      {/* Clarifying questions with inline answer boxes */}
      {questions.length > 0 && (
        <div className="mt-4 border-t border-border pt-3">
          <div className="flex items-center gap-2">
            <div className="eyebrow">Answer these for a sharper draft</div>
            {refining && <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />}
          </div>
          <p className="mb-3 mt-1 text-[11px] text-muted-foreground">
            Optional — your answers are added to the brief before drafting.
          </p>
          <div className="space-y-3">
            {questions.map((q) => (
              <div key={q.id}>
                <label className="mb-1 block text-xs font-medium text-foreground">{q.question}</label>
                <input
                  value={answers[q.id] ?? ""}
                  onChange={(e) => onAnswer(q.id, e.target.value)}
                  placeholder={q.why || "Type your answer…"}
                  className="hairline h-9 w-full rounded-md bg-card px-3 text-sm placeholder:text-muted-foreground"
                />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
