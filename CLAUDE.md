# CLAUDE.md — Nikhar Platform
# Last Updated: April 2026 (v3 — competitor update + prompt engineering added)
# Read this file completely before writing any code.

---

## WHAT THIS PROJECT IS

Nikhar is an AI-powered legal workspace for solo lawyers and small firms
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

## CURRENT PHASE

Phase 1 only. Do not build anything outside this list.
Do not suggest Phase 2 features. Do not over-engineer.

---

## FOLDER STRUCTURE

nikhar/
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

### Frontend
- Framework:   React 18
- Styling:     TailwindCSS
- Server state: React Query
- UI state:    Zustand
- Target:      1366x768 optimised

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
- Sources: eSCR (SC official) + P&H HC official website + Punjab district court portals
- Do NOT use Indian Kanoon — they are now a direct competitor (launched Prism AI)
- Minimum 10,000 judgments before launch — all from government sources
- Daily Celery cron updates new judgments
- Hybrid search: vector + keyword combined
- Works from day one — no upload needed by lawyer
- Every result shows: case name, court, year, citation, source URL

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

### 6. Case Synopsis Generator
- Upload any judgment or petition
- Output structured one-pager:
  parties / facts / issues / held / citations used
- Export as .docx

### 7. Smart Reply Generator
- Upload legal notice PDF
- Extract each allegation automatically
- For each allegation show:
  → Admit / Deny / Partial options
  → AI suggests 2-3 legal grounds if denied
  → Verified citations supporting each ground
- Generate complete reply incorporating lawyer's admit/deny decisions
- Verified citations only — no unverified citations in final reply

### 8. Strategic Filing Drafter
- Input: filing type + brief form + filing objective
- Filing objective selector:
  [ ] Win on merits
  [ ] Delay proceedings (CPC)
  [ ] Challenge jurisdiction
  [ ] Seek settlement
  [ ] Preserve appeal rights
- Draft strategy changes completely based on objective
- Citation verification on every citation before delivery
- Draft quality score (0-100) shown before lawyer accepts
- Score dimensions: citation safety 35% / completeness 25% /
  legal accuracy 20% / brief coverage 15% / language 5%
- Block draft if citation safety below 50%

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

No Punjabi translator
No judge analytics feature (but DO collect judge data from day one — see below)
No clause analyser
No contract redliner
No mobile app
No Redis cache (add Phase 2)
No Azure Service Bus (Celery Phase 1)
No Azure AD B2C (simple JWT Phase 1)
No Nikhar Audit vertical
No Nikhar Visa vertical
No Kubernetes
No microservices
No per-seat billing (tiered plans only)
No Word add-in
No client portal
No time and billing tracker
No outcome predictor
No Hindi drafting
No eCourts API integration (Phase 2)
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
 Upload it to Nikhar.
 Nikhar extracts all key info,
 adds it to your matter,
 sets deadline reminders automatically."

Phase 2: eCourts official API integration
(auto-pull next hearing dates directly)

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
- GPT-4o-mini:  Everything else — RAG, extraction, synopsis, reply
- Ada-002:      All embeddings

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
CORS:           law.nikhar.ai only
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
GAP-043: Explicit timeouts — browser 120s, FastAPI 90s
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
Prism (Indian Kanoon):          Nikhar:
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
"Prism is for Indian lawyers. Nikhar is for YOUR court."

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
