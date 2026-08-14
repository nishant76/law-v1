# CLAUDE.md — SuperAdvocate Platform
# Last Updated: August 2026 (v12 — Cloud migrated from Azure to GCP; OpenAI API directly (not Azure OpenAI); Azure AI Search replaced by pgvector on Cloud SQL; Azure Blob replaced by GCS; eCourtsIndia API replaces government scraping pipeline for public judgment search; v11 — Drafting now GROUNDS jurisdiction on VERIFIED govt data, not the model's memory: built data/jurisdiction/bnss_first_schedule.json (462 offence rows, BNS 49-357, extracted from the OFFICIAL BNSS First Schedule on indiacode.nic.in via scripts/extract_bnss_schedule.py + build_jurisdiction_json.py) + backend/services/jurisdiction_service.py (lookup_section / court_tier_for_punishment / grounding_block); filing_service.generate_template injects jurisdiction_service.grounding_block(brief) so the drafter uses correct BNS section numbers + trial courts; the prompt's old HAND-CURATED offence→court table (which had WRONG numbers — murder said 101 not 103, dacoity 304 [=snatching!] not 310, robbery 302 not 309) was REMOVED, replaced by the verified-data block + corrected First-Schedule-Part-II fallback (bail sections 482/483/528 BNSS confirmed correct); Document Type dropdown REMOVED from app.drafting.tsx → free-text only, prompt returns detected_document_type shown as an EDITABLE type chip (correct it → prepends + regenerates); docs/drafting_correctness_audit.md = full taxonomy audit of every draft type→verified govt source (P&H HC Rules & Orders, NDPS S.O.1055(E), etc.) + 6-step extraction plan; KNOWN GAP — special acts (NDPS §37+quantity, PMLA §45, UAPA §43D(5)), court fees & limitation are NOT in verified data yet and remain model-memory (an NDPS bail draft was caught missing §37/quantity/Special-Court) — extraction Phase 1 will fix; v10 — Drafting now GROUNDS on real precedents: DU Faculty of Law drafting reader split into 43 model drafts (scripts/extract_du_drafts.py → data/draft_examples/du_book/), filing_examples.py routes EVERY dropdown type to a matching precedent (real P&H HC samples for HC types; DU book drafts for all district/family/consumer/NI/property/deed types, which previously got NO example) injected as a FORMAT REFERENCE block; drafting model switched to GPT-5.2 (was gpt-4o); JURISDICTION INFERENCE added to filing_template_prompt (auto-selects Sessions/Magistrate/HC/Family/Consumer forum from the offence when the Court field is blank — hand-curated from BNSS First Schedule + Ss.21-23, NOT yet line-verified against the official Schedule); markdown-bold KNOWN ISSUE fixed (MarkdownText now used in app.drafting.tsx); v9 — Drafting document-type dropdown expanded to 22 verified types across 7 categories + filing_drafter.py forum-conditional format rules (District/Sessions/Family/Consumer/HC headings, was always P&H HC) + expanded verified BNSS section table; v8 — eCourtsIndia REST API validated + one-click import UX built; official gov portals confirmed CAPTCHA-gated; Sonner toast wired app-wide; v7 — active frontend is frontends/law-v2 (TanStack Start + React 19 + shadcn/ui + Tailwind v4); frontends/law is RETIRED — do not edit it; v6 — renamed Nikhar→SuperAdvocate; Draft-a-Filing rebuilt as template/live-fill; Reply-to-Notice perspective; eCourts integration BUILT; PDF extractor section-label + omit-empty; v5 — PDF extractor routing-first prompt + GPT-5.2; v4 — frontend design system)
# Read this file completely before writing any code.

## GIT WORKFLOW — READ FIRST

- NEVER create a new git worktree. Do not use isolation: "worktree" in any agent call.
- Always work directly in the current branch (e.g. pdfExtractor, main).
- The developer manages branching themselves — do not create branches automatically.

---

## WHAT THIS PROJECT IS

SuperAdvocate is an AI-powered legal workspace for solo lawyers and small firms
in Punjab, Haryana, and Chandigarh. Phase 1 builds two things simultaneously:
(1) semantic search over a database of 10,000+ public Indian judgments
(2) semantic search over a lawyer's own uploaded case files.
Both are unified into a single search interface. Lawyers get verified
citations instantly — without uploading anything first.

Target user: Solo practitioner, 4-10 years experience, district courts Punjab/Haryana.
Includes both criminal AND civil litigation lawyers.
Civil litigation lawyers spend up to 1 hour per matter on citation research —
higher ROI than criminal lawyers for search feature.

---

## LAUNCH QUALITY MANDATE — READ BEFORE SHIPPING ANY FEATURE

