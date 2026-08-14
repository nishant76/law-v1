# Making Drafting Unbeatable — Audit + Build Plan

**Status: PROPOSAL — for review. Nothing in this document has been built.**
Date: 2026-07-22. Scope: Feature 8 (Strategic Filing Drafter).
Companion doc: [`drafting_correctness_audit.md`](drafting_correctness_audit.md) (the source/taxonomy map, still valid — this document supersedes its §5 build plan).

---

## 0. The verdict in one paragraph

The drafter today produces **a good-looking draft that no one has checked**. Structure and
jurisdiction grounding are genuinely ahead of the market (verified BNSS First Schedule, real
P&H HC precedents). But between the model's JSON and the lawyer's screen there is **zero
verification** — no check that the mandatory sections are present, that a cited section number
exists, that a citation is real, or that the export is even e-filable. The quality-gate code
(`draft_quality_service`) exists but is wired to the **dead** `/filing/generate` endpoint, not
the live `/filing/template` one. Meanwhile every draft ships with **zero case law** because the
citation picker was removed from the UI and nothing replaced it. "Unbeatable" is not another
prompt revision: it is (a) finish the verified-data plane, (b) add a validate-and-repair layer
that makes wrongness *structurally impossible to ship*, (c) put verified citations back into
the grounds, and (d) build an eval harness so we can prove it. Items (b) and (d) are what no
Indian competitor has.

---

## 1. What is genuinely strong already

Worth protecting — do not regress these in the rebuild.

| Asset | Why it matters |
|---|---|
| `data/jurisdiction/bnss_first_schedule.json` — 462 rows, 461 verified, coordinate-parsed from the official Schedule | Real verified-data plane. Correctly removed the hand-curated table that had murder as BNS 101 instead of 103. Nobody else in this market grounds forum selection on parsed statute. |
| `jurisdiction_service.grounding_block()` injecting authoritative rows that **override model memory** | The right architectural pattern. Everything else should copy it. |
| `filing_examples.py` — real filed P&H HC documents as FORMAT REFERENCE | Actual filed docs beat any textbook. The 6 P&H samples are the crown jewels. |
| Free-text input + `detected_document_type` editable chip | Correct call. Removing the dropdown killed the stale-default footgun; the chip keeps a correction path. |
| Forum-conditional format rules (5 fora) + template/live-fill UX | The live-fill two-pane model is a genuinely better interaction than a wall of generated text. |
| Honest gap-flagging culture (the NDPS miss was *caught and written down*, not hidden) | This is the discipline the whole plan depends on. |

---

## 2. Defect register — what is actually wrong, with evidence

Ordered by damage to a lawyer's trust on first contact.

### D1 — No output validation whatsoever (severity: critical)
`filing_service.generate_template()` ([filing_service.py:284-298](backend/services/filing_service.py:284)) does exactly three things with the model's response: parse JSON, reconcile `{{tokens}}` against `key_fields`, return. There is **no** check that:
- the seven mandatory P&H HC sections are present (the prompt *asks*; nothing *verifies*)
- a BNS/BNSS section number appearing in the draft actually exists in `bnss_first_schedule.json`
- the court heading matches the forum the jurisdiction data implies
- the draft contains no fabricated citation
- required blocks (verification clause, affidavit, court-fee endorsement) exist

The prompt ends with "BEFORE YOU OUTPUT — re-check…" ([filing_drafter.py:244](backend/services/prompts/filing_drafter.py:244)). That is a *request to a language model*, not a guarantee. Under the Launch Quality Mandate ("gate it rather than ship it half-working") this is the single largest exposure.

### D2 — The quality gate is connected to the dead path (severity: critical)
`generate_filing()` runs citation verification + `draft_quality_service.calculate_draft_quality_score()` and **blocks** on failure ([filing_service.py:100-130](backend/services/filing_service.py:100)). That is `/filing/generate` — the legacy objective-based flow the UI no longer uses. The live flow (`/filing/template`) bypasses all of it. We built the safety net and then routed traffic around it.

### D3 — Every draft ships with zero case law (severity: critical, competitive)
`generate_template` only receives citations via `selected_citations` ([filing_service.py:223-230](backend/services/filing_service.py:223)). The drafting UI no longer has a citation picker — `grep` over [app.drafting.tsx](frontends/law-v2/src/routes/app.drafting.tsx) finds only a read-only "Citations used" display at line 371. So `citations_text` is, in practice, always `"No citations provided."` and the prompt correctly instructs "add no citations." **Result: our grounds sections contain no authority at all.** Prism, CaseMine AMICUS and Manupatra all lead with retrieval-grounded citations. A grounds section with no case law reads as a student's draft. We already own a verified-citations-only search service — it is simply not wired in.

