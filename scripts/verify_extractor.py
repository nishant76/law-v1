"""
Verify the PDF Extractor readable briefing across many document types.

Runs the REAL READABLE_SYSTEM_PROMPT / READABLE_USER_TEMPLATE through the REAL
LLMService streaming path (READABLE_MODEL = GPT-5.2), parses the SNAPSHOT line,
and checks DOCUMENT ROUTING correctness:

  - Court judgments/orders  -> judgment template (Winning Argument, Court's
                               Reasoning, Operative Directions, etc.)
  - Everything else         -> Executive Summary (no fabricated legal sections)

Writes each full output to scripts/bench_out/verify/<tag>.md and a summary table.

Run from repo root:
    python scripts/verify_extractor.py                 # whole corpus
    python scripts/verify_extractor.py LABEL1 LABEL2   # only these labels
"""
import asyncio
import io
import json
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.services.llm_service import get_llm_service, ModelType  # noqa: E402
from backend.services.prompts.pdf_extractor import (  # noqa: E402
    READABLE_SYSTEM_PROMPT,
    READABLE_USER_TEMPLATE,
    READABLE_MODEL,
)
from backend.core.sanitiser import sanitise_document_text  # noqa: E402

PDF_DIR = Path(r"D:\NISHANT\test-pdfs")
OUT_DIR = Path(__file__).resolve().parent / "bench_out" / "verify"

# label -> (filename, category, expect_judgment_template)
CORPUS = {
    # ---- Legal: judgments / court orders (must be perfectly detailed) ----
    "JUD_charnbir":   ("CWP-No.-13338-of-2025-(CHARNBIR-SINGH-VERSUS-PUNJABI-UNIVERSITY-PATIALA-AND-OTHERS).pdf", "judgment", True),
    "JUD_manik":      ("CWP-No.-39633-OF-2025-(MANIK-KHURANA-VERSUS-THE-CENTRAL-ADMINISTRATIVE-TRIBUNAL-AND-OTHERS).pdf", "judgment", True),
    "JUD_cocp":       ("COCP_1484_2016_21_12_2016_FINAL_ORDER.pdf", "judgment", True),
    "JUD_madan":      ("Madan and Rakesh.pdf", "judgment", True),
    "JUD_pbpt":       ("PBPT010007012024_22_2026-02-27.pdf", "judgment", True),
    "JUD_jassar":     ("Jassar display_pdf.pdf", "judgment", True),
    "NOTICE_sample":  ("Sample Legal Notice - pdf_upload-369733.pdf", "legal_notice", False),
    # ---- SRS ----
    "SRS_reqview":    ("SRS_reqview.pdf", "srs", False),
    "SRS_wvu":        ("SRS_wvu.pdf", "srs", False),
    "SRS_chalmers":   ("SRS_chalmers.pdf", "srs", False),
    "SRS_rit":        ("SRS_rit.pdf", "srs", False),
    # ---- Product launch ----
    "PL_productplan": ("The-Anatomy-of-a-Product-Launch-by-ProductPlan.pdf", "product_launch", False),
    "PL_pragmatic":   ("PLAUNCH_pragmatic.pdf", "product_launch", False),
    "PL_zaslofsky":   ("PLAUNCH_zaslofsky.pdf", "product_launch", False),
    "PL_crayon":      ("PLAUNCH_crayon.pdf", "product_launch", False),
    # ---- Employee handbook ----
    "HB_turner":      ("HANDBOOK_turner.pdf", "handbook", False),
    "HB_publiccounsel": ("HANDBOOK_publiccounsel.pdf", "handbook", False),
    "HB_udp":         ("HANDBOOK_udp.pdf", "handbook", False),
    # ---- Annual reports ----
    "AR_disney":      ("AR_disney2022.pdf", "annual_report", False),
    "AR_cision":      ("AR_cision2022.pdf", "annual_report", False),
    "AR_aquaporin":   ("AR_q4cdn2022.pdf", "annual_report", False),
    # ---- Brochures ----
    "BR_camry":       ("BROCHURE_toyota_camry.pdf", "brochure", False),
    "BR_tundra":      ("BROCHURE_toyota_tundra.pdf", "brochure", False),
    "BR_hp":          ("BROCHURE_hp_printer.pdf", "brochure", False),
    "BR_toshiba":     ("BROCHURE_toshiba.pdf", "brochure", False),
}

