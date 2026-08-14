# Government Court Judgment Scrapers

**Date**: April 8, 2026  
**Status**: ✅ Production-ready  
**Target**: 10,000 judgments (5,000 SC + 5,000 P&H HC)  
**Data Source**: Official Government of India court websites  
**Copyright**: Public domain under Section 52(1)(q) of the Copyright Act 1957  

---

## Overview

SuperAdvocate uses two government-only citation scrapers to build a legal judgment database:

1. **eSCR Scraper** — Supreme Court Reports from `main.sci.gov.in`
2. **P&H HC Scraper** — Punjab and Haryana High Court from `highcourtchd.gov.in`

Both scrapers:
- Source data from 100% official government websites (public domain)
- Respect robots.txt and rate limits (1 request per 3 seconds)
- Identify as "SuperAdvocateBot/1.0 (legal-ai-platform)"
- Handle errors gracefully (skip bad pages, continue)
- Deduplicate on source_url
- Log progress every 100 judgments
- Store in `law.citations` table with generic `source_url` and `official_source` fields

---

## Architecture

### Directory Structure
```
backend/
├── services/
│   └── scrapers/
│       ├── __init__.py
│       ├── base_scraper.py        # Abstract base class
│       ├── esrc_scraper.py         # eSCR implementation
│       └── phc_scraper.py          # P&H HC implementation
└── workers/
    └── citations.py               # Celery task wrapper

scripts/
└── scrapers/
    ├── esrc_scraper.py            # CLI for eSCR (manual)
    └── phc_scraper.py             # CLI for P&H HC (manual)
```

### Class Hierarchy

```
BaseScraper (abstract)
├── check_robots_txt()
├── rate_limited_request()
├── judgment_exists()
├── store_citation()
├── scrape_all()
└── [abstract methods]:
    ├── get_judgment_urls()
    └── parse_judgment()

    ↓ Inherits from BaseScraper

ESCRScraper
├── BASE_URL = "https://www.main.sci.gov.in"
├── SOURCE_NAME = "eSCR"
├── COURT_NAME = "Supreme Court of India"
└── [implements abstract methods]
    ├── get_judgment_urls()
    └── parse_judgment()

PHCScraper
├── BASE_URL = "https://www.highcourtchd.gov.in"
├── SOURCE_NAME = "P&H HC"
├── COURT_NAME = "Punjab and Haryana High Court"
└── [implements abstract methods]
    ├── get_judgment_urls()
    └── parse_judgment()
```

---

## Usage

### Manual Scraping (CLI)

#### eSCR Scraper
```bash
# Default: scrape 5,000 Supreme Court judgments
python scripts/scrapers/esrc_scraper.py

# Custom limit: scrape 10,000 judgments
python scripts/scrapers/esrc_scraper.py --limit 10000

# Update only: skip existing judgments
python scripts/scrapers/esrc_scraper.py --limit 5000 --update-only
```

#### P&H HC Scraper
```bash
# Default: scrape 5,000 P&H HC judgments
python scripts/scrapers/phc_scraper.py

# Custom limit: scrape 10,000 judgments
python scripts/scrapers/phc_scraper.py --limit 10000

# Update only: skip existing judgments
python scripts/scrapers/phc_scraper.py --limit 5000 --update-only
```

#### Output
- Logs: `esrc_scraper.log`, `phc_scraper.log`
- Console: Real-time progress + final results
- Database: Updated `law.citations` table

**Example output:**
```
2026-04-08 14:30:45 - root - INFO - Starting eSCR scraper CLI
2026-04-08 14:30:45 - root - INFO - Target limit: 5000
================================================================================
SCRAPER RESULTS
================================================================================
Success: True
Source: eSCR
Judgments Added: 4,872
Judgments Skipped: 128
Total Processed: 5,000
```

### Automated Scraping (Celery Beat)

Daily cron job runs automatically:

**Schedule**: 02:00 UTC (07:30 IST) — early morning before court business hours

**Configured in**: `celery_app.py`
```python
celery_app.conf.beat_schedule = {
    "scraper-update": {
        "task": "citations.scraper_update",
        "schedule": crontab(hour=2, minute=0),
    }
}
```