### D4 — Special acts are model-memory (severity: critical, already known)
NDPS §37 + quantity classification, PMLA §45, UAPA §43D(5), NI §138/§142 provisos, §12A Commercial Courts, §80 CPC, §69 Partnership, §14 HMA. `grounding_block` covers **only** BNS First Schedule offences. An NDPS bail draft was already caught omitting §37, the quantity classification and the Special Court. This is the highest-probability catastrophic error: a bail application that ignores a statutory twin-condition bar is not a weak draft, it is a *dismissed* one.

### D5 — The export cannot actually be filed (severity: high)
- [docx_service.py:66-77](backend/services/docx_service.py:66): Times New Roman **12pt**, margins L1.25″/R1.0″/T1.0″/B1.0″, no line spacing set (= single).
- The prompt and P&H R&O require **Roman 14, double spacing, 1.25″ top/left/right, 0.75″ bottom, one side of page only**.
- P&H HC e-filing rules (R&O Vol. V Ch. 1 Part J) require **OCR-searchable PDF/A**; we emit only `.docx` ([filing.py:257](backend/api/filing.py:257)).

So we instruct the model in formatting rules the exporter then discards, and produce a file that the e-filing portal will not accept. A lawyer discovers this at the registry.

### D6 — Nothing is persisted on the live path (severity: high)
`generate_template` never calls `_store_draft`; `/template/export` takes the markdown in the request body rather than a `draft_id`. Consequences: no draft history, no "my drafts", `/filing/{draft_id}` can't retrieve anything the lawyer actually made, no audit trail, and — most importantly — **no feedback loop**. We cannot learn which drafts got edited, regenerated, or abandoned, which is the data that would compound into a real moat.

### D7 — No regression tests on the drafter (severity: high)
`tests/prompt_regression/` contains `test_case_synopsis.py` and `test_pdf_extractor.py` only. CLAUDE.md states "Changing a prompt = making a PR" and "Prompt regression tests run before every deploy." The drafter — the most complex prompt in the product, at ~275 lines of system prompt — has none. Every prompt edit to date has been unmeasured. We cannot currently answer "is today's drafter better than last month's?"

### D8 — Precedent corpus is thin and geographically wrong (severity: medium-high)
44 DU drafts + 6 P&H samples. The DU reader is **July 2020, pre-BNS/BNSS, Delhi-oriented** — it is used, correctly, for structure only, but it is the *sole* source for every district/family/consumer/NI/deed type. There is **not one Punjab or Haryana district-court precedent** in the corpus. Routing is a 40-line ordered regex ([filing_examples.py:76-136](backend/services/filing_examples.py:76)) returning exactly one example, truncated at 6000 chars. A first-time-unseen draft type falls through to a generic CWP.

### D9 — Single-pass generation with a hard ceiling (severity: medium)
`max_tokens=6000` for a filing that must contain Index + Memo of Parties + List of Dates + 10-12 numbered paragraphs + Prayer + Verification + Affidavit. Long HC petitions will truncate. There is no draft→critique→revise loop, which is the cheapest large quality gain available on a GPT-5.2-class model.

### D10 — Silent input truncation (severity: medium)
`safe_input[:12000]` ([filing_service.py:243](backend/services/filing_service.py:243)). An uploaded 30-page draft to "improve" loses everything past ~5 pages, with no warning. This is the same bug already fixed in Reply-to-Notice (12000→30000).

### D11 — Grounding coverage is a 30-word keyword list (severity: medium)
`_OFFENCE_KEYWORDS` ([jurisdiction_service.py:199-208](backend/services/jurisdiction_service.py:199)) is 33 hand-typed nouns against 462 offence rows. Briefs phrased in other terms ("he was booked for snatching a chain", "misappropriated company funds") may or may not hit. Should be embedding/alias-based over the offence descriptions we already have.

### D12 — The BNSS/CrPC regime switch is left to the model (severity: medium)
`ipc_equivalent` is `null` for all 462 rows (documented TODO). So for an FIR dated before 01-Jul-2024 — still the majority of live matters — we have **no verified mapping at all** and fall back entirely to model memory, the exact failure mode that motivated building the table.

---

## 3. What "unbeatable" has to mean

The market position is already right ("Prism is for Indian lawyers; SuperAdvocate is for YOUR court"). Depth in one geography. Three claims we should be able to defend literally, not rhetorically:

