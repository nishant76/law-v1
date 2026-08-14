"""
Build data/jurisdiction/bnss_first_schedule.json from the verified raw rows
produced by extract_bnss_schedule.py.

Each output record is traceable to a single First Schedule row (source_ref
carries the schedule page). Nothing is inferred from memory:
  * cognizable / bailable booleans are read from the Schedule's own
    Cognizable/Non-cognizable and Bailable/Non-bailable columns.
  * triable_by is the Schedule's exact "By what Court triable" wording
    (whitespace/glyph-tracking normalised).
  * court_tier is a derived enum that maps that verbatim wording onto the
    court hierarchy of BNSS Ss.21-23 (Court of Session / Magistrate of the
    first class / second class / any Magistrate). It is a mechanical mapping
    of the Schedule text, NOT an independent judgement.
  * ipc_equivalent is left null: the First Schedule does not contain the
    BNS<->IPC mapping, and we do not fill it from memory. Populating it from a
    verified government comparison table is a separate TODO (see manifest).
  * verified=false + triable_by=null ONLY when the court column could not be
    resolved to a Schedule category. We never guess a court.

Usage:
  python3 scripts/build_jurisdiction_json.py <raw_rows.json> <out.json>
"""
import json
import re
import sys
from datetime import date

SOURCE_URL = ("https://upload.indiacode.nic.in/schedulefile"
              "?aid=AC_CEN_5_23_00049_202346_1719552320687&rid=1191")
RETRIEVED = "2026-07-15"


def _nsx(s):
    return re.sub(r"\s+", "", s).lower()


def classify_cognizable(raw):
    x = _nsx(raw)
    if "accordingas" in x:
        return None, "According as offence abetted is cognizable or non-cognizable."
    if "non-cognizable" in x or "noncognizable" in x or ("non" in x and "cognizable" in x):
        return False, "Non-cognizable."
    if "cognizable" in x:
        return True, "Cognizable."
    return None, None


def classify_bailable(raw):
    x = _nsx(raw)
    if "accordingas" in x:
        return None, "According as offence abetted is bailable or non-bailable."
    if "non-bailable" in x or "nonbailable" in x or ("non" in x and "bailable" in x):
        return False, "Non-bailable."
    if "bailable" in x:
        return True, "Bailable."
    return None, None


def classify_court(raw):
    """-> (triable_by_verbatim, court_tier_enum, verified)."""
    clean = re.sub(r"\s+", " ", raw).strip()
    x = _nsx(raw)
    if "courtofsession" in x:
        return "Court of Session.", "COURT_OF_SESSION", True
    # s210-style special committal phrasing (contains 'any magistrate' but is a
    # conditional committal rule) — keep verbatim, tier SPECIAL.
    if "thecourtinwhichtheoffenceiscommitted" in x:
        return clean, "SPECIAL_COMMITTAL", True
    if "firstclass" in x:
        return "Magistrate of the first class.", "MAGISTRATE_FIRST_CLASS", True
    if "secondclass" in x:
        return "Magistrate of the second class.", "MAGISTRATE_SECOND_CLASS", True
    if "anymagistrate" in x:
        return "Any Magistrate.", "ANY_MAGISTRATE", True
    if "courtbywhich" in x and "abetted" in x:
        return ("Court by which the abetted offence is triable.",
                "ABETMENT_DEPENDENT", True)
    if "courtbywhich" in x:
        # e.g. "Court by which offence of giving false evidence is triable."
        return clean, "OFFENCE_DEPENDENT", True
    return None, None, False  # could not resolve -> not verified, never guessed


def max_imprisonment_years(punishment):
    p = punishment.lower()
    vals = []
    if "death" in p:
        vals.append(1000)
    if re.search(r"imprisonment for life|for life|transportation for life", p):
        vals.append(999)
    for m in re.finditer(r"(\d+)\s*years?", p):
        vals.append(float(m.group(1)))
    for m in re.finditer(r"(\d+)\s*months?", p):
        vals.append(round(int(m.group(1)) / 12.0, 2))
    if vals:
        v = max(vals)
        return int(v) if v == int(v) else v
    return 0  # fine only / community service / no imprisonment term stated


def main():
    raw_path, out_path = sys.argv[1], sys.argv[2]
    rows = json.load(open(raw_path))
    out = []
    for r in rows:
        cog, cog_txt = classify_cognizable(r["cognizable"])
        bail, bail_txt = classify_bailable(r["bailable"])
        triable, tier, verified = classify_court(r["court"])
        punishment = re.sub(r"\s+", " ", r["punishment"]).strip()
        out.append({
            "bns_section": r["section"],
            "sub_scenario": r["sub_scenario"],
            "offence": re.sub(r"\s+", " ", r["offence"]).strip(),
            "punishment_summary": punishment,
            "max_imprisonment_years": max_imprisonment_years(punishment),
            "cognizable": cog,
            "cognizable_text": cog_txt,
            "bailable": bail,
            "bailable_text": bail_txt,
            "triable_by": triable,             # verbatim Schedule wording
            "court_tier": tier,                # derived enum (BNSS Ss.21-23 map)
            "ipc_equivalent": None,            # TODO: verified BNS<->IPC table
            "source_ref": (f"BNSS First Schedule, Part I, p.{r['page']} "
                           "(indiacode aid AC_CEN_5_23_00049_202346)"),
            "verified": verified,
        })

    verified_n = sum(1 for o in out if o["verified"])
    manifest = {
        "title": "BNSS 2023 First Schedule — Classification of Offences (Part I: "
                 "Offences under the Bharatiya Nyaya Sanhita)",
        "source_url": SOURCE_URL,
        "source_document": "173 THE FIRST SCHEDULE, Bharatiya Nagarik Suraksha "
                           "Sanhita, 2023 (Act 46 of 2023)",
        "retrieved_date": RETRIEVED,
        "regime_note": "BNSS/BNS applies to offences committed on or after "
                       "01-Jul-2024. For earlier offences the CrPC/IPC classification "
                       "governs under the savings clause. This table is BNSS-regime.",
        "columns_source": "Section / Offence / Punishment / Cognizable-or-Non-"
                          "cognizable / Bailable-or-Non-bailable / By-what-Court-"
                          "triable, read per-row from the Schedule table.",
        "court_tier_note": "court_tier is a mechanical mapping of the Schedule's "
                          "verbatim 'By what Court triable' wording onto the BNSS "
                          "Ss.21-23 hierarchy. 'Magistrate of the first class' "
                          "covers both CJM and JMFC under S.21 — the Schedule does "
                          "not distinguish them, so neither does this field.",
        "ipc_equivalent_status": "NOT POPULATED — the First Schedule contains no "
                                 "BNS<->IPC mapping; will be filled from a verified "
                                 "government comparison table in a follow-up pass.",
        "total_records": len(out),
        "distinct_base_sections": len({re.match(r'\d+', o['bns_section']).group()
                                       for o in out}),
        "verified_records": verified_n,
        "unverified_records": len(out) - verified_n,
        "section_range": "BNS 49-357 (offence-creating sections; definition-only "
                         "sections are absent because they carry no Schedule row)",
    }
    with open(out_path, "w") as f:
        json.dump({"manifest": manifest, "offences": out}, f, indent=1,
                  ensure_ascii=False)
    print(json.dumps(manifest, indent=1))
    print("wrote", out_path)


if __name__ == "__main__":
    main()
