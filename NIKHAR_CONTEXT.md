# NIKHAR_CONTEXT.md
# Read this file at the start of every new Claude chat session
# before asking any product or technical questions.
# Last updated: April 2026

---

## WHAT WE ARE BUILDING

Nikhar is an AI-powered legal workspace for solo lawyers and small firms
in Punjab, Haryana, and Chandigarh — specifically district court practitioners.

Tagline: "The AI that makes Indian lawyers unstoppable in court"

Target user: Solo practitioner, 4-10 years experience, district courts
Punjab/Haryana. Includes criminal AND civil litigation lawyers.

Holding company (planned): Gramme AI
Product name: Nikhar (Phase 1 — law vertical)
Future verticals: Nikhar Audit, Nikhar Visa (Phase 2+)

---

## FOUNDER CONTEXT

Lead Software Engineer, 11+ years experience in .NET, Azure PaaS,
and applied AI systems. Based in Patiala/Ludhiana, Punjab.
Currently at EPAM Systems.
Building Nikhar as a startup alongside current employment.

---

## MARKET INSIGHTS FROM LAWYER RESEARCH

3+ Punjab/Haryana district court lawyers interviewed. Key findings:

Confirmed pain points:
- Citation search without citation number = 1-40 mins per search
- Finding documents from own digital files = high pain
- Missing deadlines then filing condonation = confirmed pain
- Junior lawyers (0-5 yrs) don't know which application to file
- WhatsApp reminders to clients specifically requested by lawyers

Trusted sources lawyers use:
- eSCR (main.sci.gov.in) — most trusted for SC citations
- P&H HC (highcourtchd.gov.in) — most trusted for HC citations
- ChatGPT used but NOT trusted for citations — "can't rely on it"

Pricing reference: LawFinder charges ₹3,900/month — lawyers know
what paid legal tools cost.

---

## COMPETITOR LANDSCAPE

Indian Kanoon — launched Prism AI (direct competitor)
Features: DocHub, Know your Kanoon, Upload and Chat, CasePredictAI
Status: DO NOT contact, DO NOT scrape — they are a competitor
Build citation DB from government sources only

LawFinder — ₹3,900/month — no public API
SCC Online, Manupatra — paid, no scraping
LiveLaw — their summaries are their IP

Our moat:
- Punjab/Haryana deep focus vs national generic
- Strategic filing objectives (Win/Delay/Challenge/Settle/Preserve)
- WhatsApp client reminders in Hindi — no competitor does this
- Step-by-step Punjab court procedures for junior lawyers
- Citation verification with verified/unverified/fabricated badges

---

## CURRENT BUILD STATUS

Backend: COMPLETE — all 10 Phase 1 features built in FastAPI
Docker: Running locally (PostgreSQL + Redis + Celery + FastAPI)
Auth: Working — JWT, RBAC, blacklist, invite flow
Migrations: Applied — all tables created in law + shared schemas
OpenAI: API key added and configured

Citation scrapers:
- P&H HC scraper: WORKING — /index.php?linkid=218 confirmed
- eSCR scraper: URL correct — temporary 503 on SC server side
- eCourts: CAPTCHA blocked — correctly detected and logged

Known bugs being fixed:
- Unified search returning zero results — Azure AI Search not
  configured yet, need PostgreSQL full-text search fallback
- Document upload 500 error — document_service returning None

Test credentials (local only):
- API: http://localhost:8000
- Health: http://localhost:8000/api/v1/health
- DB: PostgreSQL on localhost:5433 (nikhar/nikhar/nikhar)

---

## UI DESIGN DECISIONS

### Prototype Files Location
All UI prototypes are in: ui-prototypes/
- ui-prototypes/nikhar-demo.html           ← COLOR REFERENCE (use this)
- ui-prototypes/nikhar-demo-responsive.html ← layout/responsiveness reference
- ui-prototypes/nikhar-final.html           ← combined prototype (may be revised)

### ACTIVE COLOR THEME — nikhar-demo.html

