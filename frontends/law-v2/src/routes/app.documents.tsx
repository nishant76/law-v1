import { createFileRoute } from "@tanstack/react-router";
import { AppTopbar } from "@/components/app/AppTopbar";
import { useState, useRef, useEffect } from "react";
import { streamExtractUpload, streamChatWithDocument } from "@/api/extract";
import {
  Upload, Send, FileText, Sparkles, Loader2,
  CheckCircle, XCircle, MessageSquare, FileIcon,
} from "lucide-react";
import MarkdownText from "@/components/ui/MarkdownText";

export const Route = createFileRoute("/app/documents")({
  head: () => ({ meta: [{ title: "Documents — SuperAdvocate.Ai" }] }),
  component: Documents,
});

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface CaseSnapshot {
  document_type?: string;
  outcome?: string;
  court?: string;
  judge?: string;
  date?: string;
  case_no?: string;
  appellant?: string;
  respondent?: string;
  [key: string]: unknown;
}

const JUDGE_TITLE_RE = /^(hon'?ble\.?\s+|justice\s+|mr\.?\s+|mrs\.?\s+|ms\.?\s+|dr\.?\s+|shri\s+|smt\.?\s+)+/i;
function stripJudgeTitles(name: string) { return name.replace(JUDGE_TITLE_RE, "").trim(); }

function formatDate(raw: string): string {
  const dotMatch = raw.match(/^(\d{1,2})\.(\d{1,2})\.(\d{4})$/);
  if (dotMatch) {
    const [, d, m, y] = dotMatch;
    const dt = new Date(+y, +m - 1, +d);
    if (!isNaN(dt.getTime())) return dt.toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" });
  }
  const dashMatch = raw.match(/^(\d{1,2})-(\d{1,2})-(\d{4})$/);
  if (dashMatch) {
    const [, d, m, y] = dashMatch;
    const dt = new Date(+y, +m - 1, +d);
    if (!isNaN(dt.getTime())) return dt.toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" });
  }
  const dt = new Date(raw);
  if (!isNaN(dt.getTime())) return dt.toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" });
  return raw;
}

function CaseSnapshotCard({ snap }: { snap: CaseSnapshot }) {
  const outcome = (snap.outcome ?? "").toLowerCase();
  const isAllowed = outcome.includes("allow");
  const isDismissed = outcome.includes("dismiss");
  return (
    <div className="hairline rounded-lg bg-card p-5 mb-5">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          {snap.document_type && <div className="eyebrow mb-1">{snap.document_type}</div>}
          {snap.case_no && <div className="font-mono text-xs text-muted-foreground">{snap.case_no}</div>}
        </div>
        {(isAllowed || isDismissed) && (
          <div className={`flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${isAllowed ? "bg-emerald-50 text-emerald-700" : "bg-destructive/10 text-destructive"}`}>
            {isAllowed ? <><CheckCircle className="h-3.5 w-3.5" /> Allowed</> : <><XCircle className="h-3.5 w-3.5" /> Dismissed</>}
          </div>
        )}
      </div>
      <div className="mt-4 grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
        {snap.court && (
          <div className="col-span-2">
            <div className="eyebrow mb-0.5 text-[10px]">Court</div>
            <div className="text-foreground">{snap.court}</div>
          </div>
        )}
        {snap.judge && (
          <div>
            <div className="eyebrow mb-0.5 text-[10px]">Judge</div>
            <div className="text-foreground">{stripJudgeTitles(snap.judge)}</div>
          </div>
        )}
        {snap.date && (
          <div>
            <div className="eyebrow mb-0.5 text-[10px]">Date</div>
            <div className="text-foreground">{formatDate(snap.date)}</div>
          </div>
        )}
        {snap.appellant && (
          <div>
            <div className="eyebrow mb-0.5 text-[10px]">Appellant</div>
            <div className="text-foreground">{snap.appellant}</div>
          </div>
        )}
        {snap.respondent && (
          <div>
            <div className="eyebrow mb-0.5 text-[10px]">Respondent</div>
            <div className="text-foreground">{snap.respondent}</div>
          </div>
        )}
      </div>
    </div>
  );
}

const QUICK_PROMPTS = [
  "Detailed Analysis",
  "Appeal Grounds",
  "Case Timeline",
  "Key Citations",
  "Final Order",
  "Counter-arguments",
];

function Documents() {
  const fileRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const isDragging = useRef(false);
  const pdfUrlRef = useRef<string | null>(null);

  const [splitPct, setSplitPct] = useState(60);
  const [uploading, setUploading] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);
  const [streamText, setStreamText] = useState("");
  const [snapshot, setSnapshot] = useState<CaseSnapshot | null>(null);
  const [documentId, setDocumentId] = useState<string | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"chat" | "pdf">("chat");
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // SNAPSHOT streaming refs
  const snapshotParsedRef = useRef(false);
  const snapshotBufRef = useRef("");
  const tokenBufRef = useRef("");
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Drag-to-resize ────────────────────────────────────────────────────
  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!isDragging.current || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const pct = ((e.clientX - rect.left) / rect.width) * 100;
      setSplitPct(Math.min(Math.max(pct, 25), 78));
    };
    const onMouseUp = () => {
      if (!isDragging.current) return;
      isDragging.current = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };
  }, []);

  const handleDividerMouseDown = (e: React.MouseEvent) => {
    isDragging.current = true;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    e.preventDefault();
  };

  // ── Token flush timer ────────────────────────────────────────────────
  const startFlushTimer = () => {
    if (timerRef.current) return;
    timerRef.current = setInterval(() => {
      const chunk = tokenBufRef.current;
      if (chunk) {
        tokenBufRef.current = "";
        setStreamText(prev => prev + chunk);
      }
    }, 50);
  };

  const stopFlushTimer = () => {
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
    const chunk = tokenBufRef.current;
    if (chunk) { tokenBufRef.current = ""; setStreamText(prev => prev + chunk); }
  };

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (pdfUrlRef.current) URL.revokeObjectURL(pdfUrlRef.current);
    };
  }, []);

  // ── SNAPSHOT token handler ───────────────────────────────────────────
  const handleToken = (token: string) => {
    if (!snapshotParsedRef.current) {
      snapshotBufRef.current += token;
      const nlIdx = snapshotBufRef.current.indexOf("\n");
      if (nlIdx !== -1) {
        const firstLine = snapshotBufRef.current.slice(0, nlIdx);
        const rest = snapshotBufRef.current.slice(nlIdx + 1);
        snapshotParsedRef.current = true;
        snapshotBufRef.current = "";
        if (firstLine.startsWith("SNAPSHOT:")) {
          try { setSnapshot(JSON.parse(firstLine.slice("SNAPSHOT:".length))); } catch {}
          tokenBufRef.current += rest;
        } else {
          tokenBufRef.current += firstLine + "\n" + rest;
        }
      }
      return;
    }
    tokenBufRef.current += token;
  };

  // ── File upload ───────────────────────────────────────────────────────
  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Swap object URL (revoke old, create new)
    if (pdfUrlRef.current) URL.revokeObjectURL(pdfUrlRef.current);
    const newUrl = URL.createObjectURL(file);
    pdfUrlRef.current = newUrl;
    setPdfUrl(newUrl);

    setUploading(true);
    setError(null);
    setStreamText("");
    setSnapshot(null);
    setMessages([]);
    setDocumentId(null);
    setFileName(file.name);
    snapshotParsedRef.current = false;
    snapshotBufRef.current = "";
    tokenBufRef.current = "";

    startFlushTimer();

    await streamExtractUpload(
      file,
      handleToken,
      () => {},
      (result) => { setDocumentId(result.document_id); stopFlushTimer(); setUploading(false); },
      (_code, message) => { setError(message); stopFlushTimer(); setUploading(false); },
      (docId) => { setDocumentId(docId); },
    );

    stopFlushTimer();
    setUploading(false);
    e.target.value = "";
  };

  // ── Chat ──────────────────────────────────────────────────────────────
  const handleAsk = async (q?: string) => {
    const text = (q ?? question).trim();
    if (!text || !documentId) return;
    setActiveTab("chat");
    const newMessages: Message[] = [...messages, { role: "user", content: text }];
    setMessages(newMessages);
    setQuestion("");
    setChatLoading(true);
    let answer = "";
    setMessages([...newMessages, { role: "assistant", content: "" }]);
    await streamChatWithDocument(
      documentId,
      newMessages,
      (token) => { answer += token; setMessages([...newMessages, { role: "assistant", content: answer }]); },
      () => setChatLoading(false),
      (msg) => { setError(msg); setChatLoading(false); },
    );
    setChatLoading(false);
  };

  const hasContent = !!fileName || uploading;

  return (
    <>
      <AppTopbar eyebrow="AI · Documents" title="Read & chat with a legal PDF" />

      {/* ── Two-panel resizable layout ─────────────────────────────── */}
      <div ref={containerRef} className="flex min-h-0 flex-1 overflow-hidden">

        {/* ── Left: Summary ─────────────────────────────────────────── */}
        <section
          style={{ width: `${splitPct}%` }}
          className="flex flex-col overflow-hidden bg-sand/50"
        >
          <input ref={fileRef} type="file" accept=".pdf,.docx" className="hidden" onChange={handleUpload} />

          <div className="flex-1 overflow-y-auto p-6 lg:p-8">
            {!hasContent ? (
              <div className="flex h-full items-center justify-center">
                <button
                  onClick={() => fileRef.current?.click()}
                  className="hairline flex flex-col items-center gap-4 rounded-xl bg-card px-16 py-14 text-muted-foreground hover:bg-background"
                >
                  <Upload className="h-8 w-8 opacity-50" />
                  <div className="text-sm font-medium">Upload a legal PDF</div>
                  <div className="text-xs">Judgment, contract, notice, or any legal document</div>
                </button>
              </div>
            ) : (
              <>
                <div className="mb-4 flex items-center justify-between gap-3">
                  <div className="flex min-w-0 items-center gap-3 text-sm">
                    <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
                    <span className="truncate font-medium">{fileName}</span>
                    {uploading && <Loader2 className="h-4 w-4 shrink-0 animate-spin text-muted-foreground" />}
                  </div>
                  <button
                    onClick={() => fileRef.current?.click()}
                    className="hairline shrink-0 rounded-md bg-card px-3 py-1.5 text-xs text-muted-foreground hover:bg-background"
                  >
                    Upload another
                  </button>
                </div>

                {snapshot && <CaseSnapshotCard snap={snapshot} />}

                {!snapshot && !streamText && uploading && (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" /> Extracting document…
                  </div>
                )}

                {streamText && (
                  <div className="hairline rounded-md bg-card p-6">
                    <MarkdownText text={streamText} />
                  </div>
                )}

                {error && (
                  <p className="mt-4 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>
                )}
              </>
            )}
          </div>
        </section>

        {/* ── Drag divider ──────────────────────────────────────────── */}
        <div
          onMouseDown={handleDividerMouseDown}
          className="group relative z-10 flex w-[5px] shrink-0 cursor-col-resize flex-col items-center justify-center bg-border hover:bg-accent/60 transition-colors"
        >
          <div className="h-10 w-[3px] rounded-full bg-muted-foreground/25 group-hover:bg-foreground/30 transition-colors" />
        </div>

        {/* ── Right: Chat + PDF ─────────────────────────────────────── */}
        <section
          style={{ width: `${100 - splitPct}%` }}
          className="flex flex-col overflow-hidden bg-background"
        >
          {/* Tab bar */}
          <div className="flex shrink-0 border-b border-border">
            <TabButton active={activeTab === "chat"} onClick={() => setActiveTab("chat")} icon={<MessageSquare className="h-3.5 w-3.5" />} label="Chat" />
            <TabButton active={activeTab === "pdf"} onClick={() => setActiveTab("pdf")} icon={<FileIcon className="h-3.5 w-3.5" />} label="PDF" />
          </div>

          {/* ── Chat tab — always mounted so scroll position is kept ── */}
          <div className={`flex min-h-0 flex-1 flex-col ${activeTab !== "chat" ? "hidden" : ""}`}>
            {/* Quick prompts — top of chat */}
            {documentId && (
              <div className="shrink-0 border-b border-border bg-sand/40 px-4 py-2.5">
                <div className="flex flex-wrap items-center gap-2">
                  <Sparkles className="h-3 w-3 shrink-0 text-amber-accent" />
                  {QUICK_PROMPTS.map((s) => (
                    <button
                      key={s}
                      onClick={() => handleAsk(s)}
                      className="rounded-full border border-border bg-card px-3 py-0.5 text-[11px] text-muted-foreground transition-colors hover:border-foreground/30 hover:text-foreground"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Messages */}
            <div className="flex-1 overflow-y-auto space-y-4 p-4">
              {!documentId && (
                <p className="text-sm text-muted-foreground">Upload a document to start chatting.</p>
              )}
              {messages.map((m, i) => (
                <ChatBubble key={i} who={m.role === "user" ? "you" : "ai"} text={m.content} />
              ))}
              {chatLoading && (
                <div className="mr-8 hairline rounded-lg rounded-tl-sm bg-sand p-3 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                </div>
              )}
            </div>

            {/* Input */}
            <div className="shrink-0 border-t border-border p-4">
              <div className="hairline flex items-end gap-2 rounded-md bg-card p-2">
                <textarea
                  rows={2}
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleAsk(); } }}
                  placeholder={documentId ? "Ask anything about this document…" : "Upload a document first"}
                  disabled={!documentId}
                  className="flex-1 resize-none bg-transparent p-2 text-sm placeholder:text-muted-foreground focus:outline-none disabled:opacity-50"
                />
                <button
                  onClick={() => handleAsk()}
                  disabled={!documentId || !question.trim() || chatLoading}
                  className="inline-flex h-9 items-center gap-2 rounded-md bg-amber-accent px-3 text-sm text-amber-accent-fg disabled:opacity-50"
                >
                  <Send className="h-3.5 w-3.5" /> Ask
                </button>
              </div>
            </div>
          </div>

          {/* ── PDF tab — always mounted, iframe keeps scroll/page ─── */}
          <div className={`flex min-h-0 flex-1 flex-col ${activeTab !== "pdf" ? "hidden" : ""}`}>
            {pdfUrl ? (
              <iframe
                src={pdfUrl}
                className="flex-1 w-full border-0"
                title="PDF viewer"
              />
            ) : (
              <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">
                Upload a document to view the PDF here.
              </div>
            )}
          </div>
        </section>
      </div>
    </>
  );
}

function TabButton({ active, onClick, icon, label }: { active: boolean; onClick: () => void; icon: React.ReactNode; label: string }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 border-b-2 px-5 py-3 text-sm font-medium transition-colors ${
        active
          ? "border-amber-accent text-amber-accent"
          : "border-transparent text-muted-foreground hover:text-foreground"
      }`}
    >
      {icon} {label}
    </button>
  );
}

function ChatBubble({ who, text }: { who: "you" | "ai"; text: string }) {
  if (who === "you") {
    return <div className="ml-8 rounded-lg rounded-tr-sm bg-foreground p-3 text-sm text-background">{text}</div>;
  }
  return (
    <div className="mr-8 hairline rounded-lg rounded-tl-sm bg-sand p-4">
      <MarkdownText text={text} />
    </div>
  );
}