This product launches at India scale into a market with established competitors
(Indian Kanoon's Prism, etc.). Lawyers will test it directly. A single broken
link, fabricated citation, or wrong extraction destroys trust instantly — a
lawyer who catches one error stops trusting the whole tool.

Therefore, before any feature is put in front of lawyers:
- Every user-facing output must be CONCRETE and VERIFIED, never placeholder.
- Every external link must be validated to resolve — never display an unverified
  or "landing page" URL in place of the real resource.
- Never show fabricated, guessed, or unverifiable data. When unsure, show nothing
  or an explicit "not available", never a plausible-looking fake.
- Precision over breadth: a small set of features/data that work perfectly beats
  a large set that is 90% right. 90% right = a lawyer finds the 10% and leaves.
- If a feature cannot meet this bar yet, gate it (hide it) rather than ship it
  half-working.

---

## CURRENT PHASE

Phase 1 only. Do not build anything outside this list.
Do not suggest Phase 2 features. Do not over-engineer.

---

## FOLDER STRUCTURE

superadvocate/
├── backend/
│   ├── api/              # FastAPI routers — endpoints only, no business logic
│   ├── services/         # All business logic lives here
│   ├── models/           # SQLAlchemy ORM models
│   ├── schemas/          # Pydantic request/response schemas
│   ├── core/             # config.py, security.py, logger.py
│   ├── middleware/        # JWT validation, request logging, rate limiting
│   ├── workers/          # Celery tasks — thin wrappers only, logic in services/
│   └── migrations/       # Alembic migrations
├── frontends/
│   ├── law-v2/           # ACTIVE frontend — TanStack Start + React 19 + Tailwind v4
│   │                     # Routes: frontends/law-v2/src/routes/
│   │                     # API calls: frontends/law-v2/src/api/
│   │                     # Types: frontends/law-v2/src/types/
│   │                     # Run: bun run dev (or npm run dev) from frontends/law-v2/
│   └── law/              # RETIRED — do not edit. Kept for reference only.
├── scripts/
│   ├── scrapers/         # eSCR, P&H HC, district court scrapers (NO Indian Kanoon)
│   └── sync_claude_md.py # Syncs ADR changes to this file
├── docker-compose.yml
├── Dockerfile
└── CLAUDE.md             # This file

---

## TECH STACK

### Backend
- Language:    Python 3.11
- Framework:   FastAPI (async only — never use sync)
- ORM:         SQLAlchemy 2.0 async
- Migrations:  Alembic
- Validation:  Pydantic v2
- Jobs:        Celery + Redis
- Server:      Uvicorn

### Frontend (frontends/law-v2 — ACTIVE)
- Framework:   React 19 + TanStack Start (SSR-capable Vite meta-framework)
- Routing:     TanStack Router v1 (file-based, routes in src/routes/)
- Styling:     Tailwind CSS v4 + shadcn/ui components (Radix UI primitives)
- Icons:       lucide-react
- Server state: TanStack Query v5
- UI state:    Zustand v5
- Forms:       react-hook-form + zod
- HTTP client: axios (src/api/client.ts)
- Package mgr: bun (bun.lock present) — use bun commands, not npm
- Build:       Vite 8 via @lovable.dev/vite-tanstack-config
- Target:      1366x768 optimised
- Fonts:       Serif headings (font-serif class), system sans body

### AI / LLM
- Drafting:    GPT-4o (OpenAI API) — expensive, use only for filing drafts
- RAG/Extract: GPT-4o-mini (OpenAI API) — use freely for everything else
- Embeddings:  text-embedding-ada-002 — 1536 dimensions
- OCR:         Google Document AI

### Infrastructure (GCP — asia-south1 / Mumbai region)
- Database:    Cloud SQL (PostgreSQL 15) + pgvector extension — vector + keyword hybrid search
- Storage:     Google Cloud Storage (GCS) — document uploads + exports
- Compute:     Cloud Run — containerised FastAPI (replaces Azure App Service)
- Cache/Queue: Cloud Memorystore (Redis) — Celery broker + result backend
- Secrets:     Google Secret Manager — never hardcode secrets anywhere
- Email:       SendGrid (free tier — 100/day)
- WhatsApp:    WhatsApp Business API (Meta official) — client reminders
- Monitoring:  Google Cloud Logging + Cloud Monitoring
- CI/CD:       GitHub Actions → Cloud Run (via gcloud CLI)

---

## FRONTEND DESIGN SYSTEM

### Design Language
The SuperAdvocate UI follows a "legal document + modern tool" aesthetic:
- Warm off-white background (`#F8F7F4`) — not clinical white
- Dark sidebar with gold accents — high contrast, professional
- Card-less content sections — hairline dividers only, no white card boxes
- Flow-guided navigation labels (action-oriented, not feature-named)

### Tailwind Custom Tokens (tailwind.config.ts)
```
Colors:
  bg / paper:       #F8F7F4     (warm off-white page background)
  sidebar:          #111827     (dark sidebar background)
  sidebar-hover:    #1f2937
  ink:              #1C1A16     (primary text / CTA buttons)
  gold.DEFAULT:     #C9A84C     (active nav, save buttons, logo mark)
  gold.bg:          #FDF6E3
  gold.muted:       rgba(201,168,76,0.15)  (active nav highlight)
  text.1:           #1C1A16     (primary text)
  text.2:           #6A6760     (secondary text)
  text.3:           #A09C95     (muted / labels)
  border.1:         #E5E3DD     (default dividers)
  border.2:         #C8C4BC     (input borders)
  surface.2:        #F1F0EC
  surface.3:        #E8E6E0
  green.DEFAULT:    #15803D  /  green.bg: #F0FDF4
  amber.DEFAULT:    #B45309  /  amber.bg: #FFFBEB
  blue.DEFAULT:     #1D4ED8  /  blue.bg:  #EFF6FF

Animations:
  pulseDot:         2s ease-in-out infinite — opacity + scale pulse
                    Used on active/stayed status dots in case badges
  fadeUp:           0.18s ease — subtle enter animation
  progBar:          3.5s ease-out — AI usage bar fill

Border radius:
  DEFAULT: 10px  |  sm: 7px  |  icon: 6px  |  full: 9999px
```

### Sidebar Layout
- `bg-sidebar` (#111827) dark background, 210px fixed width
- Logo mark: gold rounded square with document SVG icon
- Nav groups: WORKSPACE / DO / TRACK (uppercase 9px labels)
  - WORKSPACE: Overview, My Cases
  - DO: Draft a Filing, Find Judgments, Read a Document, Summarise Case, Reply to Notice
  - TRACK: Hearings & Dates
- Active state: `bg-gold-muted text-gold font-semibold` + absolute 3px gold left border
- Inactive: `text-white/50` hover `text-white/80`
- Footer: AI usage bar (gold fill) + user card with gold avatar ring + sign-out

### Navigation Labels (flow-guided, not feature-named)
```
Route         Label
/             Overview
/cases        My Cases
/draft        Draft a Filing
/search       Find Judgments
/pdf          Read a Document
/synopsis     Summarise Case
/reply        Reply to Notice
/deadlines    Hearings & Dates
/legal-process Legal Process Guide
```

### CaseDetail Page Pattern (dark hero + card-less sections)

**Hero strip** (`bg-sidebar rounded-[10px]`):
- Back button (ghost `text-white/40`) + Edit/Save button (top-right)
  - Edit: `bg-white/10 text-white/70` ghost
  - Save: `bg-gold text-sidebar` gold filled
- Case title: `font-serif text-[21px] text-white`
- Status badge + court · matter type · case number in `white/50`
- 4-column stats grid on dark background with `1px` gap dividers
  (Client, Next Hearing, Total Fees, Balance Due)
  - Urgent/overdue values: `text-red-400`
  - Positive (paid/no balance): `text-green-400`
  - Normal: `text-white`

**Section primitive** (card-less — NO white card borders):
```tsx
// CORRECT — hairline divider only
<div className="border-t border-border-1 pt-[16px] pb-[20px]">
  <div className="text-[10px] font-bold tracking-[1px] uppercase text-text-3 mb-[12px]">
    {title}
  </div>
  {children}
</div>

// WRONG — do not use card styling for sections
<div className="bg-white border border-border-1 rounded-DEFAULT ...">
```

**Party role chips** (coloured by role):
```
client:      bg-blue-bg text-blue border-blue/25
opponent:    bg-red-50 text-red-600 border-red-200
opp_counsel: bg-surface-3 text-text-2 border-border-1
judge:       bg-purple-50 text-purple-700 border-purple-200
witness:     bg-amber-bg text-amber border-amber/25
other:       bg-surface-2 text-text-3 border-border-1
```
Each chip: `inline-flex items-center gap-[7px] border rounded-[6px] px-[10px] py-[6px]`
Role label: `text-[9.5px] font-bold uppercase tracking-[0.5px] opacity-70`
Name: `text-[12.5px] font-semibold`

**Fees strip** (compact inline — not large stat boxes):
```tsx
<div className="inline-flex items-center divide-x divide-border-1 border border-border-1 rounded-sm">
  <div className="px-[12px] py-[6px]">Agreed / Paid / Due</div>
</div>
```

### Cases List Page (CaseCard pattern)
- Single `bg-white border border-border-1 rounded-DEFAULT overflow-hidden` container
- Each case is a row: status dot | title + matter chip | court · case# · client | hearing chip + fee tag | ›
- Status dots with coloured glow shadows:
  ```
  active:   bg-green shadow-[0_0_0_3px_rgba(22,163,74,0.18)]
  stayed:   bg-amber shadow-[0_0_0_3px_rgba(180,83,9,0.18)]
  settled:  bg-blue  shadow-[0_0_0_3px_rgba(29,78,216,0.18)]
  disposed: bg-text-3 (no shadow)
  ```

---

## TANSTACK QUERY v5 — CRITICAL PATTERN

TanStack Query v5 attaches an internal AbortController to every `useMutation`.
In React 18 Strict Mode (double-render in dev), this AbortController fires
immediately, cancelling in-flight requests before they complete.

**NEVER use `useMutation` for search or any user-triggered API call
that must not be cancelled.**

Use plain `async/await` + `useState` instead:

```typescript
// CORRECT — plain async/await, no TQ5 mutation
const [isPending, setIsPending] = useState(false)
const [errorMsg, setErrorMsg] = useState<string | null>(null)
const searchIdRef = useRef(0)   // stale-response guard

const handleSearch = async () => {
  const q = query.trim()
  if (!q || isPending) return
  const thisId = ++searchIdRef.current
  setIsPending(true)
  setErrorMsg(null)
  try {
    const resp = await unifiedSearch(q)
    if (thisId !== searchIdRef.current) return   // ignore stale
    // ...set results
  } catch (err: unknown) {
    if (thisId !== searchIdRef.current) return
    setErrorMsg(err instanceof Error ? err.message : 'Search failed.')
  } finally {
    if (thisId === searchIdRef.current) setIsPending(false)
  }
}

// WRONG — useMutation gets cancelled in React 18 Strict Mode dev
const { mutate, isPending } = useMutation({ mutationFn: unifiedSearch })
```

Use `useMutation` only for fire-and-forget mutations where cancellation
is acceptable (e.g. deleting a record, toggling a flag).

---

## SEARCH SERVICE — TIMEOUT ARCHITECTURE

The unified search has layered timeouts to prevent hangs:

```
Layer 1 — Embedding (search_service.py):
  asyncio.wait_for(embed_query(query), timeout=8.0)
  On timeout/failure: falls back to [] (empty vector)
  → search degrades to keyword-only, never hangs

Layer 2 — Full search endpoint (api/search.py):
  asyncio.wait_for(unified_search(...), timeout=25.0)
  On asyncio.TimeoutError: returns HTTP 504 with clear message

Layer 3 — Frontend (axios):
  Browser timeout: 120 seconds (per GAP-043)
  Error shown as red banner to user
```

Pattern in search_service.py:
```python
embed_result, expand_result = await asyncio.gather(
    asyncio.wait_for(self.embed_query(query), timeout=8.0),
    expand_query(query, use_llm=True),
    return_exceptions=True,
)
query_vector = embed_result if isinstance(embed_result, list) else []
expanded_queries = expand_result if isinstance(expand_result, list) else [query]
```

Never call `embed_query` or any OpenAI API call without a timeout.
Never let a single external service call block the entire request indefinitely.

---

## PHASE 1 FEATURES — BUILD THESE ONLY

### 1. Document Library
- Upload PDF, DOCX, images (max 50MB per file)
- Store originals in Google Cloud Storage (GCS)
- Background indexing via Celery: OCR → chunk → embed → index
- Status tracking: pending / processing / indexed / failed
- Retry button on failed documents with plain English error reason
- Google Drive connect option (read files, do not store originals)
- Soft delete only — never hard delete documents

### 2. Public Judgment Search
- DATA SOURCE: eCourtsIndia REST API (`webapi.ecourtsindia.com`) — replaces all
  government portal scraping. Covers ALL Indian courts (SC, HC, District, Tribunals).
  Nightly Celery job: GET /search (P&H HC + Punjab/Haryana district filter) →
  GET /case/{cnr} (grab markdownContent — full order text, 5-40 pages) →
  chunk → embed (ada-002) → upsert into pgvector on Cloud SQL.
- Do NOT use Indian Kanoon — they are now a direct competitor (launched Prism AI)
- Hybrid search: pgvector cosine similarity + pg_trgm keyword (both on Cloud SQL,
  no separate search service needed)
- Works from day one — no upload needed by lawyer
- Every result shows: case name, court, year, CNR, parties

LINK INTEGRITY — NON-NEGOTIABLE (see LAUNCH QUALITY MANDATE):
Every citation's "View Judgment" link MUST resolve to the actual judgment PDF.
- Each citation stores: cnr (Case Number Record), order_filename, link_status
  ('pending'|'verified'|'dead').
- "View Judgment" button calls GET /api/partner/case/{cnr}/order/{filename} via
  eCourtsIndia API → returns a signed pre-fetched URL to a certified true copy PDF
  (digitally signed, watermarked, served from eCourtsIndia's infrastructure —
  sourced directly from govt eCourts servers). This link can never go dead as long
  as the case exists in eCourts.
- NEVER display a generic or fabricated URL. NEVER show a citation without a
  resolvable PDF link.
- Nightly re-check job calls bulk-refresh-status for active cases to ensure
  data freshness.

### 3. Own Files Search (RAG)
- Semantic search over lawyer's indexed documents
- GPT-4o-mini synthesises answer from retrieved chunks
- Every answer shows: source document + page + paragraph
- Confidence score on every answer (0-10)
- Low confidence (<4): show warning "upload more relevant documents"

### 4. Unified Search Interface
- Single search box queries BOTH sources simultaneously
- Results clearly separated:
  "From your files: [results]" vs "From public judgments: [results]"
- One query — two sources — one interface
- Outcome filter on results:
  [ ] All results
  [ ] Decided in favour of petitioner
  [ ] Decided in favour of respondent
  [ ] Bail granted / refused
- Lawyers search by concept not just keywords
  e.g. "section 138 partner liability favour" must work correctly

### 5. PDF Extractor
- Upload any court order, judgment, contract, legal notice
- Extract structured fields: case number, parties, dates, amounts, next hearing
- Confidence score per field — amber flag if below 75%
- Q&A over document: "What conditions did the court impose?"
- Model: GPT-5.2 for the streaming readable briefing (READABLE_MODEL in
  prompts/pdf_extractor.py) — same model as the structured extraction pass, for
  consistent document classification + legal reasoning across both phases.
- The briefing prompt is ROUTING-FIRST (DOCUMENT ROUTING RULE at the top of
  READABLE_SYSTEM_PROMPT): it classifies the document first (Court Judgment/Order,
  Legal Notice, Contract, Government Notification, Business/Financial Document,
  Product Launch, etc.). ONLY court judgments/orders get the full judgment
  template (SNAPSHOT + Winning Argument + Court's Reasoning + Authorities +
  Operative Directions). Every other type gets a generic Executive Summary
  (Purpose / Key Highlights / Important Dates / Risks / Action Items / Key
  Takeaways) with NO fabricated legal sections. SNAPSHOT now carries a leading
  document_type field; for non-judgments all court-case fields are null and the
  frontend hides empty fields (never renders "Not applicable").
- Verified 2026-06-15 on a 24-doc corpus (6 judgments, legal notice, SRS,
  product-launch, handbooks, annual reports, brochures): routing was 100% correct
  (no legal sections leaked into non-legal docs) and judgment briefings captured
  full detail — court inference, full judge bench, all authorities/dates — with
  no hallucination.
- CAVEAT — GPT-5.2 is on a restricted, limited-quota tier: the verification run
  hit HTTP 429 insufficient_quota after ~18 docs while GPT-5.4-mini had headroom.
  Before relying on 5.2 at India scale, confirm the OpenAI GPT-5.2 deployment has
  adequate TPM/quota, OR fall back to GPT-5.4-mini (set READABLE_MODEL). On the
  earlier 2-judgment benchmark 5.4-mini was ~$0.02/call (3x cheaper than 5.2, ~6x
  cheaper than 5.5) and ~10s vs ~28s (5.2)/~50s (5.5) with equal snapshot accuracy
  after prompt tuning; 5.2/5.5 extract richer evidentiary detail on complex cases.
- document_type labels for non-legal docs are approximate (no SRS/Brochure types
  in the routing list yet — brochures classify as "Product Launch", SRS as
  "Research Report"); routing is unaffected. Add categories if label accuracy
  matters for the UI chip.
- Judgment-brief section refinements: the "Court's Reasoning" bullets use the labels
  Contention / Evidence / Decision (was Finding/Evidence/Impact); "Authorities Relied
  Upon" is renamed "Judgements Relied Upon" (rendered as a collapsible list in
  MarkdownText, with a guard so an item with no sub-detail never opens to an empty panel).
- OMIT-EMPTY rule: any section/field with no data is omitted entirely — no "Not specified"
  placeholders. Enforced in the prompt AND by a frontend safety-net (MarkdownText strips
  any "## " section whose body is blank/placeholder), and the SNAPSHOT card hides empty fields.
- GPT-5.x models reject temperature/top_p — use max_completion_tokens via
  extra_body (handled in LLMService).

### 6. Case Synopsis Generator
- Upload any judgment or petition
- Output structured one-pager:
  parties / facts / issues / held / citations used
- Export as .docx

### 7. Smart Reply Generator
- Upload legal notice PDF/DOCX → extract EVERY allegation (notices run 15-25 paras; the
  input is read up to ~30000 chars so the latter-paragraph legal arguments AND the
  prayer/demands are not dropped — a 12000 cap previously lost the back half).
- PERSPECTIVE (critical): the reply is drafted for the RECIPIENT / Noticee. Allegations
  are restated from the recipient's viewpoint — the sender's client is referred to by
  name (or "the Sender" / he / she), and "my client" ALWAYS means the recipient. Never
  carry over the notice's own "My Client" (there it means the sender's side). The
  extraction starts each point with "The Sender alleges that …".