The canonical color palette comes from nikhar-demo.html.
Always use these exact values:

```css
:root {
  /* Primary */
  --navy:       #1B2E4B;   /* sidebar, headers, primary buttons */
  --navy-dark:  #111E30;   /* sidebar background */
  --navy-mid:   #243D61;   /* hover states */
  --navy-light: #2E4E7A;   /* search hero gradient */

  /* Accent */
  --gold:       #C9A84C;   /* highlights, badges, CTAs, active states */
  --gold-light: #E2C270;   /* hover gold */
  --gold-pale:  #FDF6E3;   /* gold tint background */

  /* Semantic */
  --green:      #1A6B3C;   /* verified citations ✓ */
  --green-bg:   #E8F5EE;
  --amber:      #B8860B;   /* unverified citations ⚠ */
  --amber-bg:   #FFF8E1;
  --red:        #8B1A1A;   /* fabricated citations ✗ / errors */
  --red-bg:     #FDECEA;

  /* Neutrals */
  --bg:         #F4F6F9;   /* page background */
  --card:       #FFFFFF;   /* card background */
  --border:     #DDE3EC;   /* borders */
  --text:       #1E2A3A;   /* primary text */
  --text-mid:   #4A5568;   /* secondary text */
  --text-light: #8A96A8;   /* hints, labels */
}
```

### Typography — nikhar-demo.html

```css
--font-body:  'Sora', sans-serif;         /* all body text, UI elements */
--font-serif: 'DM Serif Display', serif;  /* headings, case names, titles */
--font-mono:  'JetBrains Mono', monospace;/* citations only e.g. (2014) 8 SCC 273 */
```

Google Fonts import:
```
https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700
&family=DM+Serif+Display:ital@0;1
&family=JetBrains+Mono:wght@400;500
```

### Layout Rules

```
Desktop (1366x768 primary target):
- Fixed sidebar: 244px wide, navy-dark background
- Main content: remaining width, --bg background
- Cards: white background, 1px --border, 12px border-radius
- Topbar: 56px height, white background, border-bottom

Mobile (responsive — must work on phone):
- Bottom navigation: 5 tabs (Desk, Search, Draft, Deadlines, Files)
- Sidebar: slide-in drawer on hamburger tap, dark overlay behind
- Toast notifications: appear above bottom nav
- All tap targets: minimum 44x44px
- No horizontal scroll anywhere

Breakpoints:
- Mobile: max-width 768px → bottom nav visible, sidebar hidden
- Tablet: 769px–1023px → sidebar available via hamburger
- Desktop: 1024px+ → fixed sidebar always visible
```

### Component Patterns

```
Sidebar:
- Background: --navy-dark (#111E30)
- Active nav item: rgba(201,168,76,0.15) bg + gold left border
- Logo icon: gold gradient, navy text

Search hero (home + search screen):
- Background: linear-gradient(135deg, --navy, --navy-light)
- Radial gold glow top-right
- Search input: rgba white on dark bg

Citation badges (always monospace font):
- Verified ✓:    green bg (#E8F5EE), green text (#1A6B3C)
- Unverified ⚠:  amber bg (#FFF8E1), amber text (#B8860B)
- Fabricated ✗:  red bg (#FDECEA), red text (#8B1A1A)

Cards:
- Background: white (#FFFFFF)
- Border: 1px solid --border (#DDE3EC)
- Border-radius: 12px
- Hover: box-shadow 0 4px 16px rgba(27,46,75,0.1)

Buttons:
- Primary: --gold background, white text, font-weight 600
- Secondary: white bg, --border border, --text-mid color
- Border-radius: 8px (not pill — too casual for lawyers)

Stat cards:
- Coloured top border (3px): navy/gold/green/amber per card type
- White background, subtle hover shadow
```

### Home Screen — Search First