> **1. Every section number, forum, fee, limitation period and statutory bar in the draft came from a parsed government source — not a language model's memory. Click any of them to see the source.**
>
> **2. The draft was checked against a machine-readable rulebook before you saw it. Whatever the checker could not verify is flagged in amber, on the draft, by name.**
>
> **3. It exports in the format the registry accepts.**

Claim 1 is the extraction work. Claim 2 is the validator — **this is the differentiator**, because every competitor is a RAG pipeline that ends at generation. Claim 3 is a day's work that removes a whole class of embarrassment.

Anti-goal, stated explicitly: we are **not** trying to make the model smarter. We are trying to make wrongness structurally unable to reach the lawyer.

---

## 4. Target architecture

Five stages, replacing today's one.

```
Brief (free text)
   │
   ├─▶ 1. CLASSIFY        deterministic + LLM: draft type, forum family, statute family,
   │                      regime (BNSS vs CrPC via offence date), party roles
   │
   ├─▶ 2. GROUND          assemble a VERIFIED FACTS PACK from the data plane:
   │                      · offence→court        (bnss_first_schedule.json)         ✅ built
   │                      · procedural sections  (bnss_sections.json)               ❌ build
   │                      · special-act bars     (special_acts.json)                ❌ build
   │                      · forum/pecuniary map  (forums.json)                      ❌ build
   │                      · court fees           (court_fees_pb_hr_chd.json)        ❌ build
   │                      · limitation           (limitation_articles.json)         ❌ build
   │                      · stamp duty           (stamp_registration_pb_hr.json)    ❌ build
   │                      · format rules         (format_rules.json, from R&O)      ❌ build
   │                      · statutory forms      (cpc_appendices.json, bnss_forms)  ❌ build
   │                      · VERIFIED CITATIONS   (SearchService — self-hosted only) ✅ exists,
   │                                                                                   not wired
   │
   ├─▶ 3. DRAFT           GPT-5.2, prompt = today's prompt MINUS every hard-coded legal
   │                      value, PLUS the facts pack + a real precedent + retrieved citations
   │
   ├─▶ 4. VALIDATE        ── THE NEW LAYER ──
   │                      deterministic rule engine over the generated markdown:
   │                        · every section number cited ∈ verified data     → else FLAG
   │                        · court heading == forum implied by facts pack   → else FLAG
   │                        · mandatory sections for this draft type present → else REPAIR
   │                        · applicable statutory bars pleaded (NDPS §37…)  → else REPAIR
   │                        · limitation stated & satisfied                  → else FLAG
   │                        · court fee / valuation stated                   → else FLAG
   │                        · every citation ∈ verified citations DB         → else STRIP
   │                        · every {{token}} has a key_field, and vice versa → REPAIR (exists)
   │                      REPAIR = one targeted regeneration pass naming the specific defects.
   │                      FLAG   = amber annotation on the draft, never a silent pass.
   │
   └─▶ 5. RENDER          live-fill → .docx **to P&H R&O spec** + OCR-searchable PDF/A
                          + a "Verification Report" panel: what was verified, from which
                          source, retrieved on what date, and what the lawyer must check.
```

The validator is deliberately **deterministic code, not an LLM judge**. An LLM judge inherits the same blind spots as the drafter. A rule engine reading parsed statute does not.

The Verification Report is also the sales demo. "Here is every legal assertion in this draft and the government PDF it came from" is a thing a lawyer can test in the room, and no competitor can answer.

---

## 5. Source acquisition — verified obtainable

I checked availability of each. Findings:

