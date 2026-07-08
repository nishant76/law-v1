SNAPSHOT:{"document_type":"Research Report","outcome":null,"court":null,"judge":null,"date":"04.03.2003","case_no":null,"appellant":null,"respondent":null}

# Executive Summary

## Purpose
- To define the **software requirements** (functional, interface, performance, and error recovery) for the **Company X Instrument A Data Processing Unit (DPU) Flight Software (FSW)**, identified as **DPUSRS-01 Rev 2 Chg 2**.

## Key Highlights
- Document type/level: A **Level 4 specification** (per **410.4-SPEC-0004, Company X Missions Requirements Document**).
- Mission/system context (high level): The **Company X observatory** is a medium-class explorer satellite mission aimed at understanding the origin of **Gamma-Ray Detectors (GRDs)** and studying approximately **1000 detectors** over a **planned three-year mission**.
- Instrument context: **Instrument A** provides UV/optical coverage with photon-counting detectors; it has two processing units:
  - **Instrument Control Unit (ICU)**: controls telescope commanding.
  - **Data Processing Unit (DPU)**: handles **data collection, processing, and formatting**.
- Key interfaces described at overview level:
  - **DPU ↔ ICU** via **Synchronous Serial Interface (SSI)** (protocol specified in **DPUICD-01**).
  - **DPU receives** raw photon position/timing data via **Data Capture Interface (DCI)**.
  - **DPU → SCU** telemetry via **MIL-STD-1553** interface; data formatted as **CCSDS Source Packets**.
  - DPU keeps a local copy of the spacecraft clock for timestamping telemetry.
- Requirements management/traceability:
  - Requirements for each CSC are maintained in a **configuration-controlled electronic spreadsheet**; a copy is in **Appendix A (Software Requirements Matrix)**.
- Change history (this revision):
  - **Rev 2 Chg 2 dated 04.03.2003** updates “redlines from Build 6 Review #1”.
  - Several edits in Section **5.15 (Data Compression CSC)**:
    - **5.15.1.1 / 5.15.1.2 / 5.15.3.2** updated to refer to “**compression software**” because a “compression task” will not be implemented.
    - “**Lossless**” was struck because a **lossy compression scheme** was designed at the request of the science team.
    - **5.15.2.1 / 5.15.2.2** stated to be no longer relevant (no **DCX task**); storage re-apportioned to **DPA-TMALI** and **DPA-SCUI**.
    - **5.15.3.1** design preference: discard new data until current data will fit; hardware supports this.
  - **5.19.1.6** moved to **Build 7** (tracking software relevance).
  - **5.19.3.1**: “Remove TBR.”
- Completeness caveat: Where final numerical values or specification references are not available, best estimates are marked **TBR**; undefined items are **TBD** (a table intended to summarize TBD/TBR is present but not populated in the provided extract).

## Important Dates
- **06.09.2000**: Draft version (WIP090600) for Software Requirements Review at PSU.
- **17.10.2000**: **Rev 0 Chg 0** initial baseline.
- **12.04.2001**: **Rev 1 Chg 0** (multiple ECRs incorporated; includes EEPROM size change to **3MB**, hardware/interface/design updates).
- **12.09.2001**: **Rev 2 Chg 0** (traceability updates; ECRs incorporated including ADC channel, WDT clock reset impacts, boot defaults, EEPROM exception data, verification levels).
- **09.04.2002**: **Rev 2 Chg 1** (science software traceability to SVP; algorithms added; EEPROM map updated for science software config area).
- **04.03.2003**: **Rev 2 Chg 2** (current issue; Build 6 Review #1 redlines; compression wording/design updates; some requirements moved to Build 7).
- Document states the mission is planned for a **three-year** duration (no start/end dates provided).

## Risks / Constraints
- **TBD/TBR items**: The document explicitly notes that some values/references may be **best estimates** (TBR) or **not yet defined** (TBD). The specific TBD/TBR list is not provided in the excerpt.
- Interface dependency: Several requirements are derived from/synchronized with external ICDs and higher-level requirements documents; conflicts may be governed by “**Superseding/Superceding**” applicability notes in the referenced documents list (e.g., **1553 Bus Protocol ICD**, **Science Requirements**, **Mission Requirements**).
- Design change risk flagged by revision notice: Shift from “lossless” to **lossy compression scheme** (requested by the science team) and removal of a “compression task” concept may affect downstream verification/traceability and performance assumptions (detail not provided in excerpt).

## Action Items
- Confirm and control the applicable versions of key dependency documents explicitly cited as governing interfaces/requirements:
  - **DPUICD-01 Rev 1 Chg 0 (June 2001)** (ICU–DPU protocol).
  - **1143 (1553 Bus Protocol ICD)** and **Spacecraft to Payload Telecommand ICD** (two entries shown).
  - **410.4-SPEC** Science Requirements (Version 1.0) and Mission Requirements (Version 1.1), both marked superseding.
- Obtain/verify the configuration-controlled **Appendix A requirements spreadsheet** corresponding to **DPUSRS-01 Rev 2 Chg 2** for the authoritative per-CSC requirements and verification traceability.
- For compression-related requirements, ensure engineering and verification teams align to the revision notice changes (lossy vs lossless wording; removal of DCX task references; new data discard behavior), using the updated Section **5.15** requirements text (not included in the excerpt).

## Key Takeaways
- This document is a **software requirements specification** (not a contract or legal notice) governing the **DPU flight software** for **Instrument A** in the Company X mission, with heavy reliance on **interface control documents** and a **separate configuration-controlled requirements matrix** for detailed CSC-level requirements and traceability.
- The **current revision (04.03.2003)** reflects notable **compression-related requirement language and design direction changes** (including movement away from “lossless” terminology due to adoption of a **lossy compression scheme**).