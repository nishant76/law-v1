# Drafting Correctness Audit & Source Map

**Goal:** every filing the Strategic Filing Drafter produces must be **structurally and
statutorily correct by construction**, and must *flag what it does not know* rather than be
silently wrong. This document maps EVERY draft type our target user files → the data each one
needs to be correct → the **verified government source** for that data. Nothing here is
extracted yet: this is the plan that drives extraction.

- **Scope:** Punjab, Haryana, Chandigarh — district courts + P&H High Court + the tribunals/
  special forums a solo/small-firm practitioner touches.
- **Regime:** BNSS/BNS/BSA for offences on/after 01-Jul-2024; CrPC/IPC/Evidence for older
  offences under the savings clause. Both regimes must be handled.
- **Rule:** values (section numbers, fees, limitation, quantities) are NOT hard-coded from
  memory in this doc — each is pointed at its source and verified at extraction time. Only
  framework facts already verified (cited inline) are stated.

Last updated: 2026-08-14.

**Build status:** extraction plan step 1 (§5) is **DONE** — see `data/special_acts/`
(source **S18**), read by `backend/services/special_acts_service.py` and injected into
`filing_service.generate_template`. The one carve-out is the NDPS *quantity* table, which
stays unbuilt on purpose: its only published copy is a scan whose OCR corrupts values, so
the drafter is made to flag the classification rather than guess a threshold. Steps 2–6
remain unbuilt.

---

## 1. The 8 correctness dimensions

Every draft must get all eight right. The build produces verified data for each.

| # | Dimension | Failure if wrong |
|---|---|---|
| 1 | **Forum / court** — subject-matter, pecuniary, territorial jurisdiction | Filed in the wrong court → returned/rejected |
| 2 | **Governing provision & section numbers** (BNSS/CPC/special act) | Cites repealed/wrong section → draft discredited |
| 3 | **Statutory bars & mandatory pleadings** (NDPS §37, PMLA §45, §12A mediation, notice u/s 80 CPC, §69 Partnership, pre-suit notice, sanction) | Application legally barred / not maintainable |
| 4 | **Court fees & valuation** (ad valorem/fixed; state-specific) | Under-stamped → objected; over-paid → client loss |
| 5 | **Limitation period** | Time-barred filing / missed condonation plea |
| 6 | **Format & mandatory parts** (heading, cause title, index, memo, verification, affidavit, court-fee endorsement) | Registry objection |
| 7 | **Verified citations** | Fabricated citation → total loss of trust |
| 8 | **Facts / strategy** (lawyer-supplied) | Human responsibility — drafter must surface gaps |

**Coverage legend used below:** ✅ verified data exists · ⚠️ partial / hand-mapped · ❌ model-memory only (must build).

---

## 2. Master Source Registry (verified government/official sources)

Referenced by ID (S1…S17) in the taxonomy tables. All are government or official-court sources
(public-domain statute text — safe to self-host per Copyright Act §52(1)(q)).

