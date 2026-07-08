import { createFileRoute, Link } from "@tanstack/react-router";
import { SiteHeader } from "@/components/marketing/SiteHeader";
import { SiteFooter } from "@/components/marketing/SiteFooter";
import {
  FileText,
  Search,
  MessageSquareReply,
  ScrollText,
  Briefcase,
  CalendarClock,
  BookOpen,
  FileSearch,
  ArrowUpRight,
  Scale,
  ShieldCheck,
  Clock3,
} from "lucide-react";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "SuperAdvocate.Ai — AI built for India's lawyers" },
      { name: "description", content: "Draft court filings, reply to notices, research judgments, and run your practice — purpose-built for solo lawyers and small law firms across India." },
      { property: "og:title", content: "SuperAdvocate.Ai — AI built for India's lawyers" },
      { property: "og:description", content: "Draft court filings, reply to notices, research judgments, and run your practice — purpose-built for solo lawyers and small law firms across India." },
    ],
  }),
  component: Landing,
});

const FEATURES = [
  { icon: FileText, title: "AI court filing drafts", body: "Generate writs, plaints, applications and replies from a plain-language brief or an existing draft." },
  { icon: FileSearch, title: "Read & chat with PDFs", body: "Upload any legal PDF. Get a precise summary and ask follow-up questions grounded in the document." },
  { icon: MessageSquareReply, title: "Legal notice reply", body: "We extract each allegation, you respond, and we assemble a court-ready reply." },
  { icon: Search, title: "Judgment & citation search", body: "Search across your own files and public Indian judgments — Supreme Court, High Courts, and tribunals." },
  { icon: ScrollText, title: "One-page case summaries", body: "Turn a 60-page judgment into a clean one-pager you can hand to a client or a partner." },
  { icon: Briefcase, title: "Case & fee management", body: "Parties, hearings, notes, and fee instalments — tracked in ₹ with GST-ready invoices." },
  { icon: CalendarClock, title: "Hearings from eCourts", body: "Auto-pull next hearing dates and push WhatsApp reminders to clients and juniors." },
  { icon: BookOpen, title: "Step-by-step process guides", body: "Walk through bail applications, Section 138, divorce filings and more — step by step." },
] as const;

