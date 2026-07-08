import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { AppTopbar } from "@/components/app/AppTopbar";
import { EcourtsQuickImport } from "@/components/app/EcourtsQuickImport";
import { useAuthStore } from "@/store/authStore";
import { useCaseStore } from "@/store/caseStore";
import {
  FileText,
  MessageSquareReply,
  Search,
  ScrollText,
  BookOpen,
  FileSearch,
  ArrowUpRight,
  Plus,
  Sparkles,
  CalendarClock,
  Briefcase,
  Download,
} from "lucide-react";

export const Route = createFileRoute("/app/")({
  head: () => ({ meta: [{ title: "Dashboard — SuperAdvocate.Ai" }] }),
  component: Dashboard,
});

const AI_TOOLS = [
  {
    icon: FileText,
    label: "Draft a Filing",
    desc: "Write writs, plaints and bail applications from a plain-language brief.",
    to: "/app/drafting",
    cta: "Start drafting",
  },
  {
    icon: Search,
    label: "Research Judgments",
    desc: "Search SC, HC and tribunal judgments by legal concept, not just keywords.",
    to: "/app/research",
    cta: "Search now",
  },
  {
    icon: MessageSquareReply,
    label: "Reply to Notice",
    desc: "Extract every allegation from a legal notice and build a formal reply.",
    to: "/app/notice-reply",
    cta: "Upload notice",
  },
  {
    icon: FileSearch,
    label: "Read a Document",
    desc: "Upload any PDF — get an accurate briefing and ask follow-up questions.",
    to: "/app/documents",
    cta: "Upload PDF",
  },
  {
    icon: ScrollText,
    label: "Summarise a Case",
    desc: "Turn a 60-page judgment into a clean one-pager for your client or brief.",
    to: "/app/summaries",
    cta: "Upload case",
  },
  {
    icon: BookOpen,
    label: "Legal Process Guide",
    desc: "Step-by-step procedure for bail, Section 138, divorce and more.",
    to: "/app/process-guide",
    cta: "Browse",
  },
] as const;

