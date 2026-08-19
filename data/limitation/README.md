# Verified limitation periods (Limitation Act, 1963 — THE SCHEDULE)

`limitation_schedule.json` holds all **137 articles** of the Schedule
(Periods of Limitation), extracted from the official India Code bare act.

It exists because limitation was previously model-memory — the dimension that,
per [`docs/drafting_correctness_audit.md`](../../docs/drafting_correctness_audit.md),
loses cases outright when it is wrong. This is step 4 of that audit's extraction
plan, and follows the same discipline as [`data/jurisdiction/`](../jurisdiction/README.md)
and [`data/special_acts/`](../special_acts/README.md).

## Source

- URL: <https://www.indiacode.nic.in/bitstream/123456789/1565/5/A1963-36.pdf>
- Document: *THE LIMITATION ACT, 1963 (Act 36 of 1963), THE SCHEDULE [See sections 2(j) and 3]*
- Local copy: [`source/limitation_1963.pdf`](source/limitation_1963.pdf) (24 pp)
- Public-domain statute text (Copyright Act s.52(1)(q)).

## Coverage

**137 articles, 137 verified.** Articles 1–113 (suits), 114–117 (appeals),
118–137 (applications). Each record carries `article`, `description`,
`period_text` (verbatim), `period` (`{value, unit}` for computation),
`starts_from` (the event the clock runs from), `source_ref` and `verified`.

## How it was built (re-runnable, deterministic)

```bash
python3 scripts/extract_limitation_schedule.py data/limitation/limitation_schedule.json
```

The Schedule is a three-column table, so plain text extraction is unsafe — it
interleaves the columns line by line and welds one article's period onto
another's description. Instead, as with the BNSS First Schedule:

- Column boundaries are read from **each page's own header rule**: the rule is a
  run of wide cell spans broken by very narrow separator rects, and those
  separator centres are the boundaries. Pages differ (some put the article
  number in its own gutter), so the last two separators are used.
- Words are assigned to a column by x-centre, then grouped into visual lines by
  a **y tolerance** rather than fixed bucket rounding.
- A row opens when the description column starts with an article number;
  other lines append cell by cell.
- Division/Part headings and amendment footnotes are dropped.

A row whose period or trigger cannot be read is written `verified:false` with
its verbatim text preserved, and the reading service skips it — an extraction
failure degrades to "not found", never to a guessed date.

## ⚠️ A period is not a deadline

`period` + `starts_from` give the **raw window only**. The Act's own extension
and exclusion provisions are **not encoded here**:

- **s.4** — when the court is closed on the last day, filing on reopening is in time
- **s.12** — time for obtaining a copy of the decree/order is excluded
- **s.14** — time spent bona fide in a court without jurisdiction
- **s.17** — fraud or mistake
- **s.18** — a fresh period runs from an acknowledgement in writing
- **s.5** — condonation of delay for appeals/applications

Any date computed from this data is therefore **provisional** and must be
presented as requiring verification before filing. Court-holiday calendars
(needed for s.4) are not in this repository.

## Read path

`backend/services/limitation_service.py` (calculators — task in progress).
Nothing may state a limitation date without also surfacing the caveats above.
