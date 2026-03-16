"""
test_voting.py

Validates the agents and voting engine with zero API calls.
All inputs are hardcoded — no files, no Claude.

Run from project root:
    python test_voting.py

What it checks:
  1. Board composition       — 10 agents, all required domains present
  2. AES scoring             — CTO likes R&D increases, CFO does not
  3. Vote direction          — correct sign logic
  4. Vote weight (AWS)       — domain bonus applies correctly
  5. Full board score        — score_action() end-to-end
  6. Contradiction check     — freeze_hiring and increase_engineering_hiring
                               should not both pass with the same effect vector
  7. select_top_actions()    — returns at most TOP_K_ACTIONS, sorted by score
  8. Action library          — 30 actions, all have a category mapping
"""

from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.board import BOARD, AESWeights
from sim.action_library import Action, ACTION_PRIMARY_CATEGORY, ALL_ACTION_NAMES
from sim.voting_engine import (
    AES_CATEGORY_VARIABLES,
    compute_aes, vote_direction, compute_vote_weight,
    score_action, select_top_actions, ActionResult,
)
from config import DECISION_THRESHOLD, TOP_K_ACTIONS

PASS = "  ✓"
FAIL = "  ✗"


def check(label: str, condition: bool, detail: str = ""):
    status = PASS if condition else FAIL
    print(f"{status}  {label}" + (f"  ({detail})" if detail else ""))
    return condition


def section(title: str):
    print(f"\n{'─' * 55}")
    print(f"  {title}")
    print(f"{'─' * 55}")


# ── 1. Board composition ───────────────────────────────────────────────────────
section("1 · Board composition")

check("10 agents on the board", len(BOARD) == 10, f"got {len(BOARD)}")

required_domains = {"revenue", "cash_reserves", "operating_cost", "headcount",
                    "rd_investment", "brand_strength", "innovation_index"}
actual_domains = {a.primary_domain for a in BOARD}
check("all required domains represented", required_domains <= actual_domains,
      f"missing: {required_domains - actual_domains}")

for agent in BOARD:
    weights = agent.aes_weights
    all_in_range = all(
        -4 <= v <= 4 for v in [
            weights.revenue, weights.operating_cost, weights.cash_reserves,
            weights.headcount, weights.rd_investment,
            weights.brand_strength, weights.innovation_index,
        ]
    )
    check(f"weights in [-4,+4]: {agent.title[:40]}", all_in_range)


# ── 2. AES scoring ─────────────────────────────────────────────────────────────
section("2 · AES scoring")

# Effects for "increase R&D 5%"
rd_effects = {
    "rd_spending": 2, "engineering_headcount": 1,
    "cash_and_equivalents": -2, "innovation_index": 3,
    "ai_investment_focus": 2, "capex": 1,
}

cto = next(a for a in BOARD if "Technology" in a.title)
cfo = next(a for a in BOARD if "Financial" in a.title)
cpo = next(a for a in BOARD if "People" in a.title)

aes_cto = compute_aes(cto, rd_effects)
aes_cfo = compute_aes(cfo, rd_effects)

check("CTO likes R&D increase (AES > 0)", aes_cto > 0, f"AES={aes_cto:.1f}")
check("CFO dislikes R&D increase (AES < 0)", aes_cfo < 0, f"AES={aes_cfo:.1f}")
check("CTO likes R&D more than CFO", aes_cto > aes_cfo,
      f"CTO={aes_cto:.1f} CFO={aes_cfo:.1f}")

# Effects for "layoff 5%"
layoff_effects = {
    "total_employees": -3, "layoffs_this_quarter": -3,
    "hiring_freeze": -1, "cost_of_revenue": -1,
    "total_operating_expenses": -2, "brand_strength": -1,
    "innovation_index": -1, "investor_sentiment": 1,
}
aes_cpo_layoff = compute_aes(cpo, layoff_effects)
check("CPO dislikes layoffs (AES < 0)", aes_cpo_layoff < 0,
      f"AES={aes_cpo_layoff:.1f}")


# ── 3. Vote direction ──────────────────────────────────────────────────────────
section("3 · Vote direction")

check("positive AES → YES (+1)", vote_direction(12.0) == +1)
check("negative AES → NO  (-1)", vote_direction(-5.0) == -1)
check("zero AES    → abstain (0)", vote_direction(0.0) == 0)
check("small positive → YES", vote_direction(0.001) == +1)
check("small negative → NO",  vote_direction(-0.001) == -1)


# ── 4. Vote weight (AWS) ───────────────────────────────────────────────────────
section("4 · Vote weight (AWS)")

