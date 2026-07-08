import { createFileRoute } from "@tanstack/react-router";
import { AppTopbar } from "@/components/app/AppTopbar";
import { useState, useRef } from "react";
import {
  uploadAndExtractAllegations,
  generateReply,
  exportReplyDocx,
  type NoticeExtraction,
  type AllegationResponse,
} from "@/api/reply";
import { Upload, FileText, ChevronRight, Sparkles, Download, Loader2 } from "lucide-react";

export const Route = createFileRoute("/app/notice-reply")({
  head: () => ({ meta: [{ title: "Notice reply — SuperAdvocate.Ai" }] }),
  component: NoticeReply,
});

function NoticeReply() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [extraction, setExtraction] = useState<NoticeExtraction | null>(null);
  const [responses, setResponses] = useState<Record<number, { stance: AllegationResponse["stance"]; grounds: string }>>({});
  const [replyText, setReplyText] = useState<string | null>(null);
  const [draftId, setDraftId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    setExtraction(null);
    setReplyText(null);
    try {
      const res = await uploadAndExtractAllegations(file);
      setExtraction(res.data.data);
      const defaultResponses: typeof responses = {};
      res.data.data.allegations.forEach((a) => {
        defaultResponses[a.point_number] = { stance: "deny", grounds: "" };
      });
      setResponses(defaultResponses);
    } catch {
      setError("Failed to extract allegations. Please upload a valid notice PDF.");
    } finally {
      setUploading(false);
    }
  };

  const handleGenerate = async () => {
    if (!extraction) return;
    setGenerating(true);
    setError(null);
    try {
      const allegationResponses: AllegationResponse[] = extraction.allegations.map((a) => ({
        point_number: a.point_number,
        allegation: a.allegation,
        stance: responses[a.point_number]?.stance ?? "deny",
        grounds: responses[a.point_number]?.grounds ?? "",
        legal_basis_claimed: a.legal_basis_claimed,
      }));
      const res = await generateReply(extraction.document_id, allegationResponses);
      setReplyText(res.data.data.reply_text);
      setDraftId(res.data.data.draft_id);
    } catch {
      setError("Failed to generate reply. Please try again.");
    } finally {
      setGenerating(false);
    }
  };

  const handleExport = async () => {
    if (!draftId) return;
    setExporting(true);
    try {
      const res = await exportReplyDocx(draftId);
      const url = URL.createObjectURL(res.data as Blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "notice_reply.docx";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setError("Export failed. Please try again.");
    } finally {
      setExporting(false);
    }
  };

  const respondedCount = Object.values(responses).filter((r) => r.grounds.trim()).length;

  return (
    <>
      <AppTopbar
        eyebrow="AI · Notice reply"
        title={extraction ? `Reply to notice${extraction.notice_date ? ` dated ${extraction.notice_date}` : ""}` : "Reply to Legal Notice"}
        actions={
          extraction && (
            <button
              onClick={replyText ? handleExport : handleGenerate}
              disabled={generating || exporting}
              className="inline-flex h-9 items-center gap-2 rounded-md bg-amber-accent px-4 text-sm font-medium text-amber-accent-fg hover:opacity-90 disabled:opacity-50"
            >
              {generating || exporting
                ? <><Loader2 className="h-4 w-4 animate-spin" /> Processing…</>
                : replyText
                ? <><Download className="h-4 w-4" /> Export .docx</>
                : <><Download className="h-4 w-4" /> Generate full reply</>
              }
            </button>
          )
        }
      />

      <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[320px_1fr]">
        {/* Source notice panel */}
        <aside className="border-r border-border bg-sand/50 p-6">
          <div className="eyebrow">Source notice</div>

          {extraction ? (
            <div className="hairline mt-3 flex items-start gap-3 rounded-md bg-card p-4">
              <FileText className="mt-0.5 h-4 w-4 text-muted-foreground" />
              <div className="min-w-0 text-sm">
                <div className="truncate font-medium">Notice uploaded</div>
                <div className="text-xs text-muted-foreground">{extraction.notice_type}</div>
              </div>
            </div>
          ) : (
            <div className="hairline mt-3 rounded-md bg-card p-4 text-sm text-muted-foreground">
              No notice uploaded yet.
            </div>
          )}

          <input ref={fileRef} type="file" accept=".pdf,.docx" className="hidden" onChange={handleUpload} />
          <button
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
            className="hairline mt-4 flex w-full items-center justify-center gap-2 rounded-md bg-card py-5 text-sm text-muted-foreground hover:bg-background disabled:opacity-50"
          >
            {uploading ? <><Loader2 className="h-4 w-4 animate-spin" /> Extracting…</> : <><Upload className="h-4 w-4" /> {extraction ? "Replace notice" : "Upload notice"}</>}
          </button>

          {extraction && (
            <>
              {extraction.sender && (
                <>
                  <div className="eyebrow mt-8">Sender</div>
                  <div className="mt-2 text-sm font-medium">{extraction.sender}</div>
                </>
              )}
              {extraction.recipient && (
                <>
                  <div className="eyebrow mt-6">On behalf of</div>
                  <div className="mt-2 text-sm font-medium">{extraction.recipient}</div>
                </>
              )}
              <div className="mt-8 rounded-md bg-foreground p-4 text-xs text-background/85">
                <div className="text-[10px] uppercase tracking-[0.18em] text-background/60">AI overview</div>
                <p className="mt-2 leading-relaxed">
                  {extraction.allegations.length} allegation{extraction.allegations.length !== 1 ? "s" : ""} extracted from this {extraction.notice_type}.
                </p>
              </div>
            </>
          )}

          {error && <p className="mt-4 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>}
        </aside>

        {/* Main content */}
        <section className="p-6 lg:p-10">
          {!extraction && !uploading && (
            <div className="flex h-full items-center justify-center text-center text-sm text-muted-foreground">
              <div>
                <Upload className="mx-auto h-10 w-10 opacity-20" />
                <p className="mt-4">Upload a legal notice to get started.</p>
                <p className="mt-1">We'll extract allegations and help you respond to each.</p>
              </div>
            </div>
          )}

          {replyText && (
            <div className="mx-auto max-w-3xl">
              <h2 className="font-serif text-xl">Generated reply</h2>
              <article className="hairline mt-4 rounded-lg bg-card p-8 font-serif text-[15px] leading-7 whitespace-pre-wrap">
                {replyText}
              </article>
            </div>
          )}

          {extraction && !replyText && (
            <div className="mx-auto max-w-3xl">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="font-serif text-xl">{extraction.allegations.length} allegations extracted</h2>
                  <p className="text-sm text-muted-foreground">Respond to each. We assemble the reply.</p>
                </div>
                <div className="text-sm">
                  <span className="font-mono">{respondedCount} / {extraction.allegations.length}</span>
                  <span className="text-muted-foreground"> responded</span>
                </div>
              </div>

              <ol className="mt-8 space-y-4">
                {extraction.allegations.map((a) => (
                  <li key={a.point_number} className="hairline rounded-lg bg-card p-5">
                    <div className="flex items-start gap-4">
                      <div className="font-serif text-3xl text-muted-foreground">{String(a.point_number).padStart(2, "0")}</div>
                      <div className="flex-1">
                        <div className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">Allegation</div>
                        <p className="mt-1 text-sm leading-relaxed">{a.allegation}</p>

                        <div className="mt-3 flex gap-2">
                          {(["admit", "deny", "partial"] as const).map((s) => (
                            <button
                              key={s}
                              onClick={() => setResponses((r) => ({ ...r, [a.point_number]: { ...r[a.point_number], stance: s } }))}
                              className={`hairline rounded-full px-3 py-1 text-xs capitalize ${responses[a.point_number]?.stance === s ? "bg-amber-accent text-amber-accent-fg" : "bg-background"}`}
                            >
                              {s}
                            </button>
                          ))}
                        </div>

                        <div className="mt-4 rounded-md border border-border bg-sand/60 p-3">
                          <div className="flex items-center justify-between">
                            <div className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">Your grounds</div>
                            <button className="inline-flex items-center gap-1 text-xs text-amber-accent underline-offset-4 hover:underline">
                              <Sparkles className="h-3 w-3" /> Suggest
                            </button>
                          </div>
                          <textarea
                            rows={3}
                            value={responses[a.point_number]?.grounds ?? ""}
                            onChange={(e) => setResponses((r) => ({ ...r, [a.point_number]: { ...r[a.point_number], grounds: e.target.value } }))}
                            placeholder="Write your grounds, or tap Suggest…"
                            className="mt-2 w-full resize-none bg-transparent text-sm leading-relaxed placeholder:text-muted-foreground focus:outline-none"
                          />
                        </div>
                      </div>
                      <ChevronRight className="h-4 w-4 text-muted-foreground" />
                    </div>
                  </li>
                ))}
              </ol>

              <button
                onClick={handleGenerate}
                disabled={generating}
                className="mt-8 inline-flex h-11 w-full items-center justify-center gap-2 rounded-md bg-amber-accent text-sm font-medium text-amber-accent-fg hover:opacity-90 disabled:opacity-50"
              >
                {generating ? <><Loader2 className="h-4 w-4 animate-spin" /> Generating reply…</> : <><Sparkles className="h-4 w-4" /> Generate full reply</>}
              </button>
            </div>
          )}
        </section>
      </div>
    </>
  );
}
