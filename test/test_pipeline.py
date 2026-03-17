"""
test/test_pipeline.py

Runs the full simulation pipeline for a single quarter end-to-end.
This is the integration test — it exercises every prompt and the
voting engine together in sequence.

Makes ~15-20 API calls (10 Prompt D + up to 10 Prompt A + 1 Prompt B).

Usage:
    python test/test_pipeline.py                   # runs FY23Q1
    python test/test_pipeline.py --quarter FY23Q2  # runs a specific quarter

What it validates:
  - All 10 agents return valid proposals
  - All proposed actions are in the ActionLibrary
  - Effect prediction returns valid [-3,+3] dicts
  - Voting engine produces a FinalDecisionScore for every action
  - At least one action passes the vote
  - Prompt B returns a valid updated CompanyState
  - Results log is written to results/
"""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DATA_PROCESSED, RESULTS_DIR, SIMULATION_QUARTERS
from sim.action_library import ALL_ACTION_NAMES
from sim.pipeline import run_quarter


EXPECTED_STATE_KEYS = {"quarter", "Financials", "Segments", "Human_Impacts",
                       "Growth_Signals", "Market_Signals"}
EXPECTED_FINANCIALS_KEYS = {"revenue", "cost_of_revenue", "gross_margin",
                             "operating_income", "net_income",
                             "cash_and_equivalents", "total_operating_expenses",
                             "rd_spending", "sales_marketing_spending", "capex"}


def validate_log(log, quarter: str) -> bool:
    ok = True

    # Proposals
    if len(log.proposals) != 10:
        print(f"  ✗ Expected 10 agent proposals, got {len(log.proposals)}")
        ok = False
    else:
        print(f"  ✓ All 10 agents proposed actions")

    bad_actions = [
        a for actions in log.proposals.values()
        for a in actions if a not in ALL_ACTION_NAMES
    ]
    if bad_actions:
        print(f"  ✗ Actions not in ActionLibrary: {bad_actions}")
        ok = False
    else:
        print(f"  ✓ All proposed actions are valid ActionLibrary entries")

    # Effects
    if not log.effects:
        print(f"  ✗ No effects computed")
        ok = False
    else:
        bad_effects = {
            k: {var: v for var, v in eff.items()
                if not isinstance(v, int) or not (-3 <= v <= 3)}
            for k, eff in log.effects.items()
        }
        bad_effects = {k: v for k, v in bad_effects.items() if v}
        if bad_effects:
            print(f"  ✗ Out-of-range effect values: {bad_effects}")
            ok = False
        else:
            print(f"  ✓ All effect values valid for {len(log.effects)} actions")

    # Voting
    if not log.action_results:
        print(f"  ✗ No action results from voting engine")
        ok = False
    else:
        passed = [r for r in log.action_results if r["passed"]]
        print(f"  ✓ Voting complete: {len(passed)}/{len(log.action_results)} actions passed")

    # Approved actions
    if not log.approved_actions:
        print(f"  ✗ No actions approved — simulation produced no decisions")
        ok = False
    else:
        print(f"  ✓ Approved actions: {log.approved_actions}")

    # End state
    end_state = log.company_state_end
    missing_keys = EXPECTED_STATE_KEYS - set(end_state.keys())
    if missing_keys:
        print(f"  ✗ End state missing keys: {missing_keys}")
        ok = False
    else:
        print(f"  ✓ End state has all required top-level keys")

    missing_fin = EXPECTED_FINANCIALS_KEYS - set(end_state.get("Financials", {}).keys())
    if missing_fin:
        print(f"  ✗ End state Financials missing: {missing_fin}")
        ok = False
    else:
        end_rev = end_state.get("Financials", {}).get("revenue", 0)
        start_rev = log.company_state_start.get("Financials", {}).get("revenue", 0)
        print(f"  ✓ Revenue: {start_rev:,.0f}M → {end_rev:,.0f}M")

    # Log file
    log_path = RESULTS_DIR / f"{quarter}_simulation_log.json"
    if log_path.exists():
        print(f"  ✓ Log written → {log_path.name}")
    else:
        print(f"  ✗ Log file not found: {log_path}")
        ok = False

    return ok


def main():
    parser = argparse.ArgumentParser(description="Test full simulation pipeline")
    parser.add_argument("--quarter", type=str, default="FY23Q1",
                        choices=SIMULATION_QUARTERS,
                        help="Quarter to simulate (default: FY23Q1)")
    args = parser.parse_args()

    # Check CompanyState exists
    state_path = DATA_PROCESSED / f"{args.quarter}_company_state.json"
    if not state_path.exists():
        print(f"✗ CompanyState not found: {state_path}")
        print(f"  Run: python main.py  to generate it first.")
        sys.exit(1)

    print(f"\nPipeline Test — {args.quarter}")
    print("=" * 60)
    print(f"  This will make ~15-20 API calls. Press Ctrl+C to abort.\n")

    log = run_quarter(args.quarter, verbose=True)

    print(f"\n{'─' * 60}")
    print(f"  Validating results...")
    print(f"{'─' * 60}")
    passed = validate_log(log, args.quarter)

    print(f"\n{'=' * 60}")
    print(f"  {'PASSED' if passed else 'FAILED'}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()