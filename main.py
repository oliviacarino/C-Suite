"""
For every quarter in ALL_QUARTERS:
  1. Parse XLS/XLSX  → direct Financials + Segments values
  2. Parse DOCX/PPTX/PDF → plain text strings
  3. Call Prompt C (Claude) on available documents → derived fields
  4. Merge direct + derived into a CompanyState dict
  5. Write to data/processed/<QUARTER>_company_state.json

Usage:
    python main.py              # process all quarters (makes API calls)
    python main.py --dry-run    # parse files only, skip API calls
"""

from __future__ import annotations
import argparse
import json
import sys

import anthropic

from config import (
    ANTHROPIC_API_KEY, MODEL, MAX_TOKENS,
    DATA_PROCESSED, QUARTER_CONFIG, ALL_QUARTERS,
)
from util.parse_financials import parse_financials
from util.parse_qualitative import load_qualitative_docs
from prompts.prompt_c_derive_qualitative_data import build_prompt_c

# ── Anthropic helper ───────────────────────────────────────────────────────────

def _call_claude(prompt: dict) -> dict:
    """Send a prompt dict to Claude, return parsed JSON."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=prompt["system"],
        messages=[{"role": "user", "content": prompt["user"]}],
    )
    raw = response.content[0].text.strip()
    # Strip accidental markdown fences
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        raw = raw.rsplit("```", 1)[0]
    return json.loads(raw.strip())


# ── Financial file finder ──────────────────────────────────────────────────────

def _find_financial_file(quarter_dir):
    """Return the first XLS/XLSX file in quarter_dir, or None."""
    import re
    for f in sorted(quarter_dir.iterdir()):
        if f.is_file() and re.search(r"financial", f.name, re.IGNORECASE):
            return f
    # Fallback: any xlsx/xls in the directory
    for f in sorted(quarter_dir.iterdir()):
        if f.is_file() and f.suffix.lower() in (".xlsx", ".xls"):
            return f
    return None


# ── CompanyState builder ───────────────────────────────────────────────────────

def build_company_state(quarter: str, financials: dict, derived: dict | None) -> dict:
    """
    Merge direct financial data and Claude-derived qualitative data into a
    single CompanyState dict.

    total_employees is not available in quarterly earnings files — set it
    manually in the output JSON, or add it to config.py as a lookup dict.
    """
    hi = (derived or {}).get("Human_Impacts", {})
    gs = (derived or {}).get("Growth_Signals", {})
    ms = (derived or {}).get("Market_Signals", {})

    return {
        "quarter": quarter,
        "Financials": {
            "revenue":                  financials.get("revenue", 0.0),
            "cost_of_revenue":          financials.get("cost_of_revenue", 0.0),
            "gross_margin":             financials.get("gross_margin", 0.0),
            "operating_income":         financials.get("operating_income", 0.0),
            "net_income":               financials.get("net_income", 0.0),
            "cash_and_equivalents":     financials.get("cash_and_equivalents", 0.0),
            "total_operating_expenses": financials.get("total_operating_expenses", 0.0),
            "rd_spending":              financials.get("rd_spending", 0.0),
            "sales_marketing_spending": financials.get("sales_marketing_spending", 0.0),
            "capex":                    financials.get("capex", 0.0),
        },
        "Segments": {
            "productivity_revenue":        financials.get("productivity_revenue", 0.0),
            "intelligent_cloud_revenue":   financials.get("intelligent_cloud_revenue", 0.0),
            "personal_computing_revenue":  financials.get("personal_computing_revenue", 0.0),
        },
        "Human_Impacts": {
            "total_employees":        TOTAL_EMPLOYEES.get(quarter, 0),  
            "hiring_freeze":          hi.get("hiring_freeze", False),
            "layoffs_this_quarter":   hi.get("layoffs_this_quarter", False),
            "engineering_headcount":  hi.get("engineering_headcount"),
            "sales_headcount":        hi.get("sales_headcount"),
        },
        "Growth_Signals": {
            "ai_investment_focus":  gs.get("ai_investment_focus", 5),
            "innovation_index":     gs.get("innovation_index", 5),
            "competitive_pressure": gs.get("competitive_pressure", 5),
            "regulatory_pressure":  gs.get("regulatory_pressure", 5),
            "brand_strength":       gs.get("brand_strength", 5),
        },
        "Market_Signals": {
            "investor_sentiment": ms.get("investor_sentiment", 5),
            "growth_expectation": ms.get("growth_expectation", 5),
            "stock_price":        None,
        },
        "derivation_notes": (derived or {}).get("derivation_notes", {}),
    }


# ── Per-quarter processing ─────────────────────────────────────────────────────

def process_quarter(quarter: str, dry_run: bool = False) -> bool:
    """
    Full parse → derive → merge → write flow for one quarter.
    Returns True on success.
    """
    quarter_dir = QUARTER_CONFIG.get(quarter, {}).get("quarter_dir")

    if not quarter_dir or not quarter_dir.exists():
        print(f"  [SKIP] directory not found: {quarter_dir}")
        return False

    # ── Step 1: Parse financial file ──────────────────────────────────────────
    fin_path = _find_financial_file(quarter_dir)
    if fin_path:
        financials = parse_financials(fin_path)
        print(f"  Financials ({fin_path.name}):")
        print(f"    revenue={financials.get('revenue', 0):>12,.0f}  "
              f"rd={financials.get('rd_spending', 0):>10,.0f}  "
              f"cash={financials.get('cash_and_equivalents', 0):>12,.0f}")
    else:
        financials = {}
        print(f"  Financials: no XLS/XLSX found in {quarter_dir}")

    # ── Step 2: Parse qualitative documents ───────────────────────────────────
    performance_dir = QUARTER_CONFIG.get(quarter, {}).get("performance_dir")
    docs = load_qualitative_docs(quarter_dir, performance_dir)
    found = [k for k, v in docs.items() if v]
    missing = [k for k, v in docs.items() if not v]
    print(f"  Documents found:   {found if found else 'none'}")
    if missing:
        print(f"  Documents missing: {missing}")

    if dry_run:
        print(f"  [dry-run] Skipping Prompt C.\n")
        state = build_company_state(quarter, financials, derived=None)
        out_path = DATA_PROCESSED / f"{quarter}_company_state.json"
        out_path.write_text(json.dumps(state, indent=2))
        print(f"  Written (stub) → {out_path.name}\n")
        return True

    # ── Step 3: Run Prompt C ──────────────────────────────────────────────────
    available_docs = {k: v for k, v in docs.items() if v}
    if not available_docs:
        print(f"  No documents available — skipping Prompt C.")
        derived = None
    else:
        print(f"  Calling Prompt C...")
        prompt = build_prompt_c(quarter, available_docs)
        derived = _call_claude(prompt)
        hi = derived.get("Human_Impacts", {})
        gs = derived.get("Growth_Signals", {})
        ms = derived.get("Market_Signals", {})
        print(f"  Derived:")
        print(f"    hiring_freeze={hi.get('hiring_freeze')}  "
              f"layoffs={hi.get('layoffs_this_quarter')}")
        print(f"    ai_focus={gs.get('ai_investment_focus')}  "
              f"innovation={gs.get('innovation_index')}  "
              f"competition={gs.get('competitive_pressure')}")
        print(f"    sentiment={ms.get('investor_sentiment')}  "
              f"growth_exp={ms.get('growth_expectation')}")

    # ── Step 4: Merge and write ───────────────────────────────────────────────
    state = build_company_state(quarter, financials, derived)
    out_path = DATA_PROCESSED / f"{quarter}_company_state.json"
    out_path.write_text(json.dumps(state, indent=2))
    print(f"  Written → {out_path.name}\n")
    return True


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="C-Suite parsing phase")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Parse files and print findings — no API calls",
    )
    args = parser.parse_args()

    if not args.dry_run and not ANTHROPIC_API_KEY:
        print("Error: ANTHROPIC_API_KEY not set. Add it to your .env file.")
        sys.exit(1)

    mode = "DRY RUN — no API calls" if args.dry_run else "FULL RUN"
    print(f"\nC-Suite Parse [{mode}]")
    print(f"Output: {DATA_PROCESSED}\n")
    print("=" * 60)

    success = 0
    for quarter in ALL_QUARTERS:
        print(f"\n[{quarter}]")
        if process_quarter(quarter, dry_run=args.dry_run):
            success += 1

    print("=" * 60)
    print(f"\nDone. {success}/{len(ALL_QUARTERS)} quarters written to {DATA_PROCESSED}")


if __name__ == "__main__":
    main()