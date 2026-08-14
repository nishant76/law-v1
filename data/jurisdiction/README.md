# Verified offence → court jurisdiction data (BNSS First Schedule)

`bnss_first_schedule.json` is a **verified** offence → court lookup built from the
official **BNSS 2023 First Schedule, Part I** ("Offences under the Bharatiya Nyaya
Sanhita"). It exists so the Strategic Filing Drafter (Feature 8) and Legal Process
Guide (Feature 10) determine the trial court from the **statute**, not from an
LLM's memory — per the launch-quality mandate.

## Source (government primary source, public-domain statute text)

- URL: <https://upload.indiacode.nic.in/schedulefile?aid=AC_CEN_5_23_00049_202346_1719552320687&rid=1191>
- Document: *173 THE FIRST SCHEDULE*, Bharatiya Nagarik Suraksha Sanhita, 2023 (Act 46 of 2023)
- Retrieved: **2026-07-15**
- Local copy: [`source/bnss_first_schedule.pdf`](source/bnss_first_schedule.pdf) (47 pp)

## How it was built (re-runnable, deterministic)

1. `scripts/extract_bnss_schedule.py <pdf> source/bnss_raw_rows.json`
   Coordinate-based table parse. Column boundaries are read **per page** from the
   table's header rule rectangles (they vary page to page). Nothing is filled
   from memory — every cell is the PDF's own text at its column x-position.
2. `scripts/build_jurisdiction_json.py source/bnss_raw_rows.json bnss_first_schedule.json`
   Derives `cognizable`/`bailable` booleans and the `court_tier` enum from the
   Schedule's verbatim columns; writes the manifest.

## Fields (per record)

`bns_section`, `sub_scenario`, `offence`, `punishment_summary`,
`max_imprisonment_years` (999 = life, 1000 = death), `cognizable`/`bailable`
(bool; `null` = "according as the abetted offence"), `triable_by` (verbatim
Schedule wording), `court_tier` (derived enum mapped to BNSS Ss.21-23),
`ipc_equivalent`, `source_ref`, `verified`.

## Coverage & verification status

- 462 offence rows across 287 distinct base sections (BNS 49–357).
- 461 verified; 1 unverified (s264 — a chapeau heading with no court of its own;
  its real data is in sub-clauses (a)/(b), which ARE verified). No court is ever
  guessed: an unresolved court is `verified:false` + `triable_by:null`.
- Definition-only BNS sections carry no Schedule row and are legitimately absent.

## Known TODOs

- **`ipc_equivalent` is null for every record.** The First Schedule contains no
  BNS↔IPC mapping, so it was NOT filled from memory. Populate from a verified
  government BNS↔IPC comparison table in a follow-up pass.
- Read path: [`backend/services/jurisdiction_service.py`](../../backend/services/jurisdiction_service.py).
  Wiring the filing drafter / Legal Process Guide to read from this (replacing the
  prompt's inline hand-curated table) is a deliberate follow-up — do it only once
  this data is trusted.

## Regime note

BNSS/BNS governs offences **on/after 01-Jul-2024**. For earlier offences the
CrPC/IPC classification applies under the savings clause. This table is
BNSS-regime.
