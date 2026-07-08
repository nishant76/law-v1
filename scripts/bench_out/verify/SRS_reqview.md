SNAPSHOT:{"document_type":"Research Report","outcome":null,"court":null,"judge":null,"date":null,"case_no":null,"appellant":null,"respondent":null}

# Executive Summary

## Purpose
- Provide a working **example Software Requirements Specification (SRS)** based on **ISO/IEC/IEEE 29148:2018** for a simple offline requirements-management application (functionality corresponding to **ReqView v1.0 (2015)**).
- The document expressly states it is **an example and not complete**.

## Key Highlights
- **Scope / capabilities**: capture requirements specifications; manage requirements using custom attributes; set up and browse traceability (including a traceability matrix); comment/review; filter/search; import from **MS Word** and **MS Excel**; export to **DOCX/XLSX/PDF/HTML/CSV**; analyze coverage/impact; print specifications.
- **Offline / data handling**:
  - Stores documents as **human readable files with open file format**.
  - Runs **offline**, **without server connection**.
  - Must **not send any project data to the Internet** (**[DEMO-SRS-176]**).
  - Persistent application data must be **encrypted** (**[DEMO-SRS-194]**).
  - Must **sanitize any data input or imported by users** (**[DEMO-SRS-199]**).
- **Platform / environment**:
  - Runs in latest **Chrome or Firefox** on **Windows, Linux, Mac** (also stated as a system attribute: **[DEMO-SRS-195]**).
- **Interfaces / formats**:
  - MS Word import/export via **HTML data format**; Excel import/export via **CSV**.
  - Stores project data in **JSON** to enable integration with third-party applications.
- **Functional requirement groups (illustrative, not exhaustive)**:
  - File operations: create/open/save; templates; import (Word/Excel); export (HTML/CSV).
  - Document view: table of contents; requirements table (columns include ID/Description/Discussion/Links plus custom attributes); sorting/hiding/reordering columns.
  - Editing: create/copy/move/delete/undelete/permanently remove requirements/sections; rich text paste (HTML); attachments; comments; traceability link types and links.
  - Auto-save: automatically persist changes and restore on restart; clear persisted data when closing the document.
  - Filtering/search: DNF filtering; filter missing traceability links; full-text search + navigation.
  - History of changes: record author/date-time/description; display and expand/collapse.
  - Reporting: print requirements table; create PDF of displayed requirements table.
- **Performance targets** (non-mandatory “should” statements unless otherwise stated):
  - Startup: display opened document within **10s** (**[DEMO-SRS-174]**).
  - Edit response: show updated values within **1s** (**[DEMO-SRS-171]**).
  - Scrolling: no jerks longer than **200ms** (**[DEMO-SRS-173]**).
  - Capacity: open documents up to **10,000 objects**, **100 attachments**, total attachment size up to **100 MB** (**[DEMO-SRS-170]**).

## Important Dates
- **Published on: 03.09.2021** (document header).
- Revision history (as stated):
  - **10.06.2016**: Export of demo SRS from ReqView **2.1.0** (Version **1**).
  - **12.06.2019**: Export of demo SRS from ReqView **2.6.2** (Version **2**).
  - **23.06.2020**: Update of Scope section (Version **3**).

## Risks / Constraints
- **Completeness risk**: the document states it is **not complete**; requirements coverage cannot be assumed beyond what is written.
- **Security/compliance constraints**: requirements to **not transmit project data to the Internet**, **encrypt persistent data**, and **sanitize imported/input data** impose implementation and verification burdens; failure would undermine stated product attributes.
- **Browser/version constraint**: “latest version” of Chrome/Firefox is a moving target and may create ongoing compatibility obligations (no further detail provided in the document).
- **Data interoperability constraints**: Word/Excel integration is specified through **HTML/CSV**, and internal storage in **JSON**—any deviation may break the described import/export behaviors.

## Action Items
- Treat as a **template/example**: confirm whether this SRS is intended to be contractually binding or only demonstrative (not specified in the document).
- If using for procurement/contracting:
  - Identify which requirements are **mandatory (“shall”)** vs **targets (“should”)** and align acceptance criteria accordingly.
  - Ensure verification planning references the separate **[DEMO-TESTS]** document (verification tests are stated to be specified there).
- For privacy/security review:
  - Map requirements **[DEMO-SRS-176]**, **[DEMO-SRS-194]**, **[DEMO-SRS-199]** to concrete controls and test cases (tests not included here).

## Key Takeaways
- This is an **ISO/IEC/IEEE 29148:2018-style SRS example** for an **offline requirements management** app emphasizing **traceability**, **import/export interoperability**, and **local data security** (no internet data transmission, encrypted persistence, sanitized inputs).
- No legal deadlines, notice periods, or enforceable timelines are created in the text beyond performance “should” targets; **no calculable deadlines** are stated.