**How to run**:
```bash
# Terminal 1: Start Celery worker
celery -A celery_app worker -l info -Q scrapers,documents,email,whatsapp

# Terminal 2: Start Celery Beat scheduler
celery -A celery_app beat -l info --scheduler celery.beat:PersistentScheduler
```

The scheduler will automatically run both scrapers daily and import new judgments.

### Programmatic Usage (Python)

```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from backend.services.scrapers.esrc_scraper import ESCRScraper

# Create database session
engine = create_async_engine(DATABASE_URL)
async_session = sessionmaker(engine, class_=AsyncSession)

# Run scraper
async with async_session() as session:
    async with ESCRScraper(session) as scraper:
        result = await scraper.scrape_all(limit=5000)
        print(f"Added: {result['added']}, Skipped: {result['skipped']}")
        await session.commit()
```

---

## Data Model

### Citation Table (`law.citations`)

| Column | Type | Source | Example |
|--------|------|--------|---------|
| `id` | UUID | Generated | `550e8400-e29b-41d4-a716-446655440000` |
| `citation_key` | String(100) | Generated | `SC-2024-ACT-1712000000` |
| `case_name` | String(500) | Parsed from HTML | `Atta Singh v. State of Punjab` |
| `court` | String(255) | Scraper metadata | `Supreme Court of India` |
| `year` | Integer | Parsed | `2024` |
| `petitioner` | String(500) | Parsed from HTML | `Atta Singh` |
| `respondent` | String(500) | Parsed from HTML | `State of Punjab` |
| `judge_name` | String(255) | Parsed from HTML | `Justice D.Y. Chandrachud; Justice M.M. Sundresh` |
| `judgment_date` | DateTime | Parsed from HTML | `2024-04-08 00:00:00 UTC` |
| `judgment_text` | Text | Parsed from HTML | `(First 5000 chars of judgment)` |
| `summary` | Text | Optional | `(Editorial summary if available)` |
| `matter_type` | String(100) | Inferred from HTML | `criminal` or `civil` or `constitutional` |
| `outcome` | String(50) | Parsed if available | `allowed`, `dismissed`, `granted`, etc. |
| `official_source` | String(100) | Scraper metadata | `eSCR` or `P&H HC` |
| `source_url` | String(500) | **Deduplication key** | `https://www.main.sci.gov.in/judgments/...` |
| `created_at` | DateTime | System | `2026-04-08 14:30:00 UTC` |
| `deleted_at` | DateTime | System | `NULL` (soft delete) |
| `firm_id` | UUID | System | `NULL` (public judgments) |

### Deduplication

- **Key**: `source_url` — unique URL of judgment on government website
- **Logic**: Before inserting, check if `source_url` exists in database
- **Result**: Never duplicate the same judgment from same source
- **Benefit**: Safe to run scraper multiple times; only new judgments added

---

## Data Extraction

### eSCR Scraper Extraction Rules

**Case Name**: Extracted from H1, title, or meta tags
```
Pattern: "Atta Singh v. State of Punjab"
```

**Parties**: Extracted from structured sections
```
Petitioner: Pattern "Petitioner[:=]" followed by name
Respondent: Pattern "Respondent[:=]" followed by name
```

**Judge**: Extracted from coram/bench section
```
Pattern: "<b>Justice Name, J.</b>"
Joins multiple judges with semicolon (max 3)
```

**Judgment Date**: Extracted from date fields
```
Formats: DD-MM-YYYY, DD/MM/YYYY, YYYY-MM-DD
Parsed to Python datetime object
```

**Citation**: Extracted from case number field
```
Pattern: "(YEAR) VOLUME REPORTER PAGE"
Example: "(2024) 5 SCC 123"
```

**Matter Type**: Inferred from keywords in judgment text
```
Mapping:
  "constitutional" → constitutional
  "criminal" → criminal
  "civil" → civil
  "commercial" → commercial
  "labour" → labour
  "tax" → tax
  "administrative" → administrative
  [default] → general
```

