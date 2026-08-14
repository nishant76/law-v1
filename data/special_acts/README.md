# Verified special-act statutory bars & mandatory pleadings

`special_acts.json` holds the **verbatim text** of the provisions that decide whether
a filing is maintainable at all — the "landmine" table in
[`docs/drafting_correctness_audit.md`](../../docs/drafting_correctness_audit.md) §4.

It exists because those provisions previously lived only in the model's memory. A real
NDPS bail draft was caught omitting s.37, the quantity classification, **and** the
Special Court — the exact class of error the launch-quality mandate forbids.

This is step 1 of the audit's extraction plan (§5), and the companion to
[`data/jurisdiction/`](../jurisdiction/README.md): that answers *which court tries this
BNS offence*, this answers *what bar or mandatory pleading must the draft clear*.

## Coverage

| Act | Provisions | What it gates |
|---|---|---|
| NDPS 1985 (61 of 1985) | s.37, s.36A, s.2(viia), s.2(xxiiia) | Bail twin conditions; Special Court; small/commercial quantity definitions |
| PMLA 2002 (15 of 2003) | s.45 | Bail twin conditions |
| UAPA 1967 (37 of 1967) | s.43D | Bail bar (43D(5)); modified remand periods |
| NI Act 1881 (26 of 1881) | s.138, s.142 | Cheque-bounce provisos; complaint limitation |
| Commercial Courts Act 2015 (4 of 2016) | s.12A | Pre-institution mediation |
| CPC 1908 (5 of 1908) | s.80 | Notice before suing Government / public officer |
| Indian Partnership Act 1932 (9 of 1932) | s.69 | Suit by unregistered firm barred |
| Hindu Marriage Act 1955 (25 of 1955) | s.14 | One-year bar on divorce petitions |

**12 provisions, 12 verified.**

## Source

All text is from the **official India Code bare-act PDFs** (`indiacode.nic.in`) —
public-domain statute text, safe to self-host under Copyright Act s.52(1)(q). No
commercial commentary is used. Each record carries its own `source_url`,
`source_handle`, and `retrieved_date`; PDFs are cached in [`source/`](source/).

## How it was built (re-runnable, deterministic)

```bash
python3 scripts/extract_special_acts.py data/special_acts/special_acts.json
```

`scripts/extract_special_acts.py` downloads each act, reads the PDF's own text layer via
pdfplumber, and slices each provision between two **literal** markers (the section
heading, and the heading of the next section). Amendment footnotes (`1. Subs. by Act 9
of 2001…`) and bare page numbers are stripped — they interleave with statutory text in
these PDFs and are not part of the provision.

If a marker is not found, the record is written with `verified: false` and **empty
text**. `special_acts_service` skips unverified rows, so an extraction failure degrades
to silence rather than to a guess.

## ⚠️ Known gap — NDPS quantity thresholds are NOT here

The small/commercial quantity table is fixed by **S.O. 1055(E) dated 19-10-2001**. The
only published copy (<https://www.cbn.gov.in/pdf/qtynotif.pdf>) is a **poor scan**:
OCR of it drops and corrupts values — heroin's small-quantity column is lost entirely,
and substance names come out mangled. Extracting it would produce wrong thresholds, and
the quantity is the single highest-consequence number in NDPS drafting (it decides
whether the s.37 bar applies at all, the punishment, and the forum).

So **no threshold is stored and none is guessed.** Instead
`special_acts_service.grounding_block()` instructs the drafter to:

- obtain the seized quantity from the lawyer and classify it expressly,
- state **no** threshold figure the quoted statutory text does not contain,
- put the quantity in `missing_facts` when the brief omits it, and
- add a `strategy_notes` line that the classification must be verified against
  S.O. 1055(E) before filing.

Replace this with a real extraction once a text-layer or machine-readable gazette copy
is obtained. Until then the behaviour is *explicitly flagged unknown*, which is the
launch-quality bar — never a plausible-looking fake.

## Read path

[`backend/services/special_acts_service.py`](../../backend/services/special_acts_service.py)
— `detect_triggers()` matches the brief's subject-matter (and, where a bar only bites for
a particular relief, the relief too), `grounding_block()` emits the verbatim text plus a
"THE DRAFT MUST" checklist. `filing_service.generate_template()` appends it to the prompt
next to the jurisdiction grounding. Returns `""` when no bar is engaged, so ordinary
filings are not padded with irrelevant statute.

## Still model-memory (next extraction passes)

Per the audit's §5 order, these remain unbuilt: the verified CrPC→BNSS procedural section
map (step 2), special-court/tribunal forum map (step 3), **court fees and limitation**
tables (step 4), P&H HC Rules & Orders format authority (step 5), and stamp/registration
for deeds (step 6).
