# Tasks

## Active

### Drafting page (frontends/law-v2/src/routes/app.drafting.tsx)
- [ ] After a draft is generated, move the brief description into a modal/popup — show a "Brief description" line with an Edit button at the top that opens the popup on click.
- [ ] Fix generated draft title (e.g. "Application under section...") rendering shrunk/wrapped to the left — layout/CSS bug in the result header.
- [ ] Key Details panel: reduce/consolidate unnecessary fields (ties into the existing key_fields over-granularity TODO in filing_drafter.py ~line 294).
- [ ] Brief-strength clarifying questions: drop questions for details that are already captured via Key Details fields (e.g. FIR number) so we don't ask twice.
- [ ] Existing-draft upload should also accept handwritten/scanned case notes (not just typed drafts) to generate a draft from — route these through the same clarifying-questions review step before generation.
- [ ] Add a citation search popup so the user can find and attach matching citations, either after the draft is generated or optionally before.
- [ ] Generated draft should open in a text/word-style editor with basic formatting controls, editable in place. Selecting text should surface an "AI Edit" action opening a small popup textarea — user types an instruction, the selected section is sent to the LLM and replaced with the edited result.

### Legal Q&A Search
- [ ] **User Story:** As a lawyer, I want to ask any legal question in a search bar and get answers sourced only from government sources, so that I can trust the answer is accurate and verifiable without cross-checking it myself.

### Cases
- [ ] **User Story:** As a lawyer with cases imported from eCourts, I want to edit the WhatsApp number attached to a case, so that case update notifications go to the correct number (e.g. when the client's number was wrong at import time or has changed).

### eCourts Connect
- [ ] Increase the overall size of the search textbox, and the text/search results shown in the eCourts connect flow (EcourtsQuickImport.tsx) — currently too small to read comfortably.

### WhatsApp Automation
- [ ] **User Story:** As a lawyer, I want SuperAdvocate to automatically send WhatsApp fee reminders and hearing reminders to both myself and my clients, so that neither of us misses a payment or a court date without me having to track and send these manually.

## Waiting On

## Someday

## Done
- [x] Drafting page: Layout — moved the brief/description prompt to the center of the page instead of the left pane (Step 1 only; two-pane layout still used once a draft exists).
- [x] Drafting page: Removed the Court text box from Step 1 (court is inferred).
