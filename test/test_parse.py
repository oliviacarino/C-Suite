"""
test_parse.py

Runs both parsers against your actual files and prints results.
No API calls. No CompanyState class required.

Usage:
    python test_parse.py              # test all quarters
    python test_parse.py FY22Q4       # test one quarter
    python test_parse.py FY23Q1 FY22Q4  # test specific quarters

What it checks:
  1. Financial parser  — prints all values, flags any that are 0.0
  2. Qualitative parser — confirms which documents were found and
                          prints the first 300 chars of each
"""

from __future__ import annotations
import sys
from pathlib import Path

# ── Make sure project root is on the path ─────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import QUARTER_CONFIG, ALL_QUARTERS
from util.parse_financials import parse_financials
from util.parse_qualitative import load_qualitative_docs


# ── Helpers ───────────────────────────────────────────────────────────────────

def _find_financial_file(quarter_dir: Path) -> Path | None:
    for f in sorted(quarter_dir.iterdir()):
        if f.is_file() and "financial" in f.name.lower() and f.suffix.lower() in (".xlsx", ".xls"):
            return f
    return None


def _flag(val: float) -> str:
    return "  ⚠ ZERO — check row label or sheet name" if val == 0.0 else ""


def test_financials(quarter: str, quarter_dir: Path):
    print(f"\n{'─' * 55}")
    print(f"  FINANCIALS — {quarter}")
    print(f"{'─' * 55}")

    fin_path = _find_financial_file(quarter_dir)
    if fin_path is None:
        print(f"  ✗ No financial XLSX found in {quarter_dir}")
        return

    print(f"  File: {fin_path.name}")
    result = parse_financials(fin_path)

    sections = {
        "Income Statement": [
            "revenue", "cost_of_revenue", "gross_margin",
            "operating_income", "net_income",
            "total_operating_expenses", "rd_spending",
            "sales_marketing_spending",
        ],
        "Balance Sheet / Cash Flow": [
            "cash_and_equivalents", "capex",
        ],
        "Segments": [
            "productivity_revenue",
            "intelligent_cloud_revenue",
            "personal_computing_revenue",
        ],
    }

    for section, keys in sections.items():
        print(f"\n  [{section}]")
        for k in keys:
            v = result.get(k, "MISSING")
            if isinstance(v, float) and v != int(v):
                formatted = f"{v:>12.2f}"
            else:
                formatted = f"{float(v):>12,.0f}" if v != "MISSING" else f"{'MISSING':>12}"
            unit = "%" if k == "gross_margin" else "M"
            print(f"    {k:<35} {formatted} {unit}{_flag(float(v) if v != 'MISSING' else 0.0)}")

    # Sanity checks
    print()
    rev = result.get("revenue", 0)
    prod = result.get("productivity_revenue", 0)
    cloud = result.get("intelligent_cloud_revenue", 0)
    pc = result.get("personal_computing_revenue", 0)
    seg_total = prod + cloud + pc

    if rev > 0 and abs(seg_total - rev) < 5:
        print(f"  ✓ Segment sum ({seg_total:,.0f}) matches total revenue ({rev:,.0f})")
    elif rev > 0:
        print(f"  ⚠ Segment sum ({seg_total:,.0f}) does NOT match total revenue ({rev:,.0f})")

    gm = result.get("gross_margin", 0)
    if 50 < gm < 90:
        print(f"  ✓ Gross margin {gm:.2f}% looks reasonable")
    else:
        print(f"  ⚠ Gross margin {gm:.2f}% — check calculation")


def test_qualitative(quarter: str, quarter_dir: Path, performance_dir: Path | None):
    print(f"\n{'─' * 55}")
    print(f"  QUALITATIVE DOCS — {quarter}")
    print(f"{'─' * 55}")

    docs = load_qualitative_docs(quarter_dir, performance_dir)

    found    = {k: v for k, v in docs.items() if v}
    missing  = [k for k, v in docs.items() if not v]

    print(f"  Found ({len(found)}):   {list(found.keys())}")
    print(f"  Missing ({len(missing)}): {missing}")

    for doc_type, text in found.items():
        char_count = len(text)
        word_count = len(text.split())
        preview = text[:300].replace("\n", " ").strip()
        print(f"\n  [{doc_type}]  {char_count:,} chars / {word_count:,} words")
        print(f"  Preview: {preview}...")


def test_quarter(quarter: str):
    cfg = QUARTER_CONFIG.get(quarter)
    if cfg is None:
        print(f"\n✗ Unknown quarter: {quarter}")
        print(f"  Valid quarters: {ALL_QUARTERS}")
        return

    quarter_dir     = cfg["quarter_dir"]
    performance_dir = cfg["performance_dir"]

    if not quarter_dir.exists():
        print(f"\n✗ Directory not found: {quarter_dir}")
        print(f"  Make sure your files are in the right place.")
        return

    test_financials(quarter, quarter_dir)
    test_qualitative(quarter, quarter_dir, performance_dir)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    quarters = sys.argv[1:] if len(sys.argv) > 1 else ALL_QUARTERS

    print("=" * 55)
    print("  C-Suite Parse Test")
    print("=" * 55)

    for q in quarters:
        test_quarter(q)

    print(f"\n{'=' * 55}")
    print("  Done.")
    print(f"{'=' * 55}")