- Per allegation the lawyer sets Admit / Deny / Partial and types their own facts in a
  "Your facts / grounds" box; a "Rewrite in legal language" action (grounds_rewrite_prompt,
  gpt-4o-mini) polishes those notes into formal legal prose WITHOUT adding facts or citations.
- Generate a complete formal reply letter → review / copy / export .docx.
  DENY drafting rule (generalised, NOT notice-specific): always state the positive contrary
  averment ("My client avers that…"); never a double negative ("denies that there was no X");
  use singular "it/its" for a corporate client; never assert a step was already taken unless
  the grounds say so.
- Find-&-add citations was REMOVED from this feature — it moves to the Case Argument
  Generator (Feature 11). Any citations that do appear must remain verified-only.

### 8. Strategic Filing Drafter (template + live-fill)
- Input: a free-text "describe your draft" box (rough/plain language is fine) OR upload an
  existing draft (PDF/DOCX) to improve, plus a Court field. The old filing-type and
  objective (Win/Delay/Challenge/Settle/Preserve) selectors have been REMOVED — the model
  infers the filing type and strategy from the description itself.
- Generation fully rewrites the input into a properly-formatted Punjab/Haryana filing and
  returns a TEMPLATE: the legal body is written out, with {{snake_case}} placeholder tokens
  for every case-specific detail (parties, court, case/FIR no., dates, amounts). Any detail
  the lawyer already stated is captured into the matching field's pre-filled value (never
  inlined — the token stays editable).
  Prompt: filing_template_prompt in prompts/filing_drafter.py. MODEL = ModelType.GPT5_2 (same
  model as the PDF Extractor's READABLE_MODEL — switched from gpt-4o-mini/gpt-4o because 5.2
  follows the multi-part structural/depth/jurisdiction requirements far more reliably). GPT-5.2
  is slower (~30-70s), so filing_service.generate_template passes call_completion(timeout=110)
  under the asyncio.wait_for(timeout=120) outer guard (the 30s default was tuned for 4o-mini and
  timed out). GPT-5.2 quota caveat applies (see Feature 5) — fall back to GPT54_MINI if needed.
  Endpoints: POST /filing/template (describe), /filing/template/upload (improve a file),
  /filing/template/export (.docx).
