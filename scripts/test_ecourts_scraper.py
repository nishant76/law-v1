"""
Test the ecourtsindia.com scraper.

Usage:
  python scripts/test_ecourts_scraper.py --name "Neera Rani"
  python scripts/test_ecourts_scraper.py --name "Himanshu Singla" --state punjab
  python scripts/test_ecourts_scraper.py --name "Neera Rani" --state haryana --status Disposed
"""
import argparse
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.ecourts_scraper_service import (
    scrape_lawyer_cases,
    find_lawyer_slug,
    name_to_slug,
    ECOURTS_INDIA_STATE_CODES,
)


async def main():
    parser = argparse.ArgumentParser(description="Test ecourtsindia.com scraper")
    parser.add_argument("--name", required=True, help="Advocate name, e.g. 'Neera Rani'")
    parser.add_argument("--state", default=None,
                        help="State key: punjab / haryana / chandigarh / delhi (default: all)")
    parser.add_argument("--status", default="Pending",
                        help="Case status: Pending / Disposed / Both (default: Pending)")
    args = parser.parse_args()

    print("=" * 60)
    print("ecourtsindia.com Scraper Test")
    print("=" * 60)
    print("Name:   %s" % args.name)
    print("Slug:   %s" % name_to_slug(args.name))
    print("State:  %s" % (args.state or "all states"))
    print("Status: %s" % args.status)
    print()

    print("Scraping cases...")
    result = await scrape_lawyer_cases(
        name=args.name,
        state=args.state,
        status=args.status,
    )

    print("Pages fetched: %d" % result["pages_fetched"])
    print("CNRs found:    %d" % result["total_found"])
    print()

    if result["cnrs"]:
        print("First 10 CNRs:")
        for cnr in result["cnrs"][:10]:
            print("  %s  ->  https://ecourtsindia.com/cnr/%s" % (cnr, cnr))
        if len(result["cnrs"]) > 10:
            print("  ... and %d more" % (len(result["cnrs"]) - 10))
    else:
        print("No CNRs found.")
        print()
        print("Searching for possible profile slugs...")
        candidates = await find_lawyer_slug(args.name)
        print("Candidates:")
        for c in candidates[:5]:
            print("  https://ecourtsindia.com/lawyer/%s  (%s)" % (c["slug"], c["source"]))

    print()
    print("=" * 60)


asyncio.run(main())