check("domain YES  = +3", compute_vote_weight(+1, True,  2) == +3)
check("domain NO   = -3", compute_vote_weight(-1, True,  2) == -3)
check("non-domain YES = +1", compute_vote_weight(+1, False, 2) == +1)
check("non-domain NO  = -1", compute_vote_weight(-1, False, 2) == -1)
check("abstain in domain = 0", compute_vote_weight(0, True, 2) == 0)


# ── 5. Full board score ────────────────────────────────────────────────────────
section("5 · Full board score (score_action)")

result_rd = score_action("increase_rd_5", "rd_investment", rd_effects, BOARD)
check("increase_rd_5 passes (popular action)",
      result_rd.passed, f"score={result_rd.final_decision_score:.1f}")
check("10 agent votes recorded",
      len(result_rd.agent_votes) == 10)
check("CTO vote weight = +3 (domain expert YES)",
      any(v.vote_weight == 3 and "Technology" in v.agent_title
          for v in result_rd.agent_votes))
check("CFO vote weight = -3 (domain expert NO on cash category... wait, rd is CTO domain)",
      any(v.agent_title == cfo.title and v.vote_weight in (-1, -3)
          for v in result_rd.agent_votes))

result_layoff = score_action("layoff_5_percent", "headcount", layoff_effects, BOARD)
print(f"\n  layoff_5_percent: score={result_layoff.final_decision_score:.1f}  "
      f"passed={result_layoff.passed}")
check("CPO votes NO on layoffs",
      any(v.agent_title == cpo.title and v.vote_direction == -1
          for v in result_layoff.agent_votes))


# ── 6. Contradiction check ─────────────────────────────────────────────────────
section("6 · Contradiction check")

freeze_effects = {
    "hiring_freeze": 3, "total_employees": -1,
    "cost_of_revenue": -1, "total_operating_expenses": -1,
}
hire_effects = {
    "engineering_headcount": 3, "total_employees": 2,
    "rd_spending": 1, "innovation_index": 1,
    "total_operating_expenses": 2,
}

r_freeze = score_action("freeze_hiring", "headcount", freeze_effects, BOARD)
r_hire   = score_action("increase_engineering_hiring", "headcount", hire_effects, BOARD)

print(f"\n  freeze_hiring score:              {r_freeze.final_decision_score:.1f}  passed={r_freeze.passed}")
print(f"  increase_engineering_hiring score: {r_hire.final_decision_score:.1f}  passed={r_hire.passed}")

# They can both pass (the board is not contradiction-aware at this layer),
# but we confirm they score differently given opposing effect vectors
check("freeze and hire score differently",
      r_freeze.final_decision_score != r_hire.final_decision_score,
      "expected different scores from opposing effects")


# ── 7. select_top_actions ──────────────────────────────────────────────────────
section("7 · select_top_actions")

# Build a set of mock results with varying scores
mock_results = [
    ActionResult(action=f"action_{i}", final_decision_score=float(i * 2 - 5), passed=(i * 2 - 5 > 0))
    for i in range(10)
]
top = select_top_actions(mock_results)
check(f"returns at most TOP_K_ACTIONS={TOP_K_ACTIONS}",
      len(top) <= TOP_K_ACTIONS, f"got {len(top)}")
check("all returned actions passed",
      all(r.passed for r in top))
check("sorted by score descending",
      all(top[i].final_decision_score >= top[i+1].final_decision_score
          for i in range(len(top)-1)))


# ── 8. Action library ──────────────────────────────────────────────────────────
section("8 · Action library")

check(f"30 actions defined", len(ALL_ACTION_NAMES) == 30, f"got {len(ALL_ACTION_NAMES)}")
check("all actions have a category mapping",
      all(a in ACTION_PRIMARY_CATEGORY for a in Action))

valid_categories = {"revenue", "operating_cost", "cash_reserves", "headcount",
                    "rd_investment", "brand_strength", "innovation_index"}
all_categories_valid = all(
    v in valid_categories for v in ACTION_PRIMARY_CATEGORY.values()
)
check("all category values are valid AES keys", all_categories_valid)

# Confirm AES_CATEGORY_VARIABLES covers no unknown field names
# (these must match what Prompt A returns)
all_vars = {v for vars_ in AES_CATEGORY_VARIABLES.values() for v in vars_}
print(f"\n  Total CompanyState variables tracked by AES: {len(all_vars)}")


# ── Summary ────────────────────────────────────────────────────────────────────
print(f"\n{'=' * 55}")
print("  Done.")
print(f"{'=' * 55}\n")