function Landing() {
  return (
    <div className="min-h-screen bg-background">
      <SiteHeader />

      {/* Hero */}
      <section className="relative overflow-hidden border-b border-border bg-paper">
        <div className="pointer-events-none absolute inset-0 opacity-[0.04]" style={{
          backgroundImage:
            "linear-gradient(var(--color-foreground) 1px, transparent 1px), linear-gradient(90deg, var(--color-foreground) 1px, transparent 1px)",
          backgroundSize: "48px 48px",
        }} />
        <div className="relative mx-auto grid max-w-7xl gap-16 px-6 py-20 lg:grid-cols-[1.1fr_0.9fr] lg:py-28">
          <div>
            <div className="eyebrow inline-flex items-center gap-2 text-amber-accent">
              <Scale className="h-3 w-3" /> Built for Indian advocates
            </div>
            <h1 className="serif-display mt-6 text-5xl text-foreground sm:text-6xl lg:text-[78px]">
              The quiet AI <em className="font-serif italic">chamber</em> behind your practice.
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-relaxed text-muted-foreground">
              Draft filings, reply to notices, research citations and manage cases — in one workspace
              made for solo lawyers and small firms across India.
            </p>
            <div className="mt-9 flex flex-wrap items-center gap-3">
              <Link
                to="/auth"
                search={{ mode: "signup" }}
                className="inline-flex h-12 items-center gap-2 rounded-md bg-amber-accent px-6 text-sm font-medium text-amber-accent-fg transition-opacity hover:opacity-90"
              >
                Start 14-day free trial <ArrowUpRight className="h-4 w-4" />
              </Link>
              <Link
                to="/features"
                className="inline-flex h-12 items-center rounded-md border border-border bg-card px-6 text-sm font-medium text-foreground hover:bg-sand"
              >
                See every feature
              </Link>
            </div>
            <div className="mt-10 flex flex-wrap items-center gap-x-8 gap-y-3 text-xs text-muted-foreground">
              <div className="flex items-center gap-2"><ShieldCheck className="h-3.5 w-3.5" /> Data stays in India</div>
              <div className="flex items-center gap-2"><Clock3 className="h-3.5 w-3.5" /> Setup in 4 minutes</div>
              <div>No credit card required</div>
            </div>
          </div>

          {/* Visual: stacked document mock */}
          <div className="relative">
            <div className="hairline relative rounded-xl bg-card p-6 shadow-[0_30px_60px_-30px_rgba(20,20,20,0.25)]">
              <div className="eyebrow">In the High Court of Karnataka</div>
              <div className="mt-2 font-serif text-xl leading-snug text-foreground">
                Writ Petition under Article 226<br />
                <span className="text-muted-foreground">— Ananya Rao v. State of Karnataka</span>
              </div>
              <div className="mt-5 space-y-3 text-sm leading-relaxed text-foreground/85">
                <p>1. The Petitioner is a citizen of India residing at the address mentioned in the cause title and is engaged in the practice of law…</p>
                <p>2. The Respondent No. 1 is the State of Karnataka, represented through the Principal Secretary, Department of…</p>
                <p>3. The facts giving rise to the present petition are as follows: <span className="bg-amber-accent/20 px-1">on 12/03/2026, an order was passed by Respondent No. 2</span>…</p>
              </div>
              <div className="mt-6 flex items-center justify-between border-t border-border pt-4 text-xs text-muted-foreground">
                <span>Draft v3 · auto-saved 12:14</span>
                <span className="rounded-full bg-foreground px-2 py-0.5 text-background">AI suggested</span>
              </div>
            </div>
            <div className="hairline absolute -bottom-8 -left-6 hidden w-56 rounded-lg bg-sand p-4 shadow-lg md:block">
              <div className="eyebrow">Next hearing</div>
              <div className="mt-1 font-serif text-lg">24/06/2026</div>
              <div className="text-xs text-muted-foreground">Court Hall 7, 11:30 AM</div>
            </div>
            <div className="hairline absolute -right-4 top-12 hidden w-52 rounded-lg bg-foreground p-4 text-background shadow-lg md:block">
              <div className="text-[10px] uppercase tracking-[0.18em] text-background/60">Citation found</div>
              <div className="mt-1 font-serif text-base">(2023) 4 SCC 615</div>
              <div className="text-xs text-background/70">Maneka Gandhi principle, para 56</div>
            </div>
          </div>
        </div>
      </section>

      {/* Stats strip */}
      <section className="border-b border-border bg-foreground text-background">
        <div className="mx-auto grid max-w-7xl grid-cols-2 gap-y-8 px-6 py-10 md:grid-cols-4">
          {[
            ["3,200+", "advocates onboarded"],
            ["1.4 cr+", "judgments indexed"],
            ["68%", "less time per draft"],
            ["28", "High Courts supported"],
          ].map(([k, v]) => (
            <div key={v}>
              <div className="font-serif text-3xl text-amber-accent">{k}</div>
              <div className="mt-1 text-xs uppercase tracking-[0.18em] text-background/60">{v}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Features grid */}
      <section className="mx-auto max-w-7xl px-6 py-24">
        <div className="grid gap-12 lg:grid-cols-[0.9fr_1.1fr]">
          <div>
            <div className="eyebrow">Capabilities</div>
            <h2 className="serif-display mt-3 text-4xl text-foreground sm:text-5xl">
              Every part of the brief, drafted with you.
            </h2>
            <p className="mt-5 max-w-md text-muted-foreground">
              SuperAdvocate.Ai is not a generic chatbot. It understands Indian procedure, citation
              style, and the way a chamber actually runs.
            </p>
            <Link to="/features" className="mt-8 inline-flex items-center gap-1 text-sm font-medium text-foreground underline-offset-4 hover:underline">
              Read the full capability list <ArrowUpRight className="h-4 w-4" />
            </Link>
          </div>
          <div className="grid gap-px overflow-hidden rounded-lg bg-border sm:grid-cols-2">
            {FEATURES.map((f) => (
              <div key={f.title} className="bg-card p-6">
                <f.icon className="h-5 w-5 text-amber-accent" />
                <div className="mt-4 font-serif text-lg leading-snug text-foreground">{f.title}</div>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{f.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Workflow */}
      <section className="border-y border-border bg-sand">
        <div className="mx-auto max-w-7xl px-6 py-24">
          <div className="eyebrow">How a typical morning looks</div>
          <h2 className="serif-display mt-3 max-w-3xl text-4xl text-foreground sm:text-5xl">
            From a client's WhatsApp to a filed reply, before lunch.
          </h2>
          <ol className="mt-14 grid gap-px overflow-hidden rounded-lg bg-border md:grid-cols-4">
            {[
              ["09:12", "Client forwards a Section 138 notice on WhatsApp."],
              ["09:20", "Upload PDF. AI lists each allegation and suggests responses."],
              ["10:05", "You approve the reply, citations are auto-checked."],
              ["11:30", "Reply dispatched. Hearing added. Client gets a reminder."],
            ].map(([t, d], i) => (
              <li key={t} className="bg-sand p-6">
                <div className="font-serif text-3xl text-amber-accent">{String(i + 1).padStart(2, "0")}</div>
                <div className="mt-3 font-mono text-xs text-muted-foreground">{t} IST</div>
                <p className="mt-2 text-sm leading-relaxed text-foreground/85">{d}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* Testimonial */}
      <section className="mx-auto max-w-5xl px-6 py-24 text-center">
        <div className="eyebrow">From the bar</div>
        <blockquote className="serif-display mt-6 text-3xl text-foreground sm:text-4xl">
          “It does what a brilliant junior would do — at 6 AM, on a Sunday, without complaining.
          My drafting time has roughly halved.”
        </blockquote>
        <div className="mt-8 text-sm text-muted-foreground">
          Adv. Mohan Iyer · Madras High Court · 17 years at the bar
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-border bg-foreground text-background">
        <div className="mx-auto flex max-w-7xl flex-col items-start justify-between gap-8 px-6 py-20 md:flex-row md:items-center">
          <div>
            <h2 className="serif-display text-4xl sm:text-5xl">Try it on a real brief this week.</h2>
            <p className="mt-3 max-w-xl text-background/70">
              Free for 14 days. No card. Full access to drafting, research, notices and case management.
            </p>
          </div>
          <div className="flex gap-3">
            <Link
              to="/auth"
              search={{ mode: "signup" }}
              className="inline-flex h-12 items-center rounded-md bg-amber-accent px-6 text-sm font-medium text-amber-accent-fg hover:opacity-90"
            >
              Start free trial
            </Link>
            <Link
              to="/contact"
              className="inline-flex h-12 items-center rounded-md border border-background/30 px-6 text-sm font-medium text-background hover:bg-background/10"
            >
              Talk to us
            </Link>
          </div>
        </div>
      </section>

      <SiteFooter />
    </div>
  );
}
