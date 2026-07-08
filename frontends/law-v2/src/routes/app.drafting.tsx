import { createFileRoute } from "@tanstack/react-router";
import { AppTopbar } from "@/components/app/AppTopbar";
import { useState, useRef } from "react";
import { generateFilingTemplate, generateFilingTemplateFromFile, exportFilingTemplate } from "@/api/filing";
import type { FilingTemplateResponse } from "@/api/filing";
import { FileText, Sparkles, Upload, Download, Loader2 } from "lucide-react";

export const Route = createFileRoute("/app/drafting")({
  head: () => ({ meta: [{ title: "Drafting — SuperAdvocate.Ai" }] }),
  component: Drafting,
});

const TEMPLATES = [
  "Writ Petition (Art. 226)",
  "Plaint — Civil Suit",
  "Bail Application (S.439 CrPC)",
  "Reply to S.138 NI Act notice",
  "Written Statement",
  "Petition for Divorce (S.13 HMA)",
  "Anticipatory Bail",
  "Consumer Complaint",
];

function Drafting() {
  const [filingType, setFilingType] = useState(TEMPLATES[0]);
  const [brief, setBrief] = useState("");
  const [court, setCourt] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<FilingTemplateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleGenerate = async () => {
    if (!brief.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await generateFilingTemplate({ input_text: `${filingType}\n\n${brief}`, court: court || undefined });
      setResult(res.data);
    } catch {
      setError("Failed to generate draft. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const res = await generateFilingTemplateFromFile(file, { court: court || undefined });
      setResult(res.data);
    } catch {
      setError("Failed to process file. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    if (!result) return;
    setExporting(true);
    try {
      const res = await exportFilingTemplate({
        title: result.title,
        filled_markdown: result.template_markdown,
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

  return (
    <>
      <AppTopbar eyebrow="AI · Drafting" title="New court filing draft" />
      <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[360px_1fr]">
        {/* Left rail: brief */}
        <aside className="border-r border-border bg-sand/60 p-6 lg:p-8">
          <div className="eyebrow">Step 1</div>
          <h2 className="mt-2 font-serif text-xl">Tell us what you need.</h2>

          <label className="eyebrow mt-6 mb-2 block">Document type</label>
          <select
            value={filingType}
            onChange={(e) => setFilingType(e.target.value)}
            className="hairline h-10 w-full rounded-md bg-card px-3 text-sm"
          >
            {TEMPLATES.map((t) => <option key={t}>{t}</option>)}
          </select>

          <label className="eyebrow mt-5 mb-2 block">Court (optional)</label>
          <input
            value={court}
            onChange={(e) => setCourt(e.target.value)}
            placeholder="e.g. High Court of Karnataka"
            className="hairline h-10 w-full rounded-md bg-card px-3 text-sm placeholder:text-muted-foreground"
          />

          <label className="eyebrow mt-5 mb-2 block">Brief description</label>
          <textarea
            rows={8}
            value={brief}
            onChange={(e) => setBrief(e.target.value)}
            placeholder="Describe the facts, parties, reliefs sought, and any relevant legal provisions or citations…"
            className="hairline w-full rounded-md bg-card p-3 text-sm leading-relaxed"
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
            onClick={handleGenerate}
            disabled={loading || !brief.trim()}
            className="mt-8 inline-flex h-11 w-full items-center justify-center gap-2 rounded-md bg-amber-accent text-sm font-medium text-amber-accent-fg hover:opacity-90 disabled:opacity-50"
          >
            {loading ? <><Loader2 className="h-4 w-4 animate-spin" /> Generating…</> : <><Sparkles className="h-4 w-4" /> Generate draft</>}
          </button>
        </aside>

        {/* Document */}
        <section className="bg-background p-6 lg:p-10">
          {!result && !loading && (
            <div className="flex h-full items-center justify-center text-center text-sm text-muted-foreground">
              <div>
                <FileText className="mx-auto h-10 w-10 opacity-20" />
                <p className="mt-4">Fill in the brief and click Generate draft.</p>
                <p className="mt-1">Your document will appear here.</p>
              </div>
            </div>
          )}

          {loading && (
            <div className="flex h-full items-center justify-center">
              <div className="text-center text-sm text-muted-foreground">
                <Loader2 className="mx-auto h-8 w-8 animate-spin" />
                <p className="mt-4">Generating your draft…</p>
                <p className="mt-1 text-xs">This may take up to 60 seconds</p>
              </div>
            </div>
          )}

          {result && (
            <div className="mx-auto max-w-3xl">
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

              <article className="hairline mt-6 rounded-lg bg-card p-10 font-serif text-[15px] leading-7 text-foreground whitespace-pre-wrap">
                {result.template_markdown}
              </article>

              {result.citations_used.length > 0 && (
                <div className="mt-6 rounded-md bg-sand p-4">
                  <div className="eyebrow mb-2">Citations used</div>
                  <ul className="space-y-1 text-sm">
                    {result.citations_used.map((c) => <li key={c} className="font-mono text-xs">{c}</li>)}
                  </ul>
                </div>
              )}

              {result.strategy_notes && (
                <div className="mt-4 rounded-md bg-sand p-4 text-xs text-muted-foreground">
                  <strong className="text-foreground">AI strategy note:</strong> {result.strategy_notes}
                </div>
              )}

              {result.key_fields.length > 0 && (
                <div className="mt-6">
                  <div className="eyebrow mb-3">Fill in these details</div>
                  <div className="grid gap-3 sm:grid-cols-2">
                    {result.key_fields.map((f) => (
                      <div key={f.key}>
                        <label className="eyebrow mb-1 block text-[10px]">{f.label}</label>
                        <input
                          defaultValue={f.value ?? ""}
                          placeholder={f.example ?? ""}
                          className="hairline h-9 w-full rounded-md bg-card px-3 text-sm placeholder:text-muted-foreground"
                        />
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </section>
      </div>
    </>
  );
}