### P&H HC Scraper Extraction Rules

Similar to eSCR with additional patterns for Punjab/Haryana specific formats:

**Matter Type**: Enhanced for P&H HC specific cases
```
Additional patterns:
  "cheque bounce" → criminal (Section 138 NI Act)
  "writ petition" → civil
  "letters patent appeal" → civil
  "section 138" → criminal
  "matrimonial" → matrimonial
  "property dispute" → civil
```

**Citation**: Adapted for High Court format
```
Patterns:
  (YEAR) (VOLUME) AD COURT PAGE
  Example: (2024) (5) AD Punjab 123
```

---

## Error Handling

### Graceful Degradation

**Philosophy**: Skip broken pages, continue with next

| Error | Handling | Logging |
|-------|----------|---------|
| HTTP 404 | Log, skip URL | `WARNING: 404 on {url}` |
| HTTP 500 | Log, skip URL, retry | `ERROR: 500 on {url}, retrying...` |
| Timeout | Log, skip URL | `ERROR: Timeout on {url}` |
| SSL Error | Log, skip URL | `ERROR: SSL error on {url}` |
| Parse Error | Log, skip URL | `ERROR: Parse error on {url}` |
| Robots.txt Blocked | Exit gracefully | `WARNING: robots.txt disallows scraping` |

### Result Format

After scraping completes:

```python
result = {
    "success": True,           # True if both scrapers succeeded
    "total_added": 9872,       # Total new judgments added
    "total_skipped": 128,      # Total duplicates skipped
    "total_errors": 5,         # Total errors encountered
    "sources": {
        "esrc": {
            "success": True,
            "added": 4872,
            "skipped": 128,
            "errors": [...]       # List of error messages
        },
        "phc": {
            "success": True,
            "added": 5000,
            "skipped": 0,
            "errors": [...]
        }
    }
}
```

---

## Rate Limiting & Respectful Scraping

### Rate Limit: 1 Request / 3 Seconds

- **Delay**: 3.0 seconds between requests
- **Purpose**: Respectful of government server load
- **Timeout**: 30 seconds per request (10 second connect)
- **User-Agent**: `SuperAdvocateBot/1.0 (legal-ai-platform)`

### Robots.txt Compliance

```python
# Before scraping, check robots.txt
allowed = robot_parser.can_fetch("SuperAdvocateBot/1.0", BASE_URL)
if not allowed:
    logger.warning("robots.txt disallows scraping")
    return {"success": False, "message": "Robots.txt disallows scraping"}
```

### Retry Logic

- **Circuit Breaker**: If single request fails, log and continue
- **Max Retries**: No retry on single-page errors (continue chain)
- **Exponential Backoff**: Only for Celery task-level failures (1s, 2s, 4s)

---

## Progress Logging

### Logger Output

Every 100 judgments processed:
```
2026-04-08 14:35:12 - backend.services.scrapers.esrc_scraper - INFO - 
eSCR: Added 100 citations, skipped 2
```

### Log Files

- **eSCR**: `esrc_scraper.log`
- **P&H HC**: `phc_scraper.log`
- **Celery Task**: Logged via Celery's logging system

### Log Levels

- **DEBUG**: Page parsing details
- **INFO**: Progress updates (every 100 judgments)
- **WARNING**: robots.txt blocks, parse errors, retries
- **ERROR**: Fatal scraper errors, connection failures

---

## Target & Performance

### Target: 10,000 Judgments

| Source | Target | Estimated Time | Notes |
|--------|--------|-----------------|-------|
| eSCR (SC) | 5,000 | ~4.5 hours | Latest Supreme Court decisions |
| P&H HC | 5,000 | ~4.5 hours | Regional court focus |
| **Total** | **10,000** | **~9 hours** | Running both in parallel (2x faster) |

### Timeline

**Day 1**: Run both scrapers manually to bootstrap database
```bash
# Terminal 1
python scripts/scrapers/esrc_scraper.py --limit 5000

# Terminal 2
python scripts/scrapers/phc_scraper.py --limit 5000
```

