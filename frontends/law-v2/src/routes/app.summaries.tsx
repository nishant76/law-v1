import { createFileRoute } from "@tanstack/react-router";
import { AppTopbar } from "@/components/app/AppTopbar";
import { useState, useRef } from "react";
import { generateSynopsisFromUpload, exportSynopsis, type Synopsis } from "@/api/synopsis";
import { Upload, Download, Printer, Loader2 } from "lucide-react";

export const Route = createFileRoute("/app/summaries")({
  head: () => ({ meta: [{ title: "Summaries — SuperAdvocate.Ai" }] }),
  component: Summaries,
});

function Summaries() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [loading, setLoading] = useState(false);
  const [synopsis, setSynopsis] = useState<Synopsis | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    setError(null);
    setSynopsis(null);
    try {
      const res = await generateSynopsisFromUpload(file);
      setSynopsis(res.data.data);
    } catch {
      setError("Failed to generate summary. Please upload a valid judgment PDF.");
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    if (!synopsis?.id) return;
    setExporting(true);
    try {
      const res = await exportSynopsis(synopsis.id);
      const url = URL.createObjectURL(res.data as Blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${(synopsis.case_name ?? "summary").replace(/\s+/g, "_")}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setError("Export failed.");
    } finally {
      setExporting(false);
    }
  };

  return (
    <>
      <AppTopbar
        eyebrow="AI · Summaries"
        title="One-page case summary"
        actions={
          synopsis ? (
            <div className="flex gap-2">
              <button onClick={() => window.print()} className="hairline inline-flex h-9 items-center gap-2 rounded-md bg-card px-3 text-sm">
                <Printer className="h-3.5 w-3.5" /> Print
              </button>
              <button onClick={handleExport} disabled={exporting} className="inline-flex h-9 items-center gap-2 rounded-md bg-amber-accent px-4 text-sm text-amber-accent-fg disabled:opacity-50">
                {exporting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />} Download PDF
              </button>
            </div>
          ) : undefined
        }
      />
      <div className="flex-1 overflow-y-auto bg-sand/40 px-6 py-10 lg:px-10">
        {!synopsis && !loading && (
          <div className="mx-auto max-w-3xl">
            <input ref={fileRef} type="file" accept=".pdf" className="hidden" onChange={handleUpload} />
            <button
              onClick={() => fileRef.current?.click()}
              className="hairline flex w-full flex-col items-center justify-center gap-3 rounded-xl bg-card py-16 text-muted-foreground hover:bg-background"
            >
              <Upload className="h-8 w-8 opacity-50" />
              <div className="text-sm font-medium">Upload a judgment PDF</div>
              <div className="text-xs">We'll generate a one-page summary with facts, issues, holding, and ratio</div>
            </button>
            {error && <p className="mt-4 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>}
          </div>
        )}

        {loading && (
          <div className="flex items-center justify-center py-32">
            <div className="text-center text-sm text-muted-foreground">
              <Loader2 className="mx-auto h-8 w-8 animate-spin" />
              <p className="mt-4">Analysing judgment and generating summary…</p>
            </div>
          </div>
        )}

        {synopsis && (
          <article className="mx-auto max-w-3xl rounded-lg border border-border bg-card p-12 font-serif leading-7 shadow-sm">
            <div className="eyebrow">Case summary · prepared {new Date().toLocaleDateString("en-IN")}</div>
            <h2 className="mt-2 text-3xl">{synopsis.case_name ?? "Judgment"}</h2>
            {(synopsis.court || synopsis.judgment_date) && (
              <div className="mt-1 font-mono text-sm text-muted-foreground">
                {[synopsis.court, synopsis.judgment_date].filter(Boolean).join(" · ")}
              </div>
            )}

            {synopsis.facts && (
              <Block label="Facts">{synopsis.facts}</Block>
            )}

            {synopsis.issues.length > 0 && (
              <Block label="Issues">
                <ol className="ml-4 list-decimal space-y-1">
                  {synopsis.issues.map((issue, i) => <li key={i}>{issue}</li>)}
                </ol>
              </Block>
            )}

            {synopsis.held && (
              <Block label="Holding">{synopsis.held}</Block>
            )}

            {synopsis.citations_used.length > 0 && (
              <Block label="Citations relied on">
                <ul className="space-y-1 font-mono text-sm">
                  {synopsis.citations_used.map((c) => <li key={c}>{c}</li>)}
                </ul>
              </Block>
            )}

            {synopsis.relief_granted && (
              <Block label="Relief granted">{synopsis.relief_granted}</Block>
            )}

            <div className="mt-10 flex justify-between border-t border-border pt-4 text-xs text-muted-foreground">
              <span>Prepared by SuperAdvocate.Ai · review before relying · confidence {Math.round(synopsis.confidence * 100)}%</span>
              <span>Page 1 of 1</span>
            </div>

            <div className="mt-4">
              <input ref={fileRef} type="file" accept=".pdf" className="hidden" onChange={handleUpload} />
              <button onClick={() => fileRef.current?.click()} className="hairline rounded-md bg-card px-3 py-1.5 text-xs text-muted-foreground hover:bg-background">
                Upload another judgment
              </button>
            </div>
          </article>
        )}
      </div>
    </>
  );
}

function Block({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <section className="mt-6">
      <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground">{label}</div>
      <div className="mt-2 text-[15px] text-foreground/90">{children}</div>
    </section>
  );
}
