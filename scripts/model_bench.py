"""
Ad-hoc model benchmark for the PDF Extractor readable briefing.

Runs the REAL readable prompt (READABLE_SYSTEM_PROMPT / READABLE_USER_TEMPLATE)
through the REAL LLMService streaming path, across multiple models and samples,
on multiple PDFs. Captures time-to-first-token, total time, word count, and the
full output for manual quality comparison.

Not part of the app — a one-off evaluation tool. Run from repo root:
    python scripts/model_bench.py
"""
import asyncio
import io
import time
import sys
from pathlib import Path

# Ensure repo root on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.services.llm_service import get_llm_service, ModelType
from backend.services.prompts.pdf_extractor import (
    READABLE_SYSTEM_PROMPT,
    READABLE_USER_TEMPLATE,
)
from backend.core.sanitiser import sanitise_document_text

PDF_DIR = Path(r"D:\NISHANT\test-pdfs")
PDFS = {
    "MANIK_KHURANA": "CWP-No.-39633-OF-2025-(MANIK-KHURANA-VERSUS-THE-CENTRAL-ADMINISTRATIVE-TRIBUNAL-AND-OTHERS).pdf",
    "JASSAR": "Jassar display_pdf.pdf",
}

MODELS = {
    "gpt-5.4-mini": ModelType.GPT54_MINI,
}

SAMPLES = 3
OUT_DIR = Path(__file__).resolve().parent / "bench_out"


def read_pdf_text(path: Path) -> str:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(path.read_bytes()))
    pages = [p.extract_text() or "" for p in reader.pages]
    return "\n".join(pages).strip()


async def run_one(llm, model_enum, safe_text: str):
    user_prompt = READABLE_USER_TEMPLATE.format(document_text=safe_text[:80_000])
    t0 = time.perf_counter()
    ttft = None
    chunks = []
    async for chunk in llm.call_completion_stream(
        system_prompt=READABLE_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        model=model_enum,
        temperature=0.0,
        max_tokens=6000,
        firm_id=None,
    ):
        if ttft is None:
            ttft = time.perf_counter() - t0
        chunks.append(chunk)
    total = time.perf_counter() - t0
    text = "".join(chunks)
    return {
        "ttft": ttft or total,
        "total": total,
        "words": len(text.split()),
        "text": text,
    }


def snapshot_line(text: str) -> str:
    first = text.lstrip().split("\n", 1)[0]
    return first[:200]


async def main():
    OUT_DIR.mkdir(exist_ok=True)
    llm = get_llm_service()

    summary_rows = []

    for pdf_label, fname in PDFS.items():
        path = PDF_DIR / fname
        raw = read_pdf_text(path)
        safe_text = sanitise_document_text(raw)
        print(f"\n{'='*70}\nPDF: {pdf_label}  ({len(raw)} chars extracted)\n{'='*70}")

        for model_label, model_enum in MODELS.items():
            for s in range(1, SAMPLES + 1):
                tag = f"{pdf_label}__{model_label}__s{s}"
                print(f"  running {tag} ...", end="", flush=True)
                try:
                    r = await run_one(llm, model_enum, safe_text)
                except Exception as exc:
                    print(f" FAILED: {exc}")
                    summary_rows.append((pdf_label, model_label, s, "ERR", "ERR", "ERR", str(exc)[:60]))
                    continue
                out_file = OUT_DIR / f"{tag}.md"
                out_file.write_text(r["text"], encoding="utf-8")
                print(f" ttft={r['ttft']:.1f}s total={r['total']:.1f}s words={r['words']}")
                summary_rows.append((
                    pdf_label, model_label, s,
                    f"{r['ttft']:.1f}", f"{r['total']:.1f}", r["words"],
                    snapshot_line(r["text"]),
                ))

    # Write summary
    print(f"\n{'='*70}\nSUMMARY\n{'='*70}")
    header = f"{'PDF':<14}{'MODEL':<14}{'#':<3}{'TTFT':<7}{'TOTAL':<8}{'WORDS':<7}SNAPSHOT"
    print(header)
    lines = [header]
    for row in summary_rows:
        line = f"{row[0]:<14}{row[1]:<14}{str(row[2]):<3}{str(row[3]):<7}{str(row[4]):<8}{str(row[5]):<7}{str(row[6])[:80]}"
        print(line)
        lines.append(line)
    (OUT_DIR / "_summary.txt").write_text("\n".join(lines), encoding="utf-8")
    print(f"\nFull outputs + summary written to: {OUT_DIR}")


if __name__ == "__main__":
    asyncio.run(main())