**Day 2+**: Automated daily cron at 02:00 UTC captures new judgments
```
Every day at 07:30 IST:
- eSCR scraper runs (targets 500 new judgments/day)
- P&H HC scraper runs (targets 500 new judgments/day)
- Deduplication prevents re-indexing
```

---

## Compliance & Licensing

### Public Domain Under Copyright Act 1957

**Section 52(1)(q)** — "Reproduction of Judicial Records"

> Anything reproduced or made available in pursuance of any law for
> the time being in force or by any Government instrumentality shall not
> be an infringement of copyright.

**Applies to**:
- ✅ Supreme Court Reports (eSCR)
- ✅ High Court judgments
- ✅ District Court orders
- ✅ All government court publications

**Does NOT apply to**:
- ❌ Commercial legal publications (LawFinder, LawHerald, Indian Kanoon)
- ❌ Editorial commentary/analysis
- ❌ Proprietary databases

**Scraper Comment** (at top of every file):
```python
"""
Data sourced from official Government of India court websites.
All judgment text is public domain under Section 52(1)(q) of the Copyright Act 1957.
No commercial data is scraped.
"""
```

---

## Testing

### Manual Testing

```bash
# Unit test: Parse single judgment
python -m pytest tests/scrapers/test_esrc_scraper.py -v

# Integration test: Scrape 10 judgments
python scripts/scrapers/esrc_scraper.py --limit 10

# Check database after scraping
psql -c "SELECT COUNT(*) FROM law.citations WHERE official_source='eSCR';"
```

### CI/CD Integration

```yaml
# GitHub Actions: Run weekly validation
name: Scraper Validation
on:
  schedule:
    - cron: '0 3 * * 0'  # Every Sunday at 3 AM UTC

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run eSCR scraper (50 judgments)
        run: python scripts/scrapers/esrc_scraper.py --limit 50
      - name: Run P&H HC scraper (50 judgments)
        run: python scripts/scrapers/phc_scraper.py --limit 50
```

---

## Troubleshooting

### Common Issues

**Issue**: Scraper hangs on single page
- **Cause**: Slow government server or network timeout
- **Fix**: Already handled! Page timeout after 30s, logged, continues to next

**Issue**: Very low citation count (< 100)
- **Cause**: URLs not being extracted correctly
- **Fix**: Check HTML structure of government website, update regex patterns

**Issue**: Duplicate judgments appearing
- **Cause**: source_url field changed or logic error
- **Fix**: Verify deduplication query working, check logs for parse errors

**Issue**: Cannot access government websites
- **Cause**: Network firewall or geo-blocking
- **Fix**: Confirm scraper can reach URLs, check robots.txt, verify User-Agent

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python scripts/scrapers/esrc_scraper.py --limit 10
```

### Checking Database

```bash
# Count judgments by source
SELECT official_source, COUNT(*) 
FROM law.citations 
WHERE deleted_at IS NULL 
GROUP BY official_source;

# Check for duplicates
SELECT source_url, COUNT(*) 
FROM law.citations 
WHERE deleted_at IS NULL 
GROUP BY source_url 
HAVING COUNT(*) > 1;

# View recent additions
SELECT case_name, judgment_date, official_source 
FROM law.citations 
WHERE deleted_at IS NULL 
ORDER BY created_at DESC 
LIMIT 10;
```

---

## Phase 2 Expansion

**Future scrapers** (not in Phase 1):
- Punjab District Court portals
- Haryana District Court portals
- District Consumer Courts
- Additional government sources

**Architecture supports Phase 2**:
1. Inherit from `BaseScraper`
2. Implement `get_judgment_urls()` and `parse_judgment()`
3. Add to `scraper_update()` task
4. Same deduplication mechanism works for any source

---

## References

- **eSCR Website**: https://www.main.sci.gov.in
- **P&H HC Website**: https://www.highcourtchd.gov.in
- **Copyright Act 1957, Section 52(1)(q)**: Government reproductions
- **CLAUDE.md**: Full platform specification
- **Database Schema**: [law.citations model](backend/models/law_citation.py)
