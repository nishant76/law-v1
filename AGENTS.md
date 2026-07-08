# AGENTS.md — SuperAdvocate Platform
# Last Updated: June 2026 (v6 — renamed Nikhar→SuperAdvocate; Draft-a-Filing rebuilt as template/live-fill (objective selector removed); Reply-to-Notice perspective + rewrite-in-legal-language, citations moved to Case Argument Generator; eCourts integration BUILT via licensed vendor; PDF extractor section-label + omit-empty refinements; v5 — PDF extractor routing-first prompt + GPT-5.2 readable model & quota caveat; v4 — frontend design system, search timeout fixes, UI patterns)
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
│   └── law/              # React 18 app — VERTICAL="law" hardcoded
├── shared/
│   └── components/       # Shared React components across verticals
├── scripts/
│   ├── scrapers/         # eSCR, P&H HC, district court scrapers (NO Indian Kanoon)
│   └── sync_claude_md.py # Syncs ADR changes to this file
├── docker-compose.yml
├── Dockerfile
└── AGENTS.md             # This file

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

### Frontend
- Framework:   React 18
- Styling:     TailwindCSS (custom design tokens — see FRONTEND DESIGN SYSTEM below)
- Server state: TanStack Query v5 (@tanstack/react-query ^5.80.2)
- UI state:    Zustand
- Routing:     React Router v6
- Target:      1366x768 optimised
- Fonts:       Plus Jakarta Sans (body), Fraunces (serif headings)

### AI / LLM
- Drafting:    GPT-4o (Azure OpenAI) — expensive, use only for filing drafts
- RAG/Extract: GPT-4o-mini (Azure OpenAI) — use freely for everything else
- Embeddings:  text-embedding-ada-002 — 1536 dimensions
- OCR:         Azure Document Intelligence

### Infrastructure (Azure — India Central region)
- Database:    Azure PostgreSQL Flexible Server
- Search:      Azure AI Search (hybrid — vector + keyword)
- Storage:     Azure Blob Storage
- Compute:     Azure App Service (B2)
- Secrets:     Azure Key Vault — never hardcode secrets anywhere
- Email:       SendGrid (free tier — 100/day)
- WhatsApp:    WhatsApp Business API (Meta official) — client reminders
- Monitoring:  Azure Application Insights
- CI/CD:       GitHub Actions → Azure App Service

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

Never call `embed_query` or any Azure OpenAI call without a timeout.
Never let a single Azure service call block the entire request indefinitely.

---

## PHASE 1 FEATURES — BUILD THESE ONLY

### 1. Document Library
- Upload PDF, DOCX, images (max 50MB per file)
- Store originals in Azure Blob Storage
- Background indexing via Celery: OCR → chunk → embed → index
- Status tracking: pending / processing / indexed / failed
- Retry button on failed documents with plain English error reason
- Google Drive connect option (read files, do not store originals)
- Soft delete only — never hard delete documents

### 2. Public Judgment Search
- Sources: eSCR / digiSCR (SC official) + P&H HC official website + Punjab district court portals
- Do NOT use Indian Kanoon — they are now a direct competitor (launched Prism AI)
- Minimum 10,000 judgments before launch — all from government sources
- Daily Celery cron updates new judgments
- Hybrid search: vector + keyword combined (keyword-only acceptable for the
  curated launch set; pgvector semantic ranking is a fast follow)
- Works from day one — no upload needed by lawyer
- Every result shows: case name, court, year, citation, source URL

LINK INTEGRITY — NON-NEGOTIABLE (see LAUNCH QUALITY MANDATE):
Every citation's link MUST resolve to the actual judgment. The pipeline enforces
this by construction — a citation with no working link is never shown.
- Each citation stores: blob_path (our self-hosted copy of the public-domain PDF),
  source_url (the official government link, shown as secondary "official source"),
  link_status ('pending'|'verified'|'self_hosted'|'dead'), link_checked_at.
- Primary "View Judgment" link serves OUR Blob copy → can never break.
  Judgment text is public domain (Copyright Act §52(1)(q)) — safe to self-host.
- Ingestion verifies every source_url (HTTP), downloads the PDF to Blob, and only
  then sets link_status='self_hosted'. Dead/unverified links are flagged, never
  displayed. Search filters out any citation without a working link.
- A periodic re-check job re-validates official links and our blob copies.
- NEVER hand-type a source_url and trust it. NEVER display a generic landing-page
  URL (e.g. ".../judgments") as if it were the specific judgment.

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
  Before relying on 5.2 at India scale, confirm the Azure GPT-5.2 deployment has
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
  Prompt: filing_template_prompt in prompts/filing_drafter.py (gpt-4o-mini dev / gpt-4o prod).
  Endpoints: POST /filing/template (describe), /filing/template/upload (improve a file),
  /filing/template/export (.docx).
- Live editor (two-pane): left = the draft with highlighted blanks; right = a Key Details
  panel (one input per blank — typing fills the draft live, client-side) + Find & Add
  Citations (reuses unified search, verified-only; selected citations are appended and exported).
- NOTE: the older objective-based generator (/filing/generate) + draft-quality scoring
  (citation safety 35% / completeness 25% / legal accuracy 20% / brief coverage 15% /
  language 5%; block if citation safety < 50) still exists in code for back-compat, but is
  no longer the UI flow.