- BOOK/PRECEDENT GROUNDING (built 2026-07-15) — backend/services/filing_examples.py injects a
  FORMAT REFERENCE excerpt of a REAL precedent into the prompt so the model matches its
  structure/heading sequence. get_format_example(user_input) keyword-matches the Document Type
  label the UI prepends to the brief (_ROUTES table, order-sensitive: reply-138 before
  138-complaint, anticipatory before regular bail, mutual-consent before divorce). Two sources:
    · Real P&H HIGH COURT filings (data/draft_examples/*.txt) — primary for HC types (writ/CWP,
      regular+anticipatory bail, quashing, habeas). Actual filed docs, better than any textbook.
    · DU Faculty of Law LL.B. reader "Drafting, Pleadings and Conveyance" (LB-502, July 2020,
      public at lawfaculty.du.ac.in) — split into 43 individual model drafts under
      data/draft_examples/du_book/*.txt by scripts/extract_du_drafts.py (re-runnable; case-
      sensitive UPPERCASE-heading split + "* * * * *" end-of-draft trim + PART-B boundary).
      Fills EVERY district/family/consumer/NI-Act/property/deed type — these had NO example before.
  IMPORTANT — the DU reader is NOT the S R Myneni book (no legit PDF of Myneni exists; physical
  only). It is pre-BNS/BNSS and Delhi-oriented, so it grounds STRUCTURE ONLY — the correct forum
  heading + current BNSS section numbers come from the prompt's rules, NOT the example (the
  injected reference label says exactly this). When a licensed Myneni digital ed. is purchased it
  drops in as another du_book-style source with no rearchitecting.
- JURISDICTION INFERENCE (built 2026-07-15; REWIRED to VERIFIED data 2026-07-16) — section in
  filing_template_prompt. When the Court field is blank the model infers the correct forum from the
  offence/matter and uses that heading (never leaves it blank or "(to be specified)"; filing_service
  passes court as "NOT SPECIFIED — infer from matter") + bail hierarchy (regular bail: Sessions
  first→HC if refused; anticipatory: Sessions first→HC; "rejected by Sessions"/"second bail" → HIGH
  COURT) + civil/family/consumer/writ routing + district inferred from any city named. On inferring,
  the model adds "Court inferred as … — verify before filing" to strategy_notes; app.drafting.tsx
  shows it in an amber "Court auto-selected" banner ABOVE the draft.
  RESOLVED (was the launch-quality CAVEAT) — the offence→court numbers are NO LONGER hand-curated
  from memory. filing_service.generate_template now calls jurisdiction_service.grounding_block(brief)
  (backend/services/jurisdiction_service.py), which scans the brief for BNS section refs + offence
  nouns, looks them up in the VERIFIED data/jurisdiction/bnss_first_schedule.json (462 offence rows
  extracted from the official BNSS First Schedule, indiacode.nic.in aid AC_CEN_5_23_00049_202346 —
  see data/jurisdiction/README.md + manifest), and injects a "VERIFIED JURISDICTION DATA" block the
  model MUST use verbatim (overrides any recalled number). The prompt's old ~25-offence hand-curated
  table (WRONG numbers: murder 101 not 103, dacoity 304 [=snatching] not 310, robbery 302 not 309)
  was REMOVED; only the general punishment→court fallback (First Schedule Part II: death/life/>7yr →
  Court of Session; 3-7yr → Magistrate of the First Class; <3yr/fine → Any Magistrate) + bail/civil/
  family/consumer routing remain in-prompt. Bail section numbers (anticipatory 482 BNSS, regular 483,
  quashing 528) confirmed correct against the statute.
- SPECIAL-ACT BARS (built 2026-08-14 — was the REMAINING GAP; audit extraction plan step 1 DONE).
  jurisdiction_service covers only BNS First Schedule offences, so the bars that make a filing
  NOT MAINTAINABLE were still model-memory — an NDPS bail draft was caught missing §37, the
  quantity, and the Special Court. Now: data/special_acts/special_acts.json holds 12 VERBATIM
  provisions sliced out of the official India Code bare-act PDFs by scripts/extract_special_acts.py
  (re-runnable; literal start/end markers; amendment footnotes stripped; a marker miss writes
  verified:false + EMPTY text, and the service skips unverified rows so failure degrades to silence,
  never a guess): NDPS §37/§36A/§2(viia)/§2(xxiiia), PMLA §45, UAPA §43D, NI §138/§142, CCA §12A,
  CPC §80, Partnership §69, HMA §14.
  backend/services/special_acts_service.py — detect_triggers(brief) keyword-matches subject-matter
  AND (where a bar only bites for a particular relief) the relief; grounding_block(brief) emits the
  verbatim statute + a "THE DRAFT MUST" pleading checklist + "MUST ALSO FLAG" items. Returns "" when
  no bar applies, so ordinary filings are not padded. filing_service.generate_template appends it
  next to the jurisdiction grounding (same degrade-gracefully rule — never block a draft).
  filing_template_prompt gained a MANDATORY STATUTORY BARS section telling the model the block
  OVERRIDES recalled numbers, and that it must never state a figure the quoted text lacks.
  DELIBERATE NON-BUILD — the NDPS small/commercial QUANTITY table (S.O.1055(E)) is NOT stored. Its
  only published copy (cbn.gov.in/pdf/qtynotif.pdf) is a poor scan; OCR drops values (heroin's
  small-quantity column vanishes entirely). Guessing a threshold would be the single
  highest-consequence error in NDPS drafting, so instead the drafter is REQUIRED to obtain the
  quantity from the lawyer, state no threshold, put it in missing_facts, and add a strategy_notes
  line that the classification must be verified against S.O.1055(E). Replace when a text-layer
  gazette copy is found. See data/special_acts/README.md.
  STILL model-memory (audit steps 2-6): CrPC→BNSS procedural map, special-court/tribunal forum map,
  COURT FEES & LIMITATION, P&H HC Rules & Orders format authority, deed stamp/registration. See
  docs/drafting_correctness_audit.md; the Legal Process Guide (Feature 10) will read the same data.
  The DU book is NOT a jurisdiction authority (format-by-example only).
- missing_facts is now returned by /filing/template and rendered as an amber "Verify before filing"
  list ABOVE the draft in app.drafting.tsx — an unverifiable statutory input must be visible, never
  swallowed.
- key_fields CONSOLIDATION rule applied to filing_template_prompt (was a known TODO): one field per
  real-world thing the lawyer types; labels must not repeat their own noun or a noun already fixed
  in the template — kills "District District" / "State of State" / duplicate FIR-number fields.
- Live editor (two-pane): left = the draft with highlighted blanks; right = a Key Details
  panel (one input per blank — typing fills the draft live, client-side) + Find & Add
  Citations (reuses unified search, verified-only; selected citations are appended and exported).
- AUTHORITIES PANE (built 2026-08-14 — the "Find & Add Citations" line above described
  behaviour that was NOT in app.drafting.tsx; the page only listed citations_used).
  components/app/DraftCitationsPanel.tsx sits in the right aside under Key Details:
    · SUGGESTED — on draft generation it auto-runs unifiedSearch seeded from the lawyer's own
      brief + detected_document_type (lib/draftCitations.buildSuggestionQuery, capped 400 chars),
      showing up to 5 one-click "Add to draft" cards. Suggestions are an ASSIST: a failure leaves
      the manual search fully usable and never blocks the draft.
    · SEARCH BOX — a BUTTON, not a live input (a 25s judgment search must not fire on keystrokes).
      Clicking opens components/app/CitationSearchModal.tsx: full search over public judgments,
      Enter-to-search, add/remove per result, Esc/backdrop to close.
  LINK INTEGRITY GATE (lib/draftCitations.isAttachable) — a judgment may only be attached when it
  has a resolvable judgment_url and link_status != 'dead'. In the modal, unattachable results are
  still LISTED but the Add button is disabled with "No certified copy available", so the lawyer
  sees the case exists and why it cannot be cited; in the suggestions list they are filtered out.
  Attached judgments render as a "## LIST OF JUDGMENTS RELIED UPON" section appended to the draft
  (authoritiesMarkdown), and composeDraft(mode) builds preview and export from ONE code path so
  the .docx can never drift from what is on screen. Citation state lives outside `result`, so
  regenerating (e.g. correcting the filing-type chip) does not silently drop attached authorities.
  Both search calls use plain async/await + a stale-response guard, never useMutation (GAP-050).
- NOTE: the older objective-based generator (/filing/generate) + draft-quality scoring
  (citation safety 35% / completeness 25% / legal accuracy 20% / brief coverage 15% /
  language 5%; block if citation safety < 50) still exists in code for back-compat, but is
  no longer the UI flow.
- Document Type dropdown REMOVED 2026-07-16 (was DOCUMENT_TYPE_GROUPS in app.drafting.tsx). The
  drafting input is now FREE-TEXT ONLY (brief + optional Court) — the model classifies the filing
  type itself and returns it as `detected_document_type`, which app.drafting.tsx renders as an
  EDITABLE amber chip in the result header. Correcting the chip prepends the corrected type to the
  brief and regenerates (steering both the type hint and the filing_examples precedent routing).
  This removed the stale-default footgun (the old default "Plaint — Civil Suit" would silently
  misroute an untouched dropdown, e.g. a bail brief). filing_examples._ROUTES already keyword-matches
  natural-language briefs (anticipatory bail / cheque bounce / divorce / gift deed…), so precedent
  routing survives without the dropdown label. (Rationale + DraftBotPro free-text comparison in the
  session notes.) KNOWN small TODO: the Key Details key_fields can be over-granular ("District
  District", "State of State") — a prompt consolidation rule (filing_drafter.py ~line 294) is drafted
  but not yet applied.
- COURT-SPECIFIC FORMAT RULES in filing_template_prompt (prompts/filing_drafter.py) — fixed
  2026-07-14: the prompt previously applied the P&H HIGH COURT heading/format unconditionally
  to every filing type, so a Bail Application or Written Statement would wrongly get "IN THE
  HIGH COURT OF PUNJAB AND HARYANA AT CHANDIGARH" instead of a district/sessions/family-court
  heading. Now branches on 5 fora — P&H High Court, District/Civil Court, Sessions/Magistrate
  Court, Family Court, Consumer Disputes Redressal Commission — each with its own heading
  convention, inferred from the filing type + Court field. Verified in-browser across all 5
  (Bail Application → "IN THE COURT OF THE SESSIONS JUDGE, PANCHKULA"; Writ Petition →
  P&H HC extraordinary-civil-jurisdiction format retained; Maintenance Application → "IN THE
  COURT OF THE PRINCIPAL JUDGE, FAMILY COURT, PANCHKULA"; Consumer Complaint → "BEFORE THE
  DISTRICT CONSUMER DISPUTES REDRESSAL COMMISSION, PANCHKULA").
  Also expanded the BNSS section-mapping table (cross-verified against 2+ independent sources
  per entry, not just recalled) — was 3 entries (438/439/482 CrPC), now 10: adds 200→223 CrPC to
  BNSS (complaint), 227→250 (discharge, sessions), 239→262 (discharge, warrant case), 397→438
  (revision), 167(2)→187(3) (default/statutory bail), 125→144 (maintenance), 451→497 (custody of
  property). BNSS governs offences on/after 01-Jul-2024 only; CrPC still applies to older
  offences under the savings clause — the prompt now tells the model to flag the offence date as
  a missing fact rather than silently assuming either regime.
- RESOLVED 2026-07-14 (was a KNOWN ISSUE): app.drafting.tsx now renders `template_markdown`
  through the shared `MarkdownText` component (imported from @/components/ui/MarkdownText —
  reused from the PDF Extractor, Feature 5), so `**bold**`, GFM tables (Index/List of Dates),
  and bullet lists render properly instead of showing literal asterisks/pipes.
- LIVE-FILL SIDE PANE: after generation the Key Details inputs render in a sticky right-hand
  aside (w-[260px]); typing a value substitutes the matching {{token}} live in the draft via
  fillTemplate() — preview mode wraps filled/blank tokens as ⟦highlighted chips⟧ (MarkdownText's
  chip syntax), export mode strips them to plain text so the .docx has no {{token}}/⟦⟧ markup.

### 9. Deadline Tracker + Court Diary
- Add matter with key dates: hearing, filing deadline, limitation period
- Reminders at 30 days, 7 days, 1 day before each deadline
- Reminder channels: in-app notification + email (SendGrid)
- If deadline missed: auto-suggest "Draft condonation of delay application?"
- One click → draft generated immediately

DELIVERY BUILT 2026-08-14 (it previously did not work at all — three bugs made the whole
feature dead, all fixed):
  · DeadlineReminder(client_phone=…) — that column does not exist on the model or in
    migration 001, so EVERY deadline creation raised TypeError. Client phone now comes from
    law.matters.client_phone at send time (one number per matter, no drift).
  · api/deadlines.py used current_user["firm_id"], but CurrentUser is an object with no
    __getitem__ → every deadline endpoint 500'd. Now attribute access, as everywhere else.
  · the deadlines router had NO /api/v1 prefix while the frontend calls /api/v1/deadlines →
    404 regardless. Fixed; the same bug on legal_process was fixed too.
  · Celery beat contained ONLY scraper-update, so process_deadline_reminders and the eCourts
    sync never ran. And _send_reminder_notifications was three `# TODO` + logger.info stubs —
    nothing was ever sent.

- backend/services/notification_service.py — REAL delivery. SendGrid + Meta WhatsApp Cloud API
  over httpx: bounded timeout (15s), retry on transient status only (408/429/5xx — a rejected
  number is not retried), recipients MASKED in logs and message bodies never logged (GAP-032),
  and an unconfigured provider returns NOT_CONFIGURED instead of raising, so one missing key
  cannot break the daily run for every firm. Also holds record_in_app() (no commit — the caller
  owns the transaction, so a reminder and its notification commit together).
- Cadence is really 30/7/1: create_deadline writes one DeadlineReminder row per offset still in
  the future, and if the deadline is nearer than the smallest offset it creates ONE immediate
  reminder rather than none. The offset is derived from (key_date − reminder_date), not from
  "days from now", so a reminder sent late still says the right thing. get_upcoming_deadlines
  collapses the 30/7/1 rows to one row per (matter, key date, type) — three deliveries of one
  deadline must not appear three times in the UI.
- law.notifications (migration 009) + /api/v1/notifications — the in-app channel, the one that
  always works. user_id NULL = firm-wide. NotificationBell.tsx replaces the topbar's hardcoded
  always-on dot; it polls 60s and the badge only appears when something is unread.

COURT DIARY (built 2026-08-14) — law.matters.next_hearing_date answers only "when next".
A diary must also answer "what is listed today, in board order", "what happened on the 14th",
and "how many adjournments has this had". So:
- law.hearing_entries (migration 009) — one row per court date per matter: board_number (the
  cause-list serial), purpose/stage, outcome, adjournment_reason, next_date, action_required,
  appeared_by, from_ecourts, status (scheduled/held/adjourned/not_taken_up/disposed). Partial
  unique index on (matter_id, hearing_date) WHERE deleted_at IS NULL so a repeated sync cannot
  stack duplicates.
- backend/services/diary_service.py — ensure_scheduled_entries() materialises entries from every
  matter's next_hearing_date (idempotent; runs on the diary read path AND as a cron), so matters
  imported before the diary existed still produce a correct cause list. record_outcome() is the
  central action: it closes the entry, creates the next scheduled entry, rolls
  matters.next_hearing_date forward, and ARMS A FRESH 30/7/1 REMINDER SET — the diary maintains
  itself from one form submission.
- TIMEZONE: storage stays UTC, but a "day" means an IST calendar day converted to a UTC window
  (local_day_bounds). Without this a 10:30 IST hearing falls on the previous UTC day and the
  cause list is silently wrong. LOCAL_TIMEZONE env var, default Asia/Kolkata.
- API: GET /api/v1/diary?day=&days= (day view, or a range — days=7 for the week),
  GET /diary/matters/{id} (full history), POST /diary, PATCH /diary/{entry_id}.
- UI: app.hearings.tsx rebuilt as a date-navigable diary (prev/next/date-picker/Today, cause
  list in board order, filing & limitation dates and missed items in a side column) +
  RecordOutcomeDialog.tsx.

CELERY BEAT — ordered through the day so reminders never run on stale data:
  00:30 UTC (06:00 IST) ecourts.sync_hearings → 01:00 diary.materialise_entries →
  02:00 citations.scraper_update → 03:30 (09:00 IST) deadlines.process_reminders →
  12:30 (18:00 IST) diary.send_daily_cause_list.

- CLIENT WhatsApp reminders (via WhatsApp Business API):
  Lawyer adds client phone number to matter
  System sends WhatsApp messages directly to client:
  → 7 days before hearing:
    "Aapka matter [Case Name] ki agli sunwai [Date] ko hai.
     Koi documents chahiye toh [Lawyer Name] se contact karein."
  → 1 day before hearing:
    "Kal [Date] ko aapki hearing hai. Court: [Court], Time: 10:30 AM"
  → Important deadline:
    "Aapke matter mein ek important deadline [Date] ko hai.
     Please apne lawyer se contact karein."
  Cost: approximately ₹0.50-1 per message via Meta API
  Lawyer controls on/off per matter
  This is a major differentiator — no competitor does this

- eCOURTS HEARING SYNC (built — see ECOURTS INTEGRATION below):
  Lawyer sets their eCourts advocate name → "Sync" pulls their pending cases
  (and next-hearing dates) from the eCourts data API and maps them to their
  matters, feeding the deadline tracker automatically.

- LAWYER daily cause list on WhatsApp (BUILT 2026-08-14 — was PLANNED, added 2026-07-07):
  diary_service.send_daily_cause_lists() + workers/diary.py, beat 12:30 UTC = 18:00 IST.
  Opt-in per lawyer via law.users.daily_cause_list_enabled + whatsapp_number (falls back to
  users.phone). Sends NOTHING when nothing is listed tomorrow — an "you have nothing on"
  message every evening trains people to ignore the channel. Caps at 25 items with a
  "…see the app" pointer. If WhatsApp delivery fails the list is written as an in-app
  notification instead, so it still reaches the lawyer.
  KNOWN TODO: no settings UI yet for whatsapp_number / daily_cause_list_enabled — the columns
  exist and the job reads them, but nothing lets a lawyer turn it on from the app.
  Every evening (e.g. 6 PM IST), send the lawyer their own next-day cause list
  directly on WhatsApp — no login needed to know what's in court tomorrow.
  → Message lists every matter with a hearing tomorrow, sorted by court/bench:
    "Kal (tomorrow's date) ki cause list:
     1. [Case Name] — [Court], [Case No.]
     2. [Case Name] — [Court], [Case No.]
     ..."
  Source: same eCourts sync data already feeding the Deadline Tracker — no new
  data source needed, just a scheduled Celery job (mirrors send_whatsapp design)
  querying tomorrow's next_hearing_date across the lawyer's matters.
  Opt-in per lawyer (WhatsApp number on their profile, not per-matter like the
  client reminders above).
  Distinct from CLIENT WhatsApp reminders above: this is internal, for the
  lawyer/firm only, sent daily regardless of how far out the hearing is (not
  tied to the 30/7/1-day deadline cadence).

### 10. Legal Process Guide
- Confirmed pain: junior lawyers don't know which application to file
- Moved from Phase 2 to Phase 1 based on lawyer research
- Input: matter type + court + brief facts
- Output: step-by-step procedure:
  → Which application/form to file
  → Which CPC order applies
  → Court jurisdiction check
  → Documents required
  → Approximate court fees
  → Limitation period with calculation
  → What happens after filing (timeline)
- Data is manually curated and verified — NOT generated by AI
  AI reads this structured data and presents it
  Never generates procedural information from memory
- Covers: civil suits, criminal matters, consumer cases,
  cheque bounce, property disputes, matrimonial matters
- Specifically for Punjab/Haryana district courts
- Feedback loop: lawyer can flag incorrect procedure
  → flagged for manual review and correction

### 11. Case Argument Generator (PLANNED — "Test 0", not built yet)
- This is where the "find / verify / insert citations" capability that was removed from
  Reply to Notice (Feature 7) now belongs.
- Intended scope: take a matter/position → find relevant VERIFIED judgments (reusing
  SearchService, which already returns only self-hosted/verified citations), and build
  supporting legal arguments with those citations woven in.
- Next step: define exactly how it works + what it needs, then build a first version.
  Until then it does not exist in code.

No Punjabi translator
No judge analytics feature (but DO collect judge data from day one — see below)
No clause analyser
No contract redliner
No mobile app
No Redis cache (add Phase 2)
No managed message bus (Celery + Redis is Phase 1)
No managed identity provider (simple JWT Phase 1)
No SuperAdvocate Audit vertical
No SuperAdvocate Visa vertical
No Kubernetes
No microservices
No per-seat billing (tiered plans only)
No Word add-in
No client portal
No time and billing tracker
No outcome predictor
No Hindi drafting
eCourts integration — BUILT in Phase 1 via a LICENSED third-party data API (not the
  official NIC API, not scraping). See ECOURTS INTEGRATION below.
No LawFinder/LawHerald integration (no public APIs — build own DB from public sources)

---

## JUDGE DATA COLLECTION — START PHASE 1, FEATURE PHASE 2

Research confirmed: 25-30 judges per district court in Punjab.
Each judge stays ~3 years then transfers within Punjab — may return.
Judge behaviour tracking across career is high-value feature.

Start collecting NOW even though feature launches Phase 2:
- Extract judge names from every case ingested via eCourtsIndia API
- Store: judge_name, court, year, matter_type, outcome
- Track judge transfers over time
- The longer we collect — the richer the Phase 2 feature

```
law.judge_analytics table (build in Phase 1):
  judge_name        VARCHAR(255)
  court             VARCHAR(255)
  year              INTEGER
  matter_type       VARCHAR(100)
  outcome           VARCHAR(50)   — granted/refused/allowed/dismissed
  judgment_id       UUID references law.citations
  created_at        TIMESTAMPTZ
```

Do NOT build the UI or analytics feature in Phase 1.
Just collect the data silently in the background.

---

## ECOURTS POSITIONING

eCourts app is used by lawyers for receiving court orders.
Do NOT compete with eCourts. Complement it:

"Get your order from eCourts.
 Upload it to SuperAdvocate.
 SuperAdvocate extracts all key info,
 adds it to your matter,
 sets deadline reminders automatically."

---

## ECOURTS INTEGRATION (BUILT — Phase 1)

Auto-pull next-hearing dates for the logged-in lawyer's matters.

### DATA SOURCE — non-negotiable

Use the LICENSED eCourtsIndia REST API (`webapi.ecourtsindia.com`, Bearer token
`eci_live_…`). Validated working July 2026.

**CONFIRMED — all official gov portals are CAPTCHA-gated:**
- `panchkula.dcourts.gov.in` — advocate search has image CAPTCHA
- `hcservices.ecourts.gov.in` — enrollment/bar-code search has CAPTCHA
- `services.ecourts.gov.in` — all search pages CAPTCHA-gated
There is no official government route that allows automated advocate/case lookups
without solving a CAPTCHA. Do NOT attempt any official portal automation — it is
technically fragile, legally risky, and would silently serve wrong hearing dates.
The official NIC API needs a govt MoU; pursue separately if ever wanted.

**CAPTCHA on eCourtsIndia.com** — the ecourtsindia.com profile/search UI also uses
CAPTCHA and is NOT a substitute. Only `webapi.ecourtsindia.com` REST API is
CAPTCHA-free. Use that exclusively.

### REST API REFERENCE (`webapi.ecourtsindia.com`)

```
GET  /api/partner/search
  Params: Advocates, CaseStatuses=PENDING, StateCodes (2-letter, e.g. HR/PB/CH),
          PageSize (max 100), Page, SortBy=nextHearingDate, SortOrder=asc
  Response: { data: { results: [...], hasNextPage: bool } }
  Results field names: cnr, petitioners[], respondents[], courtName, courtCode,
                       caseStatus, nextHearingDate, filingDate,
                       petitionerAdvocates[], respondentAdvocates[], caseType
  Pagination: iterate Page 1..50 while hasNextPage=true
  District filter: StateCodes narrows by state; district is filtered client-side
                   by matching courtCode prefix (e.g. "HRPK" for Panchkula)

GET  /api/partner/case/{CNR}
  Response: { data: { courtCaseData: { cnr, petitioners[], respondents[],
             courtName, caseStatus, nextHearingDate, lastHearingDate,
             judges[], historyOfCaseHearings[], interimOrders[], ... } } }

POST /api/partner/case/bulk-refresh
  Body: { cnrs: ["CNR1", "CNR2", ...] }  (max 50 per call, chunk if more)
  Async — results appear when dateModified advances.

Rate limits: 100 req/min · 3k req/hr · 50k req/day
```

### CITY → STATE/DISTRICT MAPPING

The API takes StateCodes (HR/PB/CH), not districts. District filtering is done
client-side by checking the `courtCode` prefix in results.

```python
# backend/services/ecourts_api_service.py
CITY_TO_STATE_CODE     = { "panchkula": "HR", "gurugram": "HR", "ludhiana": "PB", ... }
CITY_TO_DISTRICT_PREFIX = { "panchkula": "HRPK", "gurugram": "HRGR", "ludhiana": "PBLD", ... }
```

### HOW IT WORKS

1. Lawyer's `ecourts_advocate_name` is stored in `law.users`.
   No city field in the user model — city is stored client-side in
   `localStorage('sa-ecourts-city')` to avoid a migration.
2. `search_pending_cases(advocate_name, state_code, district_prefix)` paginates
   the REST API and filters client-side by district prefix.
3. `get_case_by_cnr(cnr)` fetches full detail for a single CNR.
4. Import endpoint upserts each case as a Matter (keyed by CNR) and sets
   `next_hearing_date` → feeds the Deadline Tracker automatically.
5. If ECOURTS_API_TOKEN is not configured the service raises
   `EcourtsAPINotConfigured` — it NEVER fabricates dates.

### PIECES

```
Config:
  ECOURTS_API_BASE      = https://webapi.ecourtsindia.com
  ECOURTS_API_TOKEN     = eci_live_…  (licensed vendor Bearer token)

Models (DB):
  law.users.ecourts_advocate_name   — advocate name as registered on eCourts
  law.users.bar_council_number      — bar council enrolment number (stored, not used for lookup)
  law.users.ecourts_state_code      — e.g. "HR" (stored, used as default state filter)
  law.matters.cnr_number            — Case Number Record (unique per case)
  law.matters.case_status           — PENDING / DISPOSED etc.
  law.matters.ecourts_synced_at     — last sync timestamp
  law.matters.ecourts_tracked       — bool, opt-in per matter
  (Alembic migrations 005_ecourts_integration, 006_ecourts_bar_council)

Services:
  backend/services/ecourts_api_service.py  — PRIMARY: REST API calls
    search_pending_cases(advocate_name, state_code, district_prefix)
    get_case_by_cnr(cnr)
    bulk_refresh(cnrs)
    city_to_state_code(city), city_to_district_prefix(city)
    slug_to_advocate_name(slug)   — "ashish-gupta" → "Ashish Gupta"
    Exceptions: EcourtsAPIError, EcourtsAPINotConfigured

  backend/services/ecourts_service.py — legacy sync logic (advocate-search sync,
    CNR refresh for existing matters). Still used by /ecourts/sync and /ecourts/refresh-cnr.

API endpoints (backend/api/ecourts.py):
  GET  /ecourts/status               — integration status + profile fields
  PUT  /ecourts/profile              — set advocate name / bar council / state code
  GET  /ecourts/states               — list state codes for UI dropdown
  GET  /ecourts/preview-my-cases     — NEW (Jul 2026): zero-input preview for dashboard
                                        Uses logged-in user's stored name, optional ?city=
                                        Returns pending cases; raises 400 if no name set
  GET  /ecourts/lawyer-cases/{slug}  — discovery by profile slug (onboarding wizard)
  GET  /ecourts/case/{cnr}           — single CNR detail (CNR auto-fill on Add Matter)
  POST /ecourts/sync                 — advocate-search sync (legacy)
  POST /ecourts/refresh-cnr          — CNR-based hearing date refresh for existing matters
  POST /ecourts/import-cnrs          — bulk import cases as Matters

Daily job:
  backend/workers/ecourts.py — thin Celery wrapper calling refresh-cnr logic
  Beat schedule: register in celery_app
```

### DASHBOARD UX — ONE-CLICK IMPORT (BUILT Jul 2026)

When the lawyer has no cases imported yet, the dashboard shows a banner:
  **"Your eCourts case data is ready to pull"** → "Connect eCourts →" button

Clicking opens `EcourtsQuickImport.tsx` (not the old 4-step `EcourtsOnboarding` wizard):
- Auto-fetches pending cases on open using the lawyer's stored name — no input needed
- Optional "Filter by city" collapse (city remembered in `localStorage('sa-ecourts-city')`)
- All cases pre-selected; lawyer can deselect individual ones
- "Import N cases" → modal closes immediately → background `POST /ecourts/import-cnrs`
  → Sonner toast: "Importing N cases…" updates to "N cases imported. Hearing dates sync daily."

Frontend files:
  frontends/law-v2/src/components/app/EcourtsQuickImport.tsx  — new one-click import modal
  frontends/law-v2/src/routes/app.index.tsx                   — dashboard, uses above
  frontends/law-v2/src/routes/app.tsx                         — layout, has <Toaster /> (bottom-right)
  frontends/law-v2/src/api/ecourts.ts                         — previewMyCases() + updated DiscoveredCase

NOTE: `EcourtsOnboarding.tsx` (the 4-step wizard) still exists in the codebase but is
no longer wired to the dashboard. It can be used for fallback / settings flows.

### TOAST SYSTEM (BUILT Jul 2026)

Sonner (v2) is wired app-wide:
- `<Toaster richColors position="bottom-right" />` in `frontends/law-v2/src/routes/app.tsx`
- Import `toast` from `'sonner'` in any component — it works everywhere under `/app`
- Use `toast.loading(msg)` → `toast.success(msg, { id })` / `toast.error(msg, { id })`
  for background-operation feedback (e.g. eCourts import, file processing)

---

### Schemas
- shared    — audit_logs, firms billing data
- law       — all law vertical tables
- Phase 1 only — no audit or visa schemas yet

### Every table must have:
```sql
id          UUID PRIMARY KEY DEFAULT gen_random_uuid()
created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
deleted_at  TIMESTAMPTZ DEFAULT NULL
```

### Every law schema table must also have:
```sql
firm_id     UUID NOT NULL
```

### Critical rules:
- Soft deletes everywhere — deleted_at column — never hard delete
- UUID primary keys — never integers
- TIMESTAMPTZ always — never plain TIMESTAMP
- Row Level Security enabled on every table
- SET app.firm_id at start of every DB session
- firm_id injected from JWT always — never from request body
- All times stored as UTC — display as IST in frontend

---

## SECURITY — ENFORCE ON EVERY ENDPOINT

Four layers in this exact order:

```
Layer 1: JWT validation     — middleware, every request
Layer 2: RBAC check         — permission decorator
Layer 3: Resource guard     — firm_id ownership check
Layer 4: PostgreSQL RLS     — last line of defence
```

### Roles
- super_admin  — full platform access
- firm_admin   — full firm access + user management + billing
- lawyer       — drafts + search + upload
- staff        — upload + library only
- trial        — 3 drafts + 5 searches lifetime

### Critical security rules:
- firm_id always from JWT claims — never from request body
- vertical always from JWT claims — never from request body
- Wrong firm_id access → return 404 not 403 (never reveal existence)
- On logout: blacklist JWT token
- On password change: blacklist all tokens for that user
- Sanitise ALL document content before inserting into AI prompts
  (prompt injection protection — GAP-001)
- Never log document content or client names (PII — DPDP violation)
- Log actions and IDs only

---

## AI / LLM RULES

### Model usage:
- GPT-4o:       Filing drafts only — expensive
- GPT-5.2:      PDF Extractor — structured extraction + streaming readable
                briefing (READABLE_MODEL). Check OpenAI API quota before using at
                scale; fall back to GPT-5.4-mini if quota is insufficient. See Feature 5.
- GPT-4o-mini:  Everything else — RAG, extraction, synopsis, reply
- Ada-002:      All embeddings (text-embedding-ada-002)

Note: GPT-5.x models (5.2, 5.4-mini, 5.5) reject temperature/top_p params.
LLMService routes them through max_completion_tokens via extra_body.

### Critical rules:
- ALL AI calls go through LLMService class
- Never instantiate OpenAI client outside LLMService
- Never call OpenAI API directly from endpoints or services
- Hard token limit per firm per day (GAP-003)
- Alert when single request exceeds 10,000 tokens
- Retry on RateLimitError: 3x with backoff (1s, 2s, 4s)
- On ServiceUnavailableError: retry 3x then graceful message
- On ContentFilterError: no retry — return specific message
- On TokenLimitError: no retry — "document too large, split it"

### Citation verification (every draft):
- Extract all citations from AI output
- Check local citations DB first
- Fallback to government sources (phase 2) if not found
- Verified ✓ green / Unverified ⚠ amber / Fabricated ✗ red
- Never deliver draft with unverified citations silently

---

## CODING CONVENTIONS

### Always:
- Async everywhere — never sync database calls
- All business logic in services/ — never in api/ or workers/
- Celery tasks are thin wrappers — call services/ only
- Use parameterised queries — never f-strings in SQL
- UUID everywhere — never integer IDs
- Return standardised error shape — never raw exceptions
- GZipMiddleware enabled (GAP-034)
- Every endpoint needs request_id in response headers

### Never:
- Never f-strings in SQL queries
- Never trust firm_id or vertical from request body
- Never call OpenAI API directly from endpoints
- Never hard delete any record
- Never store secrets in code or commit .env to git
- Never skip JWT validation
- Never return 403 for wrong firm_id — always 404
- Never log document content, draft text, or client names

---

## API CONVENTIONS

```
Base path:      /api/v1/
Response shape:
{
  "success": true,
  "data": {},
  "error": { "code": "", "message": "", "action": "" },
  "meta": { "request_id": "", "version": "v1" }
}

Rate limit:     60 requests/minute per firm
File uploads:   Multipart form data — max 50MB
Pagination:     Cursor-based — never offset
CORS:           law.superadvocate.ai only
Compression:    GZipMiddleware enabled
```

---

## LOGGING RULES

```
Application logs:   Google Cloud Logging
Request logs:       Every API call — middleware
Audit logs:         PostgreSQL shared.audit_logs — permanent
Analytics:          Cloud Monitoring custom metrics

Log these:          action, user_id, firm_id, resource_id,
                    duration_ms, status_code, request_id

Never log:          document content, draft text,
                    client names, search query content,
                    any PII whatsoever
```

---

## BACKGROUND JOBS (CELERY)

```
document_ingest:    PDF uploaded → OCR → chunk → embed → index
                    Timeout: 10 minutes
                    Retry: 3x exponential backoff
                    On fail: status="failed", notify user

citation_verify:    Draft generated → extract citations →
                    check DB → API fallback
                    Timeout: 2 minutes

send_whatsapp:      Deadline/hearing reminders to clients
                    Provider: WhatsApp Business API (Meta)
                    Triggered by: deadline_tracker service
                    Cost: ~₹0.50-1 per message

send_email:         Invites, indexing complete, deadline alerts
                    Provider: SendGrid

usage_report:       Daily cron — aggregate usage per firm,
                    check limits, send 80% warnings

judgment_ingest:    Daily cron — new judgments via eCourtsIndia API
                    (P&H HC + Punjab/Haryana district filter)
                    → GET /search → GET /case/{cnr} (markdownContent)
                    → chunk → embed → upsert pgvector
                    Never scrape Indian Kanoon (competitor)

Design rule:        All logic in services/ layer
                    Worker = thin wrapper only
                    Swap to Cloud Run Jobs Phase 2
                    with zero refactoring
```

---

## ENVIRONMENT VARIABLES

```
# OpenAI API (direct — not Azure)
OPENAI_API_KEY                              # from platform.openai.com
GPT4O_MODEL                 = gpt-4o
GPT4O_MINI_MODEL            = gpt-4o-mini
GPT52_MODEL                 = gpt-5.2
EMBEDDING_MODEL             = text-embedding-ada-002

# Database (Cloud SQL PostgreSQL + pgvector)
DATABASE_URL                               # postgresql+asyncpg://user:pass@/db?host=/cloudsql/...
CLOUD_SQL_CONNECTION_NAME                  # project:region:instance (for Cloud SQL proxy)

# Cache / Celery (Cloud Memorystore Redis)
REDIS_URL                                  # redis://10.x.x.x:6379

# Storage (Google Cloud Storage)
GCS_BUCKET_NAME                            # e.g. superadvocate-documents
GCP_PROJECT_ID                             # GCP project ID

# eCourts API
ECOURTS_API_BASE            = https://webapi.ecourtsindia.com
ECOURTS_API_TOKEN           = eci_live_…   (licensed eCourts data vendor)

# Messaging
SENDGRID_API_KEY
WHATSAPP_API_TOKEN
WHATSAPP_PHONE_NUMBER_ID

# Auth
JWT_SECRET_KEY
JWT_ALGORITHM               = RS256
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS   = 30

# App
ENVIRONMENT                 = development
```

All secrets in Google Secret Manager in staging and production.
.env file for local development only — never commit to git.

---

## MUST BUILD ON DAY ONE

These are not optional — build before anything else:

```
1. GET /api/v1/health
   Returns: DB status, pgvector status,
   OpenAI connectivity — for Cloud Run
   and UptimeRobot monitoring

2. GZipMiddleware
   One line in main.py — do it immediately

3. Request logging middleware
   Every request logged with request_id,
   firm_id, path, status, duration_ms

4. JWT validation middleware
   Every request validated before
   reaching any endpoint

5. docker-compose.yml
   FastAPI + PostgreSQL + Redis + Celery
   One command: docker-compose up
   Everything runs locally
```

---

## GAPS TO HANDLE DURING BUILD

```
GAP-001: Sanitise document content before AI prompts
GAP-003: Hard token limit per firm per day
GAP-004: JWT blacklist on logout/password change
GAP-034: GZipMiddleware from day one
GAP-040: Verify Razorpay webhook signatures
GAP-044: Health check endpoint on day one
GAP-031: Never f-strings in SQL — parameterised only
GAP-032: Never log PII — actions and IDs only
GAP-035: Delete from pgvector when document deleted
GAP-043: Explicit timeouts — RESOLVED for search:
         embed_query: asyncio.wait_for timeout=8s (fallback to keyword)
         search endpoint: asyncio.wait_for timeout=25s → HTTP 504
         browser: 120s axios timeout (still to enforce app-wide)
GAP-050: TanStack Query v5 AbortController — RESOLVED for search:
         Replaced useMutation with plain async/await + searchIdRef guard
         Rule: never use useMutation for user-triggered search/fetch calls
```

---

## PERFORMANCE TARGETS

```
Search query:           < 3 seconds end to end
Filing draft:           < 30 seconds
Upload API response:    < 3 seconds (async — returns immediately)
PDF extraction:         < 10 seconds
Dashboard load:         < 2 seconds
Login:                  < 1 second
```

---

## BILLING

```
Plans (Phase 1):
Solo:        ₹1,500/month — 1 user
Small Firm:  ₹3,500/month — up to 5 users
Mid Firm:    ₹6,000/month — up to 15 users
Large Firm:  ₹12,000/month — unlimited

Trial:       30 days full access no credit card
             trial_days INTEGER DEFAULT 30 in firms table
             90-day extended: set by super_admin only

Post-trial:  3 drafts/month + 5 searches/month
             Documents stay indexed
             Not full lockout

Payment:     Razorpay
```

---

## CITATION SOURCES (PRIORITY ORDER)

```
1. eCourtsIndia API — webapi.ecourtsindia.com — ALL Indian courts (SC, HC,
   District, Tribunals) — 28.3 Cr+ records — LICENSED DATA VENDOR — PRIMARY
   Replaces all direct government portal scraping. Covers P&H HC + all Punjab/
   Haryana district courts. markdownContent = full order text for indexing.
   Certified true copy PDFs served on demand via /order/{filename}.

2. LiveLaw    — latest judgment summaries — scrape carefully, summaries only
3. Law Herald — Punjab/Haryana specific — approach for partnership
```

IMPORTANT — Indian Kanoon is now a COMPETITOR:
Indian Kanoon launched their own AI product called Prism with these features:
DocHub (document drafting), Know your Kanoon (legal chatbot),
Upload and Chat (RAG over own documents), CasePredictAI (outcome prediction).
They will NOT provide API access — they are protecting their own product.
Do NOT scrape Indian Kanoon — they are a direct competitor now.
Do NOT reference Indian Kanoon in any code, scraper, or service.
Build our citation database entirely from government sources.
Government judgment text is public domain — no competitor can block this.

LawFinder and LawHerald are paid services (LawFinder ₹3,900/month).
No public APIs. Do not scrape — their content is their commercial IP.
Build from public primary sources — same underlying judgments, built ourselves.

GAP-030 (Indian Kanoon API outreach) — CLOSED. They are a competitor.

---

## COMPETITIVE POSITIONING

Indian Kanoon launched Prism — a direct competitor with similar features.
They are national and generic. We are regional and deep.

```
Prism (Indian Kanoon):          SuperAdvocate:
────────────────────            ──────────────────────────
All India generic               Punjab/Haryana/Chandigarh
English only                    Punjab-specific procedures
Generic document drafting       Strategic filing drafter
                                (Win/Delay/Challenge/Settle)
No regional court knowledge     P&H HC + district court
                                formatting and procedures
No WhatsApp reminders           Client WhatsApp reminders
No deadline tracker             Deadline + condonation draft
No judge analytics              Punjab judge tracking
No legal process guide          Step-by-step Punjab procedures
National pricing                Punjab practitioner pricing
```

Our moat is depth in one geography — not breadth across India.
"Prism is for Indian lawyers. SuperAdvocate is for YOUR court."

---

## PROMPT ENGINEERING RULES

### Location
All LLM prompts live in backend/services/prompts/ — one file per feature.
Never inline prompts in service files — always import from prompts/.

```
backend/services/prompts/
├── __init__.py
├── base_prompt.py           # PromptTemplate base class
├── filing_drafter.py        # Strategic Filing Drafter prompts
├── reply_generator.py       # Smart Reply Generator prompts
├── case_synopsis.py         # Case Synopsis Generator prompts
├── pdf_extractor.py         # PDF Extractor prompts
├── legal_process_guide.py   # Legal Process Guide prompts
└── citation_verifier.py     # Citation verification prompts
```

### Rules
- Changing a prompt = making a PR — never change prompts casually
- Prompt regression tests run before every deploy
- Every prompt file contains: SYSTEM_PROMPT, USER_PROMPT_TEMPLATE, MODEL
- All prompts output structured JSON — never free text
- Every prompt instructs the model to admit uncertainty explicitly

### Base Structure (every prompt file)
```python
MODEL = "gpt-4o-mini"  # override to gpt-4o only for filing_drafter

SYSTEM_PROMPT = """..."""

USER_PROMPT_TEMPLATE = """..."""  # uses {variable} placeholders

OUTPUT_SCHEMA = {...}  # expected JSON structure
```

### Prompt 1 — Case Synopsis (filing_synopsis.py)
```python
MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = """You are a legal document analyst specialising in
Indian law, specifically Punjab and Haryana High Court and district
court matters. Extract structured information from Indian court
judgments and petitions. Always respond in valid JSON only.
Never fabricate information not present in the document.
If a field cannot be determined, set it to null."""

USER_PROMPT_TEMPLATE = """Analyse this Indian court document and
extract structured information.

Document text:
{document_text}

Return JSON with this exact structure:
{{
  "case_name": "full case name",
  "petitioner": "petitioner name",
  "respondent": "respondent name",
  "court": "court name",
  "judgment_date": "YYYY-MM-DD or null",
  "case_number": "case number or null",
  "facts": "2-3 sentence summary of facts",
  "issues": ["issue 1", "issue 2"],
  "held": "what the court decided",
  "citations_used": ["citation 1", "citation 2"],
  "relief_granted": "what relief was granted or null",
  "confidence": 0-10
}}"""
```

### Prompt 2 — PDF Extractor (pdf_extractor.py)
```python
MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = """You are a legal document data extraction specialist
for Indian courts. Extract specific structured fields from court orders,
judgments, and legal documents. Always respond in valid JSON only.
For each field provide a confidence score 0-100.
If a field is not clearly present in the document set value to null
and confidence to 0. Never guess or infer values not explicitly stated."""

USER_PROMPT_TEMPLATE = """Extract structured data from this Indian
court document.

Document text:
{document_text}

Return JSON with this exact structure:
{{
  "case_number": {{"value": "...", "confidence": 0-100}},
  "petitioner": {{"value": "...", "confidence": 0-100}},
  "respondent": {{"value": "...", "confidence": 0-100}},
  "court": {{"value": "...", "confidence": 0-100}},
  "date_of_order": {{"value": "YYYY-MM-DD", "confidence": 0-100}},
  "next_hearing_date": {{"value": "YYYY-MM-DD", "confidence": 0-100}},
  "relief_granted": {{"value": "...", "confidence": 0-100}},
  "conditions_imposed": {{"value": ["condition 1", "condition 2"], "confidence": 0-100}},
  "amount": {{"value": "...", "confidence": 0-100}},
  "judge_name": {{"value": "...", "confidence": 0-100}}
}}"""
```

### Prompt 3 — RAG Answer Synthesis (rag_synthesis.py)
```python
MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = """You are a legal research assistant for Indian lawyers
practising in Punjab and Haryana courts. Answer questions based ONLY
on the provided document excerpts. Always cite your source.
If the answer is not in the provided excerpts, say so explicitly —
never fabricate information. Rate your confidence 0-10."""

USER_PROMPT_TEMPLATE = """Answer this legal question based only on
the provided document excerpts.

Question: {query}

Document excerpts:
{context_chunks}

Return JSON:
{{
  "answer": "direct answer to the question",
  "confidence": 0-10,
  "sources": [
    {{
      "document_name": "...",
      "page": "...",
      "excerpt": "brief relevant quote under 15 words"
    }}
  ],
  "answer_found": true/false,
  "missing_information": "what additional docs would help or null"
}}"""
```

### Prompt 4 — Strategic Filing Drafter (filing_drafter.py)
```python
MODEL = "gpt-4o"  # Only feature using GPT-4o

SYSTEM_PROMPT = """You are an expert Indian lawyer specialising in
Punjab and Haryana High Court and district court matters with 20 years
of experience. Draft professional court filings formatted specifically
for Punjab/Haryana courts. Use formal legal language.
Never fabricate citations — only use citations provided to you.
Always follow the filing objective specified by the lawyer."""

USER_PROMPT_TEMPLATE = """Draft a {filing_type} for the following matter.

Filing objective: {objective}
(Win on merits / Delay proceedings / Challenge jurisdiction /
Seek settlement / Preserve appeal rights)
Adapt your entire drafting strategy to this objective.

Court: {court}
Client: {client_name}
Facts: {facts}
Relief sought: {relief}

Verified citations to use (use ONLY these — do not add others):
{verified_citations}

Return JSON:
{{
  "draft_sections": {{
    "court_heading": "...",
    "parties_section": "...",
    "facts_section": "...",
    "grounds_section": "...",
    "prayer_section": "...",
    "verification": "..."
  }},
  "citations_used": ["citation 1", "citation 2"],
  "strategy_notes": "brief note on how objective influenced drafting",
  "completeness_score": 0-100,
  "missing_facts": ["fact 1 that would strengthen the draft"]
}}"""
```

### Prompt 5 — Reply Generator (reply_generator.py)
```python
MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = """You are an Indian legal assistant specialising in
drafting replies to legal notices for Punjab and Haryana practitioners.
Extract allegations from legal notices precisely.
For each allegation suggest legal grounds supported by verified citations.
Always respond in valid JSON only."""

ALLEGATION_EXTRACTION_TEMPLATE = """Extract all allegations/claims
from this legal notice.

Notice text:
{notice_text}

Return JSON:
{{
  "sender": "...",
  "recipient": "...",
  "notice_date": "YYYY-MM-DD or null",
  "notice_type": "property/cheque bounce/employment/other",
  "allegations": [
    {{
      "point_number": 1,
      "allegation": "exact allegation in plain language",
      "legal_basis_claimed": "what law/section sender cited or null"
    }}
  ]
}}"""

LEGAL_GROUNDS_TEMPLATE = """For this allegation in an Indian legal
notice, suggest legal grounds to deny it.

Allegation: {allegation}
Matter type: {matter_type}
Verified citations available: {verified_citations}

Return JSON:
{{
  "suggested_grounds": [
    {{
      "ground": "legal ground in plain English",
      "legal_provision": "relevant section/act",
      "citation": "case citation if applicable or null",
      "strength": "strong/medium/weak"
    }}
  ],
  "recommended_stance": "deny/admit/partial",
  "reasoning": "why this stance is recommended"
}}"""
```

### Prompt 6 — Legal Process Guide (legal_process_guide.py)
```python
MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = """You are a procedural guide for Indian lawyers in
Punjab and Haryana courts. Answer ONLY from the provided structured
knowledge base data. Never generate procedural information from memory.
If the specific court procedure is not in the knowledge base,
say so explicitly and direct the lawyer to verify at the court registry."""

USER_PROMPT_TEMPLATE = """A lawyer needs procedural guidance.

Matter type: {matter_type}
Court: {court}
Brief facts: {facts}

Knowledge base data for this matter type and court:
{knowledge_base_data}

Return JSON:
{{
  "steps": [
    {{
      "step_number": 1,
      "action": "what to do",
      "details": "specific details",
      "source": "which law/rule this comes from"
    }}
  ],
  "documents_required": ["document 1", "document 2"],
  "court_fees": "approximate amount or 'verify at registry'",
  "limitation_period": "X days/months/years from Y event",
  "limitation_calculation": "how to calculate",
  "typical_timeline": "how long this matter typically takes",
  "confidence": 0-10,
  "verify_at_registry": true/false
}}"""
```

### Prompt 7 — Citation Verification (citation_verifier.py)
```python
MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = """You are a citation extraction specialist for Indian
legal documents. Extract all case citations from legal text precisely.
Return only what is explicitly present — never infer or complete
partial citations."""

EXTRACTION_TEMPLATE = """Extract all case citations from this
Indian legal document text.

Text:
{draft_text}

Return JSON:
{{
  "citations": [
    {{
      "raw_text": "exact citation as written in document",
      "case_name": "party names only",
      "year": 2024,
      "reporter": "SCC/AIR/SCR/etc or null",
      "volume": "volume number or null",
      "page": "page number or null",
      "court": "court name or null"
    }}
  ]
}}"""
```

### Prompt Testing Rule
Before adding any prompt to production:
- Test with 10 real Indian legal documents
- Verify JSON structure is always returned
- Verify confidence scores are calibrated correctly
- Verify no hallucination on out-of-context questions
- Add test cases to tests/prompt_regression/

---

## SYNC PROCESS
```
python scripts/sync_claude_md.py
```
Reviews the diff before committing.
Never auto-merge CLAUDE.md changes.