| ID | Source | URL | Provides | Status |
|----|--------|-----|----------|--------|
| **S1** | India Code — central bare acts + state amendments (handle-based) | https://www.indiacode.nic.in | Dimensions 2, 3, 5, 6 for all central acts | anchor |
| **S2** | P&H High Court **Rules & Orders**, Vols I–V | https://highcourtchd.gov.in/?mod=high_court_rules | Dimensions 1, 6 (procedure, format, court business); some fees (Vol I) | anchor ✅ resolves |
| **S3** | P&H HC case-type nomenclature + e-filing/practice rules | https://highcourtchd.gov.in | Dimension 1 (case-type codes), filing format | anchor |
| **S4** | **NDPS quantity notification** S.O. 1055(E) 19-10-2001 (+ 18-11-2009 mixture clarification) | https://www.cbn.gov.in/pdf/qtynotif.pdf | Dimension 3 — small/commercial thresholds, 239 substances | ✅ resolves |
| **S5** | Court Fees Act 1870 + **Court Fees (Punjab 2nd Amdt) Act 2009** + **Court Fees (Haryana Amdt) Act 2009** | https://www.indiacode.nic.in/handle/123456789/2293 ; state amdts on S1; fee chapters in S2 Vol I | Dimension 4 | ✅ resolves |
| **S6** | Limitation Act 1963 (the Schedule, Arts 1–137) | https://www.indiacode.nic.in (Act 36 of 1963) | Dimension 5 | anchor |
| **S7** | Suits Valuation Act 1887 + Punjab/Haryana valuation rules | S1 + S2 | Dimension 4 (valuation for jurisdiction) | anchor |
| **S8** | Consumer Protection Act 2019 + Rules 2020 | https://www.indiacode.nic.in (Act 35 of 2019) ; https://ncdrc.nic.in | Dimension 1 (pecuniary tiers), 6 (form) | anchor |
| **S9** | Commercial Courts Act 2015 (esp. **§12A** pre-institution mediation, pecuniary ≥ specified value) | https://www.indiacode.nic.in (Act 4 of 2016) | Dimensions 1, 3 | anchor |
| **S10** | Registration Act 1908 + Indian Stamp Act 1899 + Punjab/Haryana stamp schedules | S1 ; https://igrpunjab.gov.in ; https://jamabandi.nic.in (Haryana) | Dimension 4/6 for **deeds** (stamp duty, registration) | anchor |
| **S11** | Motor Vehicles Act 1988 (**§166** MACT claim) + Central MV Rules | https://www.indiacode.nic.in (Act 59 of 1988) | Dimensions 1, 2 (MACT) | anchor |
| **S12** | East Punjab Urban Rent Restriction Act 1949 ; Haryana Urban (Control of Rent & Eviction) Act 1973 | S1 / state legislative sites | Dimension 1, 2 (rent/eviction) | anchor |
| **S13** | RDB Act 1993 + SARFAESI Act 2002 (**§17** DRT) ; IBC 2016 (NCLT) | https://www.indiacode.nic.in | Dimension 1, 2 (debt/insolvency) | anchor |
| **S14** | Arbitration & Conciliation Act 1996 (**§9/11/34/37**) | https://www.indiacode.nic.in (Act 26 of 1996) | Dimension 1, 2 (arbitration) | anchor |
| **S15** | Special-act **bail bars**: NDPS §37, PMLA §45, UAPA §43D(5) | https://www.indiacode.nic.in (respective acts) | Dimension 3 (the highest-risk landmines) | anchor |
| **S16** | **Existing verified data** — BNSS First Schedule offence→court | `data/jurisdiction/bnss_first_schedule.json` | Dimensions 1, 2 for BNS offences | ✅ built |
| **S17** | Format precedents — DU LL.B. drafting reader + P&H HC filed samples | `data/draft_examples/` | Dimension 6 (structure) | ✅ built |
| **S18** | **Existing verified data** — special-act bars, verbatim from India Code bare acts (NDPS 37/36A/2(viia)/2(xxiiia), PMLA 45, UAPA 43D, NI 138/142, CCA 12A, CPC 80, Partnership 69, HMA 14) | `data/special_acts/special_acts.json` | Dimension 3 for the landmines in §4 | ✅ built 2026-08-14 |

> **Note on India Code (S1):** each act has a stable `handle/123456789/<id>` page and per-section
> PDFs; the extraction phase records the exact handle per act (BNSS = 20340/20099, BNS = 20062,
> Court Fees = 2293 already known). No commercial commentary (Ratanlal/Mulla/Sarkar) is used —
> jurisdiction, limitation, fees, bars and official formats are all in these primary sources.

---

## 3. Draft-type taxonomy — required data per type

Columns: **Forum** (dim 1) · **Governing provision** (dim 2) · **Statutory bar / mandatory pleading** (dim 3, the danger column) · **Fee** (dim 4) · **Limitation** (dim 5) · **Format** (dim 6). Cells cite Source Registry IDs; ❌/⚠️/✅ = current coverage.

### 3A. Criminal (incl. special acts) — *highest risk*

