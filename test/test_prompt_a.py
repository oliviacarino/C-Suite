"""
test/test_prompt_a.py

Tests Prompt A against a handful of actions using your real FY22Q4
CompanyState JSON. Makes one API call per action tested.

Usage:
    python test/test_prompt_a.py                        # tests 3 default actions
    python test/test_prompt_a.py --action increase_rd_5 # test one specific action
    python test/test_prompt_a.py --all                  # tests all 30 actions

What it checks:
  - Response is valid JSON
  - All 25 effect variables are present
  - All effect values are integers in [-3, +3]
  - Rationale field is non-empty
  - Effects are directionally sensible (sanity checks on known actions)
"""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import anthropic
from config import ANTHROPIC_API_KEY, MODEL, MAX_TOKENS, DATA_PROCESSED
from sim.action_library import ALL_ACTION_NAMES
from prompts.prompt_a_effect_prediction import build_prompt_a

EXPECTED_EFFECT_KEYS = {
    "revenue", "cost_of_revenue", "gross_margin", "operating_income",
    "net_income", "cash_and_equivalents", "total_operating_expenses",
    "rd_spending", "sales_marketing_spending", "capex",
    "productivity_revenue", "intelligent_cloud_revenue",
    "personal_computing_revenue", "total_employees", "hiring_freeze",
    "layoffs_this_quarter", "engineering_headcount", "sales_headcount",
    "ai_investment_focus", "innovation_index", "competitive_pressure",
    "regulatory_pressure", "brand_strength", "investor_sentiment",
    "growth_expectation",
}

# Sanity checks: for known actions, assert certain effects point the right way.
# Format: action_name → {variable: expected_sign}
# expected_sign: +1 means effect should be > 0, -1 means < 0, 0 means == 0
SANITY_CHECKS: dict[str, dict[str, int]] = {
    "increase_rd_5": {
        "rd_spending":          +1,
        "cash_and_equivalents": -1,
        "innovation_index":     +1,
    },
    "increase_rd_10": {
        "rd_spending":          +1,
        "cash_and_equivalents": -1,
        "innovation_index":     +1,
    },
    "freeze_hiring": {
        "total_employees":          -1,
        "total_operating_expenses": -1,
    },
    "layoff_5_percent": {
        "total_employees":      -1,
        "brand_strength":       -1,
    },
    "increase_marketing_10": {
        "sales_marketing_spending": +1,
        "brand_strength":           +1,
    },
    "stock_buyback_program": {
        "cash_and_equivalents": -1,
    },
    "expand_enterprise_sales": {
        "revenue":       +1,
        "sales_headcount": +1,
    },
}

# Default actions to test (covers a spread of categories)
DEFAULT_ACTIONS = [
    "increase_rd_5",
    "layoff_5_percent",
    "expand_enterprise_sales",
]


def call_claude(prompt: dict) -> dict:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=prompt["system"],
        messages=[{"role": "user", "content": prompt["user"]}],
    )
    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        raw = raw.rsplit("```", 1)[0]
    return json.loads(raw.strip())


def load_state(quarter: str) -> dict:
    path = DATA_PROCESSED / f"{quarter}_company_state.json"
    if not path.exists():
        print(f"  ✗ CompanyState not found: {path}")
        print(f"    Run: python main.py")
        sys.exit(1)
    return json.loads(path.read_text())


def test_action(action_name: str, state: dict) -> bool:
    print(f"\n  [{action_name}]")
    print(f"  Calling Claude... ", end="", flush=True)

    prompt = build_prompt_a(state, action_name)
    result = call_claude(prompt)
    print("done")

    ok = True
    effects = result.get("effects", {})

    # Check all 25 keys present
    missing = EXPECTED_EFFECT_KEYS - set(effects.keys())
    if missing:
        print(f"  ✗ Missing effect keys: {missing}")
        ok = False
    else:
        print(f"  ✓ All 25 effect variables present")

    # Check all values are ints in [-3, +3]
    bad_values = {
        k: v for k, v in effects.items()
        if not isinstance(v, int) or not (-3 <= v <= 3)
    }
    if bad_values:
        print(f"  ✗ Out-of-range or non-int values: {bad_values}")
        ok = False
    else:
        print(f"  ✓ All values are integers in [-3, +3]")

    # Rationale check
    rationale = result.get("rationale", "")
    if not rationale or len(rationale.strip()) < 20:
        print(f"  ✗ Rationale missing or too short")
        ok = False
    else:
        print(f"  ✓ Rationale: {rationale[:120]}...")

    # Sanity checks for known actions
    if action_name in SANITY_CHECKS:
        checks = SANITY_CHECKS[action_name]
        for var, expected_sign in checks.items():
            actual = effects.get(var, 0)
            if expected_sign == +1 and actual <= 0:
                print(f"  ✗ Sanity: {var} should be positive, got {actual}")
                ok = False
            elif expected_sign == -1 and actual >= 0:
                print(f"  ✗ Sanity: {var} should be negative, got {actual}")
                ok = False
            else:
                print(f"  ✓ Sanity: {var} = {actual:+d} (expected {'positive' if expected_sign > 0 else 'negative'})")

    # Print non-zero effects for inspection
    non_zero = {k: v for k, v in effects.items() if v != 0}
    print(f"  Non-zero effects ({len(non_zero)}): {non_zero}")

    return ok


def main():
    parser = argparse.ArgumentParser(description="Test Prompt A — effect prediction")
    parser.add_argument("--action", type=str, default=None,
                        help="Specific action to test (e.g. increase_rd_5)")
    parser.add_argument("--all", action="store_true",
                        help="Test all 30 actions (30 API calls)")
    parser.add_argument("--quarter", type=str, default="FY22Q4",
                        help="Which CompanyState JSON to use (default: FY22Q4)")
    args = parser.parse_args()

    if not ANTHROPIC_API_KEY:
        print("Error: ANTHROPIC_API_KEY not set.")
        sys.exit(1)

    state = load_state(args.quarter)
    print(f"\nPrompt A Test — quarter={args.quarter}")
    print(f"Revenue: {state.get('Financials', {}).get('revenue', 0):,.0f}M")
    print("=" * 55)

    if args.all:
        actions_to_test = ALL_ACTION_NAMES
    elif args.action:
        if args.action not in ALL_ACTION_NAMES:
            print(f"Unknown action: '{args.action}'")
            print(f"Valid actions: {ALL_ACTION_NAMES}")
            sys.exit(1)
        actions_to_test = [args.action]
    else:
        actions_to_test = DEFAULT_ACTIONS

    results = []
    for action in actions_to_test:
        passed = test_action(action, state)
        results.append((action, passed))

    print(f"\n{'=' * 55}")
    passed_count = sum(1 for _, p in results if p)
    print(f"  {passed_count}/{len(results)} actions passed")
    for action, passed in results:
        status = "✓" if passed else "✗"
        print(f"  {status}  {action}")


if __name__ == "__main__":
    main()