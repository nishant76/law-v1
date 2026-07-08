SNAPSHOT:{"document_type":"Research Report","outcome":null,"court":null,"judge":null,"date":null,"case_no":null,"appellant":null,"respondent":null}

# Executive Summary

## Purpose

- Define the requirements and scope for a **new Co-op Evaluation System (CES)** to replace RIT’s existing co-op evaluation application, enabling:
  - Students to provide feedback on their most recent co-op.
  - Employers to provide feedback on a student’s performance during their most recent co-op.
  - Faculty to approve or fail a student’s co-op.
  - OCSCE to gather data on students’ co-ops.
- Serve as a “definitive list of requirements” for **project sponsors’ sign-off** and to help the **project coach** evaluate whether the team met agreed requirements.

## Key Highlights

- Document is a **Software Requirements Specification** for **Co-op Evaluation System**, **Senior Project 2014–2015**.
- Identified problem with the current system: **performance, reliability, usability, and maintainability issues**, including **session timeouts** and **submission timeouts**.
- Project approach/priorities:
  - Primary goal: deliver a system **functionally equivalent** to the existing system, with fewer performance/reliability/maintainability issues.
  - If scope becomes too large: prioritize getting **forms working end-to-end** from **creation and assignment** through **approval or rejection**.
  - Design intent: build for **extensibility** so future teams (ITS or other senior project teams) can add features later.
- Requirements prioritization scheme:
  - **High**: required for functional system.
  - **Medium**: secondary; implement as many as time allows for functional equivalence.
  - **Low**: stretch goals / future development targets.

## Important Dates

- Revision history (document versions):
  - **v1.0 – 06.10.2014** (Initial revision)
  - **v1.1 – 16.10.2014** (Update after requirements phase; more info from Jim)
  - **v1.2 – 28.10.2014** (Update after feedback from Jim on 23.10.2014)
  - **v1.3 – 30.10.2014** (Update after feedback from Jim on 28.10.2014)
  - **v1.4 – 30.10.2014** (Updated VM specification)
  - **v1.5 – 03.11.2014** (Update after feedback from Kim on 28.10.2014)
  - **v1.6 – 05.11.2014** (Verified changes; added priority description)
  - **v1.7 – 18.02.2015** (Update to match changes going into development)
  - **v1.8 – 15.03.2015** (Removed redundant requirements; updated some priorities)
  - **v1.9 – 16.05.2015** (Final version before release)

## Risks / Constraints

- Scope risk expressly flagged: if the project scope is “too much,” the team will narrow focus to **end-to-end form workflow** (creation/assignment → approval/rejection).
- The replacement effort is driven by operational deficiencies in the legacy system:
  - **Session timeouts** and **submission timeouts** (inherent problems identified).
  - Broader issues: **performance, reliability, usability, maintainability**.

## Action Items

- For sponsors/approvers:
  - Use this SRS as the **sign-off baseline** for requirements (exact sign-off process/timing is **not specified in the excerpt**).
- For implementation planning:
  - Ensure the build meets “functional equivalence” while explicitly addressing the stated pain points (timeouts; usability improvements in reporting/forms/error messages).
  - Apply the document’s requirement **priority scheme** (High/Medium/Low) when planning delivery and managing scope.

## Key Takeaways

- This is a requirements artifact intended to lock down “what to build” for a new CES replacing an underperforming legacy system.
- Delivery priority is explicitly: functional equivalence first; enhancements only if time permits; minimum viable fallback is **forms end-to-end** capability.
- The excerpt does not contain specific acceptance criteria, deadlines for delivery, or sign-off dates beyond the revision history dates.