| Draft type | Forum | Governing provision | Statutory bar / mandatory pleading | Fee | Limitation | Format |
|---|---|---|---|---|---|---|
| Regular bail | Sessions/Magistrate/HC per offence tier ✅S16 | BNSS §483 (CrPC 439) ⚠️S1 | none (ordinary) | fixed S5 | none | ✅S17 |
| Anticipatory bail | Sessions→HC ✅S16 | BNSS §482 (CrPC 438) ⚠️S1 | **carve-outs**: §482 excludes certain BNS offences (verify list S1) | fixed S5 | none | ✅S17 |
| Default / statutory bail | court of remand | BNSS §187(3) (CrPC 167(2)) ⚠️S1 | indefeasible right if charge-sheet window lapsed; **§37 bar does NOT apply** ✅S4/S15 | fixed | window-driven S1 | ⚠️S17 |
| **NDPS bail** | **Special Court u/ NDPS §36/36A** ❌S1 | BNSS §483 **r/w NDPS §37** ❌S15 | **§37 twin conditions** apply to **commercial** quantity only; classify small/intermediate/commercial from **S4**; proviso exempts women/<16/sick ✅ | fixed S5 | none | ❌ (need NDPS template) |
| **PMLA bail** | Special Court (PMLA §43) ❌S1 | CrPC 439 **r/w PMLA §45** ❌S15 | **§45 twin conditions** (like §37) ❌ | fixed | none | ❌ |
| UAPA bail | NIA/Special Court ❌ | **§43D(5) UAPA** bar ❌S15 | court cannot grant if accusation prima facie true ❌ | fixed | none | ❌ |
| FIR quashing | HC ✅ | BNSS §528 (CrPC 482) / Art 226-227 ⚠️S1 | none | HC fee S5 | none | ✅S17 |
| Private complaint | Magistrate ✅S16 | BNSS §223 (CrPC 200) ⚠️S1 | pre-cognizance examination; sanction where needed | fixed | offence-limitation BNSS §514 (CrPC 468) ❌S1 | ✅S17 |
| §138 NI complaint | JMFC where cheque presented ✅ | **NI Act §138–142** ❌S1 | **§138 provisos** (notice 30d, 15d default), **§142 limitation 1 month** ❌ | fixed | §142 ❌S1 | ✅S17 |
| Direction to register FIR | Magistrate | BNSS §175(3) (CrPC 156(3)) ⚠️S1 | prior §173(4)/(1) approach to police; affidavit | fixed | none | ⚠️S17 |
| Criminal revision | Sessions/HC | BNSS §438 (CrPC 397) ⚠️S1 | bar on revision vs interlocutory orders | fixed | 90 days S6 | ⚠️S17 |
| Criminal appeal (conviction/acquittal) | Sessions/HC per §ladder | BNSS Ch. XXXII ❌S1 | leave to appeal (acquittal); limitation | fixed | S6 | ⚠️S17 |
| Discharge | trial court | BNSS §262/250 (CrPC 239/227) ⚠️S16 | stage-specific | fixed | none | ❌ |

### 3B. Civil suits + applications

| Draft type | Forum | Governing provision | Statutory bar / mandatory pleading | Fee | Limitation | Format |
|---|---|---|---|---|---|---|
| Plaint — recovery/money | Civil Judge by pecuniary S7; **Commercial Court** if "commercial dispute" ≥ specified value S9 | CPC O.VII; O.XXXVII (summary) ❌S1 | **§12A CCA pre-institution mediation** (commercial) ❌S9; §80 CPC notice (govt) ❌ | **ad valorem S5** | Limitation Art (3yr contract) S6 | ✅S17 |
| Plaint — declaration | Civil Judge S7 | CPC; Specific Relief Act §34 ❌S1 | consequential relief rule §34 proviso | ad valorem S5 | S6 | ✅S17 |
| Plaint — permanent injunction | Civil Judge S7 | Specific Relief §38-41 ❌S1 | §41 bars | fixed/ad valorem S5 | S6 | ✅S17 |
| Suit — specific performance | Civil Judge S7 | Specific Relief §10-25 (2018 amdt) ❌S1 | readiness-&-willingness pleading mandatory | ad valorem S5 | Art 54 S6 | ✅S17 |
| Suit — possession/ejectment | Civil Judge S7 | CPC; TP Act; Specific Relief §5-6 ❌S1 | §6 SRA 6-month bar | ad valorem S5 | S6 | ✅S17 |
| Suit — partition | Civil Judge S7 | CPC; partition law ❌ | valuation rules S7 | court fee S5 | S6 | ✅S17 |
| Written statement / counter-claim | same court | CPC O.VIII ❌S1 | 30/90-day filing limit; specific denial rule | — | O.VIII R.6A | ✅S17 |
| Temporary injunction app | same court | CPC **O.XXXIX R.1-2**, §151 ❌S1 | three-fold test pleading | fixed S5 | — | ✅S17 |
| Rejection of plaint | same court | CPC **O.VII R.11** ❌S1 | grounds enumerated | fixed | — | ⚠️ |
| Set aside ex-parte / restoration | same court | CPC **O.IX R.13 / R.9** ❌S1 | sufficient-cause + limitation | fixed | 30 days S6 | ⚠️ |
| Amendment of pleadings | same court | CPC **O.VI R.17** ❌S1 | post-trial proviso | fixed | — | ⚠️ |
| Add/implead party | same court | CPC **O.I R.10** ❌S1 | — | fixed | — | ⚠️ |
| Execution petition | executing court | CPC **O.XXI** ❌S1 | 12-yr limitation Art 136 | ad valorem S5 | Art 136 S6 | ✅S17 |
| First appeal / second appeal | District/HC | CPC **§96 / §100** ❌S1 | §100 substantial question of law | ad valorem S5 | 30/90d S6 | ⚠️ |
| Civil revision | HC | CPC **§115** ❌S1 | jurisdictional-error limit | fixed | 90d S6 | ⚠️ |
| Review | same court | CPC **O.XLVII** ❌S1 | grounds limited | fixed | 30d S6 | ⚠️ |
| Caveat | any court | CPC **§148A** ❌S1 | 90-day life | fixed | — | ✅S17 |
| Transfer petition | District J/HC | CPC **§24 / §25** ❌S1 | — | fixed | — | ✅S17 |
| Writ petition | HC | **Art 226/227** ⚠️S1 | alternative-remedy, laches | HC fee S5 | reasonable S6 | ✅S17 |