| # | Source | Where | Status | Yields |
|---|---|---|---|---|
| S18 | **BNSS Second Schedule — statutory FORMS** | `upload.indiacode.nic.in/schedulefile?aid=AC_CEN_5_23_00049_202346_1719552320687&**rid=1192**` | ✅ **Same document, same aid, adjacent rid to the First Schedule we already parsed** | ~65 official forms (bail bonds, summons, warrants, recognizances). Statutory format — unarguable. Reuses `extract_bnss_schedule.py` almost verbatim. **Highest ratio of value to effort in this entire plan.** |
| S19 | **CPC First Schedule Appendices A–I** | `indiacode.nic.in/bitstream/123456789/2191/…` (HTTP 200 confirmed) | ✅ | Appendix A = **statutory model pleadings** (plaint, written statement) — App. B process, D decrees, E execution, G appeals, **I Statement of Truth** (mandatory for commercial suits). This replaces the Delhi DU reader as the format authority for every civil draft, with a *statutory* one. |
| S20 | **P&H HC Rules & Orders Vols I–V** | `highcourtchd.gov.in/sub_pages/left_menu/Rules_orders/high_court_rules/vol-{I,III,V}-pdf/…` — predictable per-chapter PDF URLs, confirmed live | ✅ | Vol I (civil/fees), Vol III (instructions to criminal courts), Vol V (judicial business + **Ch.1 Part J = E-Filing Rules**). Punjab-specific format authority — the thing that makes us regional-deep rather than national-generic. |
| S4 | NDPS quantity notification S.O.1055(E) | `cbn.gov.in/pdf/qtynotif.pdf` | ✅ known | 239 substances × small/commercial thresholds → drives §37 applicability |
| S15 | NDPS §37 / PMLA §45 / UAPA §43D(5) | India Code per-act PDFs | ✅ | The landmine table |
| S5 | Court Fees Act + **Punjab 2nd Amdt 2009** + **Haryana Amdt 2009** | India Code + R&O Vol I fee chapters | ✅ | Fees, per state — Punjab ≠ Haryana ≠ Chandigarh |
| S6 | Limitation Act 1963 Schedule (Arts 1–137) | India Code | ✅ | Limitation per draft type |
| S8/S11/S12/S13/S14 | CPA 2019 · MV Act §166 · Rent Acts (Pb 1949 / Hr 1973) · SARFAESI §17 · A&C Act | India Code | ✅ | Tribunal forums + their limitation windows |
| S10 | Punjab/Haryana stamp schedules | igrpunjab.gov.in · jamabandi.nic.in | ⚠️ verify | Deeds (stamp duty is a *client money* error, highly visible) |

Two notes. First, **no commercial commentary is used anywhere** — Myneni, Ratanlal, Mulla, Sarkar are all excluded; everything above is public-domain statute or official court rules, safe to self-host under Copyright Act §52(1)(q), same basis as the judgments corpus. Second, S18 and S19 are the discoveries here: **the highest-authority drafting templates in Indian law are statutory schedules we can parse**, and we were using a 2020 Delhi student reader instead.

**Corpus gap that money, not code, fixes:** there is still no Punjab/Haryana *district court* filed-precedent set. Statutory forms give us correct skeletons; only real filed drafts give us local practice (how a Ludhiana JMFC bail application actually reads). Proposal: acquire 100–200 real anonymised filings from 3–5 friendly practitioners across Ludhiana/Panchkula/Gurugram, in exchange for free lifetime accounts. This is a moat competitors cannot buy their way into quickly, and it doubles as design partnership.

---

## 6. Build plan

Ordered so that the worst errors die first and something is demonstrable at every step.

### Phase 1 — Stop shipping unverified drafts (2 weeks)
*The trust floor. Nothing else matters until this exists.*
1. **Validator skeleton** — `backend/services/draft_validator.py`, deterministic rules over generated markdown, returning `{errors, warnings, verified_claims}`.
2. Wire the first three rules: section-number existence, forum-vs-heading consistency, mandatory-sections-per-type.
3. **REPAIR pass** — one targeted regeneration naming specific defects; FLAG whatever survives.
4. **Verification Report panel** in [app.drafting.tsx](frontends/law-v2/src/routes/app.drafting.tsx) — amber flags inline on the draft, sources listed below.
5. **Persist drafts** on the template path (`_store_draft`), so history + the feedback loop start accumulating from day one.

*Exit test: a draft that names a nonexistent BNS section cannot reach the screen unflagged.*

### Phase 2 — Kill the landmines (2 weeks)
6. `data/special_acts/` — NDPS §37 + S.O.1055(E) quantity table, PMLA §45, UAPA §43D(5), NI §138/§142, §12A CCA, §80 CPC, §69 Partnership, §14 HMA.
7. `special_acts_service.py` with a `grounding_block()` mirroring the jurisdiction service.
8. Validator rules: *if NDPS + commercial quantity → §37 twin conditions MUST be pleaded, else REPAIR.* Same shape for each bar.

*Exit test: the NDPS bail draft that was caught missing §37 now contains it, or refuses to generate.*

### Phase 3 — Statutory format authority (2 weeks)
9. Extract BNSS Second Schedule forms (S18) — reuse the existing extractor.
10. Extract CPC Appendices A–I (S19); demote DU reader to fallback.
11. Extract P&H R&O format rules (S20) → `format_rules.json`, replacing the prompt's inline prose.
12. **Fix the exporter**: Roman 14 / double-spaced / 1.25″-1.25″-1.25″-0.75″, plus OCR-searchable PDF/A output.