```
The home screen hero is a BIG search bar — not a dashboard.
Layout top to bottom:
1. Small greeting + date (top)
2. Urgent deadline strip (red, only shown when urgent)
3. HERO: Dark search box (navy bg) — full width on mobile
   - Source toggles below (Your files / Public judgments / Legal procedures)
   - Suggested search chips
4. Recent searches (last 3, one-tap re-run)
5. Continue your work (last 3 drafts)

No stats cards. No quick action grid. No time-saved widget.
These were removed — search is the primary action.
```

### Dashboard Look and Feel

```
IMPORTANT: Dashboard layout WILL change in future.
Do not over-invest in dashboard screen.
Focus React build on:
1. Search screen (most used daily)
2. Draft screen (highest value)
3. Document library
4. Deadline tracker

Dashboard is placeholder — will be redesigned with
real usage data from pilot lawyers.
```

### React UI Status

```
React frontend: NOT STARTED YET

When starting React build:
1. Read ui-prototypes/nikhar-demo.html for exact colors
2. Use Sora + DM Serif Display + JetBrains Mono fonts
3. Use navy/gold color palette from nikhar-demo.html
4. Build mobile-first — test at 375px width first
5. Then expand to 1366px desktop layout
6. Use shadcn/ui as component library base
7. TailwindCSS for styling
8. Every screen must work on both mobile and desktop
```

---

## KEY TECHNICAL DECISIONS

Citation sources — government only (100% legal):
- eSCR: main.sci.gov.in — public domain SC judgments
- P&H HC: highcourtchd.gov.in — public domain HC judgments
- Legal basis: Section 52(1)(q) Copyright Act 1957
- Never scrape Indian Kanoon, SCC Online, Manupatra, LawHerald

Infrastructure:
- Backend: Python 3.11, FastAPI async, SQLAlchemy 2.0, Alembic
- AI: GPT-4o (filing drafts only), GPT-4o-mini (everything else)
- Embeddings: text-embedding-ada-002
- Search: Azure AI Search (hybrid) — pgvector fallback for local dev
- Storage: Azure Blob Storage
- Jobs: Celery + Redis Phase 1
- Auth: Simple JWT Phase 1
- Deployment: Azure App Service B2
- Payments: Razorpay
- Email: SendGrid
- WhatsApp: Meta WhatsApp Business API

Database schemas: law (all product tables) + shared (audit logs)
Security: JWT → RBAC → Resource guards → PostgreSQL RLS (4 layers)
firm_id always from JWT — never from request body
Wrong firm_id returns 404 not 403

---

## PHASE 1 FEATURES (ALL BUILT)

1. Document Library — upload, OCR, background indexing
2. Public Judgment Search — eSCR + P&H HC, 10,000+ judgments
3. Own Files Search (RAG) — semantic search over lawyer's documents
4. Unified Search — both sources simultaneously, outcome filters
5. PDF Extractor — structured fields with per-field confidence scores
6. Case Synopsis Generator — one-pager export as .docx
7. Smart Reply Generator — admit/deny per allegation, verified citations
8. Strategic Filing Drafter — objective-based, quality score, citation verification
9. Deadline Tracker — WhatsApp to client in Hindi, condonation draft
10. Legal Process Guide — curated knowledge base, Punjab/Haryana courts

---

## IMMEDIATE NEXT STEPS

1. Fix unified search — add PostgreSQL full-text search fallback
2. Fix document upload — document_service must return document object
3. Seed citations DB with landmark cases for testing
4. Test case synopsis with one real P&H HC judgment PDF
5. Validate AI output quality with one lawyer
6. Then start React frontend using nikhar-demo.html as color reference

---

## HOW TO USE THIS FILE

At the start of every new Claude chat session:
1. Paste the contents of this file
2. Say: "This is the Nikhar product context"
3. Optionally paste CLAUDE.md for full technical spec
4. Then ask your question

For Claude Code (VS Code extension):
CLAUDE.md is read automatically — no need to paste anything
Just open VS Code and start building
Reference ui-prototypes/nikhar-demo.html for colors when building UI