JUDGMENT_MARKERS = ["winning argument", "court's reasoning", "operative directions", "judgements relied upon", "authorities relied upon"]
SUMMARY_MARKERS = ["executive summary", "key highlights"]


def read_pdf_text(path: Path) -> str:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(path.read_bytes()))
    return "\n".join((p.extract_text() or "") for p in reader.pages).strip()


def parse_snapshot(text: str):
    first = text.lstrip().split("\n", 1)[0].strip()
    if first.startswith("SNAPSHOT:"):
        try:
            return json.loads(first[len("SNAPSHOT:"):])
        except Exception:
            return {"_parse_error": first[:120]}
    return {"_no_snapshot": first[:120]}


MODEL_ALIASES = {
    "gpt-5.2": ModelType("gpt-5.2"),
    "gpt-5.4-mini": ModelType("gpt-5.4-mini"),
    "gpt-5.5": ModelType("gpt-5.5"),
}
RUN_MODEL = ModelType(READABLE_MODEL.value)


async def run_one(llm, safe_text: str) -> str:
    user_prompt = READABLE_USER_TEMPLATE.format(document_text=safe_text[:80_000])
    chunks = []
    async for chunk in llm.call_completion_stream(
        system_prompt=READABLE_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        model=RUN_MODEL,
        temperature=0.0,
        max_tokens=6000,
        firm_id=None,
    ):
        chunks.append(chunk)
    return "".join(chunks)


async def main(labels):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    llm = get_llm_service()
    rows = []

    for label in labels:
        fname, category, expect_jud = CORPUS[label]
        path = PDF_DIR / fname
        if not path.exists():
            print(f"  {label}: MISSING FILE {fname}")
            rows.append((label, category, "MISSING", "-", "-", "-"))
            continue
        safe = sanitise_document_text(read_pdf_text(path))
        print(f"  running {label} ({category}, {len(safe)} chars) ...", end="", flush=True)
        t0 = time.perf_counter()
        try:
            out = await run_one(llm, safe)
        except Exception as exc:
            print(f" FAILED: {str(exc)[:80]}")
            rows.append((label, category, "ERROR", "-", "-", str(exc)[:60]))
            continue
        dt = time.perf_counter() - t0
        (OUT_DIR / f"{label}.md").write_text(out, encoding="utf-8")

        snap = parse_snapshot(out)
        doc_type = snap.get("document_type", "?")
        low = out.lower()
        has_jud = any(m in low for m in JUDGMENT_MARKERS)
        has_sum = any(m in low for m in SUMMARY_MARKERS)
        # routing correctness
        if expect_jud:
            routing = "OK" if has_jud else "MISS(no judgment sections)"
        else:
            routing = "OK" if (has_sum and not has_jud) else (
                "WARN(judgment sections leaked)" if has_jud else "OK(no-jud)")
        print(f" {dt:.0f}s  type={doc_type!r}  routing={routing}")
        rows.append((label, category, doc_type, "J" if has_jud else "-", "S" if has_sum else "-", routing))

    print("\n" + "=" * 100)
    hdr = f"{'LABEL':<16}{'CATEGORY':<16}{'DETECTED_TYPE':<28}{'JUD':<4}{'SUM':<4}ROUTING"
    print(hdr)
    out_lines = [hdr]
    for r in rows:
        line = f"{r[0]:<16}{r[1]:<16}{str(r[2]):<28}{r[3]:<4}{r[4]:<4}{r[5]}"
        print(line)
        out_lines.append(line)
    (OUT_DIR / "_verify_summary.txt").write_text("\n".join(out_lines), encoding="utf-8")
    print(f"\nOutputs + summary in: {OUT_DIR}")


if __name__ == "__main__":
    model_args = [a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("model=")]
    if model_args and model_args[0] in MODEL_ALIASES:
        RUN_MODEL = MODEL_ALIASES[model_args[0]]
    print(f"[verify] using model: {RUN_MODEL.value}")
    args = [a for a in sys.argv[1:] if a in CORPUS]
    labels = args if args else list(CORPUS.keys())
    asyncio.run(main(labels))