### 3C. Family & maintenance

| Draft type | Forum | Governing provision | Statutory bar / mandatory pleading | Fee | Limitation | Format |
|---|---|---|---|---|---|---|
| Divorce (fault) | Family Court ⚠️ | **HMA §13** ❌S1 | 1-yr bar §14; territorial §19 | fixed S5 | none | ✅S17 |
| Divorce (mutual) | Family Court | **HMA §13B** ❌S1 | 6-18 month cooling (waivable) | fixed | none | ✅S17 |
| Judicial separation / RCR / nullity | Family Court | **HMA §10 / §9 / §11-12** ❌S1 | grounds; §19 territorial | fixed | none | ✅S17 |
| Maintenance | Magistrate (BNSS §144) / Family Court (HMA/HAMA) ⚠️ | **BNSS §144** (CrPC 125) / **HMA §24-25** / **HAMA §18** / **DV §20** ⚠️S1 | overlapping-relief disclosure | fixed | none | ⚠️S17 |
| Custody / guardianship | Family/District Court | **Guardians & Wards Act 1890 §7-25**; **HMGA 1956** ❌S1 | welfare-of-child paramount | fixed | none | ❌ |
| DV Act application | Magistrate | **PWDVA 2005 §12** (reliefs §18-23) ❌S1 | DIR; shared-household pleading | nil/fixed | none | ✅S17 |
| Succession certificate / probate / LoA | District Court | **Indian Succession Act §372 / §276 / §278** ❌S1 | ad valorem on assets | **ad valorem S5** (high) | S6 | ✅S17 |

### 3D. Consumer + tribunals

| Draft type | Forum | Governing provision | Statutory bar / mandatory pleading | Fee | Limitation | Format |
|---|---|---|---|---|---|---|
| Consumer complaint | District ≤ / State / National by **CPA 2019 pecuniary tiers** ❌S8 | **CPA 2019 §35/47/58** ❌S8 | 2-yr limitation §69; territorial §34 | slab fee S8 | 2 yr S8 | ✅S17 |
| MACT claim | Motor Accident Claims Tribunal | **MV Act §166** ❌S11 | no limitation (post-2019 §166(3) reintroduced 6-mo — verify S11) | nil/nominal S11 | verify S11 | ❌ |
| Rent / eviction petition | Rent Controller | **E.P. Urban Rent Act 1949 (Pb/Chd)** / **Haryana Rent Act 1973** ❌S12 | grounds enumerated; state-specific | fixed S12 | none | ❌ |
| SARFAESI / DRT | DRT | **SARFAESI §17** / RDB Act ❌S13 | 45-day limit from measure; fee slab | slab S13 | 45d S13 | ❌ |
| Arbitration petition | Commercial/District/HC | **A&C Act §9/§11/§34/§37** ❌S14 | §34 3-month+30d limit; §11 appointment | fixed/ad valorem | §34 S14 | ❌ |
| RERA complaint | RERA Authority | RERA 2016 + Pb/Hr rules ❌ | — | slab | — | ❌ |

### 3E. Conveyancing / deeds (stamp + registration critical)

| Deed | Governing law | Stamp duty (dim 4) | Registration | Format |
|---|---|---|---|---|
| Sale / gift / mortgage / lease / relinquishment / partition deed, POA, will, partnership deed | TP Act 1882; Indian Stamp Act; Registration Act 1908 ❌S10 | **Punjab/Haryana stamp schedules S10** (ad valorem on consideration/market value) | mandatory for most (Reg. Act §17) | ✅S17 |

---

## 4. Highest-risk landmine table (build these first — a wrong answer here voids the filing)

