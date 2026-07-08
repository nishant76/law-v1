import { createFileRoute } from "@tanstack/react-router";
import { AppTopbar } from "@/components/app/AppTopbar";
import { ChevronRight, Check } from "lucide-react";

export const Route = createFileRoute("/app/process-guide")({
  head: () => ({ meta: [{ title: "Process guide — SuperAdvocate.Ai" }] }),
  component: ProcessGuide,
});

const GUIDES = [
  "Bail Application (S.439 CrPC)",
  "Anticipatory Bail (S.438 CrPC)",
  "Cheque dishonour — S.138 NI Act",
  "Divorce by Mutual Consent (S.13B HMA)",
  "Contested Divorce (S.13 HMA)",
  "Consumer Complaint",
  "RERA Complaint",
  "Writ Petition under Article 226",
];

const STEPS = [
  { n: 1, t: "Verify the cheque & dishonour memo", d: "Confirm bank's return memo. Note the date of dishonour — limitation starts from this date.", done: true },
  { n: 2, t: "Issue statutory demand notice within 30 days", d: "Send notice by RPAD demanding payment within 15 days. Retain proof of dispatch and acknowledgment.", done: true },
  { n: 3, t: "Wait 15 days for compliance", d: "If amount is paid, no cause of action arises. If not paid, cause of action arises on the 16th day.", done: false, active: true },
  { n: 4, t: "File complaint within 30 days", d: "File a written complaint before the jurisdictional Magistrate within 30 days from the date cause of action arose." },
  { n: 5, t: "Sworn statement & summons", d: "Lead sworn statement under S.200 CrPC. Magistrate takes cognizance and issues summons to the accused." },
  { n: 6, t: "Evidence & arguments", d: "Examination-in-chief by affidavit. Cross-examination. Lead defence evidence if any." },
  { n: 7, t: "Judgment", d: "If proved, accused liable to fine up to twice the cheque amount or imprisonment up to 2 years, or both." },
];

function ProcessGuide() {
  return (
    <>
      <AppTopbar eyebrow="Practice" title="Step-by-step process guide" />
      <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[280px_1fr]">
        <aside className="border-r border-border bg-sand/50 p-6">
          <div className="eyebrow">Choose a process</div>
          <ul className="mt-3 space-y-1">
            {GUIDES.map((g, i) => (
              <li key={g}>
                <button className={`flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm ${i === 2 ? "bg-foreground text-background" : "text-foreground/85 hover:bg-card"}`}>
                  <span>{g}</span>
                  <ChevronRight className="h-3.5 w-3.5 opacity-60" />
                </button>
              </li>
            ))}
          </ul>
        </aside>

        <section className="p-6 lg:p-10">
          <div className="mx-auto max-w-3xl">
            <div className="eyebrow">Cheque dishonour</div>
            <h2 className="serif-display mt-2 text-4xl">S.138 Negotiable Instruments Act, 1881</h2>
            <p className="mt-4 max-w-2xl text-sm text-muted-foreground">
              The complete procedure from dishonour to judgment, with limitation periods and the
              evidence you need at each stage.
            </p>

            <ol className="mt-12 relative border-l border-border pl-8">
              {STEPS.map((s) => (
                <li key={s.n} className="relative mb-10 last:mb-0">
                  <span className={`absolute -left-[42px] flex h-7 w-7 items-center justify-center rounded-full text-xs font-medium ${
                    s.done ? "bg-foreground text-background" : s.active ? "border-2 border-foreground bg-background text-foreground" : "border border-border bg-background text-muted-foreground"
                  }`}>
                    {s.done ? <Check className="h-3.5 w-3.5" /> : s.n}
                  </span>
                  <div className="flex items-baseline gap-3">
                    <h3 className={`font-serif text-lg ${s.done ? "text-muted-foreground line-through" : ""}`}>{s.t}</h3>
                    {s.active && <span className="rounded-full bg-accent px-2 py-0.5 text-[10px] uppercase tracking-wider text-accent-foreground">In progress</span>}
                  </div>
                  <p className="mt-2 text-sm leading-relaxed text-foreground/80">{s.d}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>
      </div>
    </>
  );
}