*Exit test: an exported petition passes P&H HC e-filing format requirements.*

### Phase 4 — Citations back in the grounds (1.5 weeks)
13. Auto-retrieve verified citations during generation (SearchService, self-hosted-only — never a bare `source_url`).
14. Weave into grounds with pin-cites; validator **strips** any citation absent from the verified DB.
15. Restore an "add/remove citation" control in the live-fill pane.

*Exit test: no draft can contain a citation that is not in our verified DB with a working link.*

### Phase 5 — Fees, limitation, valuation (2 weeks)
16. `court_fees_pb_hr_chd.json` + `limitation_articles.json` + valuation rules, keyed by draft type and state.
17. Validator: limitation computed from the facts; if time-barred → *"prima facie time-barred — a condonation application under §5 Limitation Act appears necessary"* (which hands straight off to the Deadline Tracker's condonation drafter).

*Exit test: a plaint states its court fee basis and its limitation article, both traceable to source.*

### Phase 6 — The eval harness (ongoing, start in Phase 1)
18. `tests/prompt_regression/test_filing_drafter.py` — a **golden set of 40–60 briefs** across every draft type, each with machine-checkable assertions (correct forum, required sections present, required bars pleaded, no invented sections).
19. Run on every prompt change; block on regression. This closes the CLAUDE.md commitment that is currently unmet.
20. Layer a human review pass: 3–5 practising advocates score sampled drafts monthly on a fixed rubric.

*This is the thing that compounds. Competitors ship prompt changes on vibes; we would ship them on a scoreboard.*

**Total: ~10 weeks of focused work.** Phases 1–2 alone (4 weeks) remove every currently-known catastrophic failure mode and are independently shippable.

---

## 7. Sequencing rationale

Phase 1 before Phase 2 because a validator with three rules that *runs* beats ten datasets nothing checks. Phase 3 before Phase 4 because a beautifully-cited draft the registry rejects still fails. Phase 6 starts immediately and never ends — without it, Phases 1–5 are unfalsifiable claims.

---

## 8. Risks and honest limits

| Risk | Mitigation |
|---|---|
| **GPT-5.2 quota** — already hit HTTP 429 during PDF-extractor verification; a REPAIR pass adds a second call per draft | Confirm Azure TPM before Phase 1 ships; make REPAIR conditional on validator findings (most drafts won't need it); GPT54_MINI fallback path already exists |
| **Latency** — GPT-5.2 is 30-70s; classify + draft + repair could reach 2-3 min vs the <30s performance target | Stream the draft as it generates (the PDF extractor already does this); run validation on the completed text and reveal flags after. Revise the stated target — an accurate 90s draft beats a wrong 30s one, but say so honestly in the UI |
| **PDF table extraction is brittle** — R&O and CPC appendices are older scans | Same discipline as `bnss_first_schedule.json`: never fill from memory, mark `verified:false`, and let the validator treat unverified rows as unknown-not-true |
| **Statutory data drifts** (amendments, fee revisions, new notifications) | Every module ships a manifest with source URL + retrieval date; quarterly re-extraction job; surface "verified as of <date>" in the Verification Report |
| **Over-flagging** — a draft covered in amber warnings is as useless as a wrong one | Tune to flag only what a competent advocate would themselves check; measure flag-dismissal rate in the eval harness and treat a high rate as a bug |
| **The unfixable part** | Verified data eliminates *systematic* error (forum, section, fee, limitation, format, bars). Fact-specific strategy and novel edge cases remain the lawyer's. The drafter's duty there is to **surface the gap**, never to invent. "Zero systematic defects + explicit flags for the rest" is the achievable bar, and it is the one we should market. |

---

## 9. What I recommend approving

Minimum to unblock: **Phases 1 + 2** (4 weeks) — the validator, persistence, and the special-act landmines. That converts the known-catastrophic failures into flagged-or-blocked ones and makes the Launch Quality Mandate literally true for drafting.

Strongly recommended alongside: **Phase 6 started immediately**, because otherwise we cannot prove any of it.

Decisions I need from you before building:
1. Approve the phase order, or reprioritise (e.g. pull the exporter fix forward — it is a day's work and highly visible).
2. Approve the P&H district-court precedent acquisition (100–200 anonymised real filings from friendly practitioners for free lifetime accounts) — code cannot substitute for it.
3. Confirm the latency posture: is a ~90s validated draft acceptable in place of the current <30s target?
4. Confirm the Azure GPT-5.2 quota position, since the REPAIR pass depends on it.
