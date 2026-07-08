import { createFileRoute, Link } from "@tanstack/react-router";
import { SiteHeader } from "@/components/marketing/SiteHeader";
import { SiteFooter } from "@/components/marketing/SiteFooter";
import {
  FileText, FileSearch, MessageSquareReply, Search, ScrollText,
  Briefcase, CalendarClock, BookOpen, ShieldCheck, Smartphone, Languages, Database,
} from "lucide-react";

export const Route = createFileRoute("/features")({
  head: () => ({
    meta: [
      { title: "Features — SuperAdvocate.Ai" },
      { name: "description", content: "AI drafting, document chat, notice replies, judgment research, case management, hearings via eCourts, WhatsApp reminders and more." },
      { property: "og:title", content: "Features — SuperAdvocate.Ai" },
      { property: "og:description", content: "Every capability built into the SuperAdvocate.Ai workspace for Indian advocates." },
    ],
  }),
  component: FeaturesPage,
});

const GROUPS = [
  {
    eyebrow: "Drafting",
    items: [
      { icon: FileText, title: "AI court filing drafts", body: "Generate writs, plaints, applications, replies, affidavits and bail applications from a plain-language description or by improving an uploaded draft." },
      { icon: MessageSquareReply, title: "Notice reply assistant", body: "Upload a legal notice. We extract every allegation, you respond to each, and we assemble a court-ready reply that you can edit and export." },
    ],
  },
  {
    eyebrow: "Research",
    items: [
      { icon: FileSearch, title: "Chat with any legal PDF", body: "Upload pleadings, judgments, contracts or notices. Get a faithful summary and ask follow-up questions grounded in the document." },
      { icon: Search, title: "Judgment & citation search", body: "Search across your own files and a continuously updated index of Supreme Court, High Court and tribunal judgments." },
      { icon: ScrollText, title: "One-page case summaries", body: "Turn a long judgment into a structured one-pager: facts, issues, holding, ratio, and quotable paragraphs." },
    ],
  },
  {
    eyebrow: "Practice management",
    items: [
      { icon: Briefcase, title: "Cases, parties & fees", body: "Track parties, opposing counsel, fees in ₹ with instalments received, GST-ready invoices and outstanding amounts." },
      { icon: CalendarClock, title: "Hearings & deadlines", body: "Pull next dates from eCourts where available. Set limitation reminders. See your week at a glance." },
      { icon: Smartphone, title: "WhatsApp reminders", body: "Auto-nudge clients before hearings, document submissions and fee dues — in the language they understand." },
      { icon: BookOpen, title: "Step-by-step process guides", body: "Bail, Section 138, divorce, consumer cases, RERA, cheque dishonour — guided checklists for every common matter." },
    ],
  },
  {
    eyebrow: "Trust & privacy",
    items: [
      { icon: ShieldCheck, title: "Data stays in India", body: "All matter data is stored in Indian data centres with at-rest encryption. You control sharing per matter." },
      { icon: Database, title: "Your files, your model", body: "Your uploads are never used to train shared models. You can purge a matter at any time." },
      { icon: Languages, title: "Hindi + English + 6 more", body: "Drafts and conversations supported in English, Hindi, Kannada, Tamil, Telugu, Marathi, Bengali and Gujarati." },
    ],
  },
] as const;

function FeaturesPage() {
  return (
    <div className="min-h-screen bg-background">
      <SiteHeader />
      <section className="border-b border-border bg-paper">
        <div className="mx-auto max-w-7xl px-6 py-20">
          <div className="eyebrow">Features</div>
          <h1 className="serif-display mt-4 max-w-3xl text-5xl text-foreground sm:text-6xl">
            One workspace, the whole brief.
          </h1>
          <p className="mt-6 max-w-2xl text-lg text-muted-foreground">
            SuperAdvocate.Ai brings drafting, research and case management together — without the
            clutter of ten different tools.
          </p>
        </div>
      </section>

      {GROUPS.map((g, gi) => (
        <section key={g.eyebrow} className={gi % 2 === 1 ? "bg-sand border-y border-border" : ""}>
          <div className="mx-auto grid max-w-7xl gap-12 px-6 py-20 lg:grid-cols-[0.7fr_1.3fr]">
            <div>
              <div className="eyebrow">{g.eyebrow}</div>
              <h2 className="serif-display mt-3 text-3xl text-foreground sm:text-4xl">{g.eyebrow}</h2>
            </div>
            <div className="grid gap-px overflow-hidden rounded-lg bg-border sm:grid-cols-2">
              {g.items.map((it) => (
                <div key={it.title} className={`p-6 ${gi % 2 === 1 ? "bg-sand" : "bg-card"}`}>
                  <it.icon className="h-5 w-5" />
                  <div className="mt-4 font-serif text-lg leading-snug">{it.title}</div>
                  <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{it.body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      ))}

      <section className="border-t border-border bg-foreground text-background">
        <div className="mx-auto flex max-w-7xl flex-col items-start justify-between gap-6 px-6 py-16 md:flex-row md:items-center">
          <h2 className="serif-display text-3xl sm:text-4xl">Ready when you are.</h2>
          <Link to="/auth" search={{ mode: "signup" }} className="inline-flex h-12 items-center rounded-md bg-background px-6 text-sm font-medium text-foreground hover:bg-sand">
            Start free trial
          </Link>
        </div>
      </section>
      <SiteFooter />
    </div>
  );
}