Coverage below is as at 2026-08-14. Rules marked ✅ are held as **verbatim statutory text**
in S18 and injected into the drafting prompt — the wording the model sees is the bare act's
own, not a paraphrase in this table.

| Landmine | Applies to | Rule | Source | Coverage |
|---|---|---|---|---|
| **NDPS §37 twin conditions** | NDPS bail — §19/§24/§27A and **commercial** quantity | PP heard + court satisfied (a) reasonable grounds accused not guilty AND (b) not likely to offend on bail; §37(2) these are *in addition* to ordinary bail limits | S18 (verbatim §37) | ✅ built |
| **NDPS Special Court** | all NDPS offences > 3 yrs | triable only by the Special Court under §36A | S18 (verbatim §36A) | ✅ built |
| **PMLA §45 twin conditions** | PMLA bail | mirror of §37, with the §45 proviso carve-outs | S18 (verbatim §45) | ✅ built |
| **UAPA §43D(5)** | UAPA bail | no bail if accusation prima facie true; §43D(2) modifies remand clock | S18 (verbatim §43D) | ✅ built |
| **§12A Commercial Courts Act** | commercial suits not seeking urgent relief | mandatory pre-institution mediation or suit barred | S18 (verbatim §12A) | ✅ built |
| **§80 CPC notice** | suits vs government / public officer | prior notice unless §80(2) leave | S18 (verbatim §80) | ✅ built |
| **§69 Partnership Act** | suits by/on behalf of unregistered firm | suit barred; exceptions in the section | S18 (verbatim §69) | ✅ built |
| **§14 HMA one-year bar** | divorce within 1 yr of marriage | leave required on the grounds §14 states | S18 (verbatim §14) | ✅ built |
| **§138 provisos + §142 limitation** | §138 complaints | each proviso pleaded with dates; complaint by payee/holder within the §142 period | S18 (verbatim §138, §142) | ✅ built |
| **NDPS quantity classification** | all NDPS drafts | determines whether §37 applies, the punishment, and the forum | **S4** (S.O. 1055(E)) | ❌ **deliberately not built** — the only published copy is a scan whose OCR corrupts values (heroin's small-quantity column is lost). No threshold is stored or guessed; the drafter is instead required to obtain the quantity from the lawyer, state no figure the statute does not contain, and flag the classification for verification. See `data/special_acts/README.md`. |
| **Anticipatory bail carve-outs (BNSS §482)** | AB for certain offences | §482 excludes specified BNS offences | S1 | ⚠️ verify |

---

## 5. Extraction plan (build phase — after this audit is approved)

Order chosen to kill the most/worst errors first, all four families in scope.

1. **Special-act bail + landmines (S4, S15, S9, S1):** NDPS §37 + quantity table (S.O.1055(E)), PMLA §45, UAPA §43D(5), the §12A/§80/§69/§14/§142 bar checks → a `special_acts` data module the drafter reads like it now reads `bnss_first_schedule.json`. *(Directly fixes the NDPS class of bug.)*
2. **BNSS procedural section map (S1):** verified CrPC→BNSS table for bail/anticipatory/default/revision/quashing/complaint/maintenance (extract from the BNSS bare act, not the current hand-map). Replaces the prompt's inline procedural numbers.
3. **Forum map for special courts & tribunals (S1, S8, S11–S14, S3):** NDPS/PMLA Special Courts, Family Court, Commercial Court pecuniary threshold, Consumer tiers, MACT, Rent Controller, DRT, RERA, arbitration seat/court.
4. **Court fees + limitation tables (S5, S6, S7):** ad valorem/fixed per draft type, Punjab vs Haryana vs Chandigarh; Limitation Act Schedule articles keyed to draft type.
5. **Format authority upgrade (S2):** ingest relevant P&H HC Rules & Orders chapters (Vol I civil, Vol III criminal, fee chapters) to replace Delhi-oriented DU precedents where a Punjab format differs.
6. **Deeds (S10):** Punjab/Haryana stamp + registration for conveyancing.

Each module ships with a manifest (source URL + retrieval date + verified/TODO counts), same pattern as `bnss_first_schedule.json`. The drafter wires to each via a grounding block; unknowns are flagged, never guessed.

---

## 6. Honest limits

Verified data eliminates the **systematic** error classes (dims 1–6). Fact-specific strategy and
novel edge cases (dim 8) still require the lawyer — the drafter's job there is to **surface the
gap** (as the NDPS draft's strategy-notes did for quantity), never to invent. "Zero systematic
defects + explicit flags for the rest" is the achievable bar.