function Dashboard() {
  const user = useAuthStore((s) => s.user);
  const cases = useCaseStore((s) => s.cases);
  const [showQuickImport, setShowQuickImport] = useState(false);
  const [importedCount, setImportedCount] = useState(0);

  const firstName = user?.full_name?.split(" ")[0] ?? "Advocate";
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";

  const activeCases = cases.filter((c) => c.status === "active");
  const upcomingHearings = cases
    .flatMap((c) =>
      c.hearings.map((h) => ({ ...h, caseTitle: c.title, caseNo: c.case_number ?? "", court: c.court }))
    )
    .filter((h) => h.date >= new Date().toISOString().slice(0, 10))
    .sort((a, b) => a.date.localeCompare(b.date))
    .slice(0, 3);

  return (
    <>
      <AppTopbar
        eyebrow={`Chamber · ${user?.firm_name ?? "SuperAdvocate.Ai"}`}
        title={`${greeting}, ${firstName}.`}
        actions={
          <Link
            to="/app/drafting"
            className="inline-flex h-9 items-center gap-2 rounded-md bg-amber-accent px-4 text-sm font-medium text-amber-accent-fg hover:opacity-90"
          >
            <Plus className="h-4 w-4" /> New draft
          </Link>
        }
      />

      {showQuickImport && (
        <EcourtsQuickImport
          onClose={() => setShowQuickImport(false)}
          onImported={(n) => { setImportedCount((p) => p + n); setShowQuickImport(false); }}
        />
      )}

      <div className="flex-1 overflow-y-auto px-6 py-8 lg:px-10">

        {/* ── eCourts import banner (shown when no cases imported yet) */}
        {cases.length === 0 && importedCount === 0 && (
          <div className="mb-7 flex items-start gap-4 rounded-xl border border-amber-accent/30 bg-amber-accent/5 px-5 py-5">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-amber-accent/15">
              <Download className="h-5 w-5 text-amber-accent" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-foreground">Your eCourts case data is ready to pull</p>
              <p className="mt-0.5 text-xs text-muted-foreground leading-relaxed">
                Import your pending cases to track every hearing, get deadline reminders,
                and draft filings — no manual data entry needed.
              </p>
            </div>
            <button
              onClick={() => setShowQuickImport(true)}
              className="shrink-0 inline-flex h-9 items-center gap-2 rounded-md bg-amber-accent px-4 text-sm font-medium text-amber-accent-fg hover:opacity-90 whitespace-nowrap"
            >
              Connect eCourts →
            </button>
          </div>
        )}

        {importedCount > 0 && (
          <div className="mb-7 flex items-center gap-3 rounded-xl border border-green-500/30 bg-green-500/5 px-5 py-3 text-sm">
            <div className="h-2 w-2 rounded-full bg-green-500" />
            <span className="text-foreground"><strong>{importedCount}</strong> cases imported from eCourts. Hearing dates sync automatically.</span>
          </div>
        )}

        {/* ── AI Workspace ── hero section */}
        <section>
          <div className="mb-5 flex items-end justify-between">
            <div>
              <div className="eyebrow flex items-center gap-1.5 text-amber-accent">
                <Sparkles className="h-3 w-3" /> AI workspace
              </div>
              <h2 className="mt-1 font-serif text-xl text-foreground">
                What would you like to work on?
              </h2>
            </div>
            <div className="text-xs text-muted-foreground">Beta · unlimited AI access</div>
          </div>

          <div className="grid gap-px overflow-hidden rounded-xl bg-border sm:grid-cols-2 lg:grid-cols-3">
            {AI_TOOLS.map((t) => (
              <Link
                key={t.label}
                to={t.to}
                className="group flex flex-col gap-3 bg-card p-5 transition-colors hover:bg-amber-accent-subtle"
              >
                <div className="flex items-start justify-between">
                  <div className="flex h-9 w-9 items-center justify-center rounded-md bg-amber-accent/10">
                    <t.icon className="h-4 w-4 text-amber-accent" />
                  </div>
                  <ArrowUpRight className="h-3.5 w-3.5 text-amber-accent opacity-0 transition-opacity group-hover:opacity-100" />
                </div>
                <div>
                  <div className="font-serif text-[15px] text-foreground">{t.label}</div>
                  <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{t.desc}</p>
                </div>
                <div className="mt-auto text-xs font-medium text-amber-accent opacity-0 transition-opacity group-hover:opacity-100">
                  {t.cta} →
                </div>
              </Link>
            ))}
          </div>
        </section>

        {/* ── Practice ── secondary section */}
        <div className="mt-10 grid gap-6 lg:grid-cols-[1fr_300px]">

          {/* Upcoming hearings */}
          <section>
            <div className="mb-3 flex items-center justify-between">
              <h3 className="font-serif text-base text-foreground">Upcoming hearings</h3>
              <Link to="/app/hearings" className="text-xs text-muted-foreground hover:text-foreground">
                View all →
              </Link>
            </div>
            <div className="hairline rounded-xl bg-card">
              {upcomingHearings.length === 0 ? (
                <div className="flex flex-col items-center gap-3 py-10 text-center">
                  <CalendarClock className="h-8 w-8 text-border" />
                  <p className="text-sm text-muted-foreground">No hearings scheduled yet.</p>
                  <Link to="/app/cases" className="text-xs font-medium text-amber-accent hover:opacity-80">
                    Add a matter to track hearings →
                  </Link>
                </div>
              ) : (
                <ul className="divide-y divide-border">
                  {upcomingHearings.map((h) => (
                    <li key={h.id} className="flex items-center gap-4 px-5 py-4">
                      <div className="w-24 font-mono text-sm text-muted-foreground">{h.date}</div>
                      <div className="min-w-0 flex-1">
                        <div className="truncate text-sm font-medium text-foreground">{h.caseTitle}</div>
                        <div className="text-xs text-muted-foreground">{h.caseNo} · {h.court}</div>
                      </div>
                      <Link to="/app/cases" className="text-xs text-foreground underline-offset-4 hover:underline">
                        Open
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </section>

          {/* Right sidebar: stats + active matters */}
          <aside className="space-y-5">

            {/* Today — compact 2-stat strip */}
            <div className="grid grid-cols-2 gap-px overflow-hidden rounded-xl bg-border">
              {[
                [String(upcomingHearings.length), "hearings today"],
                [String(activeCases.length), "active matters"],
              ].map(([n, l]) => (
                <div key={l} className="bg-card px-4 py-4">
                  <div className="font-serif text-2xl">{n}</div>
                  <div className="mt-0.5 text-[10px] uppercase tracking-[0.14em] text-muted-foreground">{l}</div>
                </div>
              ))}
            </div>

            {/* Active matters */}
            <div className="hairline overflow-hidden rounded-xl bg-card">
              <div className="flex items-center justify-between border-b border-border px-4 py-3">
                <span className="text-sm font-medium text-foreground">Active matters</span>
                <Link
                  to="/app/cases"
                  className="flex items-center gap-1 text-xs font-medium text-amber-accent hover:opacity-80"
                >
                  <Plus className="h-3 w-3" /> Add
                </Link>
              </div>
              {activeCases.length === 0 ? (
                <div className="flex flex-col items-center gap-2 py-8 text-center">
                  <Briefcase className="h-7 w-7 text-border" />
                  <p className="text-xs text-muted-foreground">No active cases yet.</p>
                  <Link to="/app/cases" className="text-xs font-medium text-amber-accent hover:opacity-80">
                    Add your first matter →
                  </Link>
                </div>
              ) : (
                <ul className="divide-y divide-border text-sm">
                  {activeCases.slice(0, 5).map((c) => (
                    <li key={c.id} className="px-4 py-3">
                      <div className="truncate font-medium">{c.title}</div>
                      <div className="text-xs text-muted-foreground">{c.court}</div>
                    </li>
                  ))}
                </ul>
              )}
            </div>

          </aside>
        </div>
      </div>
    </>
  );
}