### 9. Deadline Tracker
- Add matter with key dates: hearing, filing deadline, limitation period
- Reminders at 30 days, 7 days, 1 day before each deadline
- Reminder channels: in-app notification + email (SendGrid)
- If deadline missed: auto-suggest "Draft condonation of delay application?"
- One click → draft generated immediately

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
No Azure Service Bus (Celery Phase 1)
No Azure AD B2C (simple JWT Phase 1)
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
- Scrape judge names from every judgment in citations DB
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

DATA SOURCE — non-negotiable:
- Use a LICENSED third-party eCourts data API (webapi.ecourtsindia.com; Bearer token
  `eci_live_…`). The vendor sources the data; we only call a REST API.
- Do NOT scrape the official eCourts site. Its case-status-by-advocate page is
  CAPTCHA-gated; programmatically defeating that CAPTCHA is circumventing an access
  control (ToS/legal risk), fragile, and would silently serve stale/wrong hearing dates
  — fatal under the LAUNCH QUALITY MANDATE. (The official NIC API needs a govt MoU; pursue
  separately if ever wanted.)

HOW IT WORKS:
- Each lawyer stores their eCourts advocate name (law.users.ecourts_advocate_name).
- ecourts_service.search_cases_by_advocate() pulls their pending cases (cnr,
  nextHearingDate, parties, court, status); sync_firm_hearings() upserts each as a Matter
  (keyed by CNR) for the firm and updates next_hearing_date → feeds Deadlines/Hearings.
- If the API token is not configured the service raises ECourtsNotConfigured — it NEVER
  fabricates dates.

PIECES:
- Config: ECOURTS_API_BASE, ECOURTS_API_TOKEN.
- Model: law.matters.cnr_number / case_status / ecourts_synced_at / ecourts_tracked;
  law.users.ecourts_advocate_name. (Alembic migration 005_ecourts_integration.)
- Service: backend/services/ecourts_service.py. API: backend/api/ecourts.py
  (GET /ecourts/status, PUT /ecourts/advocate-name, POST /ecourts/sync).
- Daily job: backend/workers/ecourts.py (thin Celery wrapper; register the beat schedule
  in celery_app). Vendor rate limits: 100/min, 3k/hr, 50k/day.

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
                briefing (READABLE_MODEL). Restricted/limited-quota tier; fall
                back to GPT-5.4-mini if quota is insufficient. See Feature 5.
- GPT-4o-mini:  Everything else — RAG, extraction, synopsis, reply
- Ada-002:      All embeddings

Note: GPT-5.x models (5.2, 5.4-mini, 5.5) reject temperature/top_p params.
LLMService routes them through max_completion_tokens via extra_body.

### Critical rules:
- ALL AI calls go through LLMService class
- Never instantiate Azure OpenAI client outside LLMService
- Never call Azure OpenAI directly from endpoints or services
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
- Never call Azure OpenAI directly from endpoints
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
Application logs:   Azure Application Insights
Request logs:       Every API call — middleware
Audit logs:         PostgreSQL shared.audit_logs — permanent
Analytics:          App Insights custom events

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

scraper_update:     Daily cron — new judgments from
                    eSCR + P&H HC + district court portals
                    Never scrape Indian Kanoon (competitor)

Design rule:        All logic in services/ layer
                    Worker = thin wrapper only
                    Swap to Azure Functions Phase 2
                    with zero refactoring
```

---

## ENVIRONMENT VARIABLES

```
AZURE_OPENAI_ENDPOINT
AZURE_OPENAI_API_VERSION        = 2024-10-21
GPT4O_DEPLOYMENT                = gpt-4o
GPT4O_MINI_DEPLOYMENT           = gpt-4o-mini
EMBEDDING_DEPLOYMENT            = text-embedding-ada-002
AZURE_SEARCH_ENDPOINT
AZURE_SEARCH_KEY
DATABASE_URL
REDIS_URL
BLOB_CONNECTION_STRING
SENDGRID_API_KEY
WHATSAPP_API_TOKEN
WHATSAPP_PHONE_NUMBER_ID
ECOURTS_API_BASE                = https://webapi.ecourtsindia.com
ECOURTS_API_TOKEN               = eci_live_…   (licensed eCourts data vendor)
GPT52_DEPLOYMENT                = gpt-5.2
JWT_SECRET_KEY
JWT_ALGORITHM                   = RS256
ACCESS_TOKEN_EXPIRE_MINUTES     = 60
REFRESH_TOKEN_EXPIRE_DAYS       = 30
ENVIRONMENT                     = development
APPLICATIONINSIGHTS_CONNECTION_STRING
```

All secrets in Azure Key Vault in staging and production.
.env file for local development only — never commit to git.

---

## MUST BUILD ON DAY ONE

These are not optional — build before anything else:

```
1. GET /api/v1/health
   Returns: DB status, search status,
   OpenAI connectivity — for Azure App Service
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
GAP-035: Delete from Azure AI Search when document deleted
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
1. eSCR       — main.sci.gov.in — official SC reports — GOVERNMENT — safe
2. P&H HC     — highcourtchd.gov.in — all P&H HC judgments — GOVERNMENT — safe
3. Punjab District Courts — official portals — GOVERNMENT — safe
4. LiveLaw    — latest judgment summaries — scrape carefully, summaries only
5. Law Herald — Punjab/Haryana specific — approach for partnership
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
Never auto-merge AGENTS.md changes.
