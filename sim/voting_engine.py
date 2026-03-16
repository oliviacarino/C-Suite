"""
simulation/voting_engine.py

Implements the full AES → vote direction → AWS → FinalDecisionScore pipeline.

Flow for each proposed action a:
  For each AIE agent:
    1. compute_aes()         → signed float (how much this agent likes action a)
    2. vote_direction()      → +1 YES / -1 NO / 0 abstain (sign of AES)
    3. compute_vote_weight() → VoteDirection × (1 + DomainBonus if in domain)
  sum all vote weights       → FinalDecisionScore
  if score > THRESHOLD       → action passes

AES_CATEGORY_VARIABLES maps each of the 7 AES weight categories to the
CompanyState variable names whose Effect values are summed for that category.
These must match the keys returned by Prompt A's effects dict.
"""

from __future__ import annotations
from dataclasses import dataclass, field

from agents.board import AIEAgent
from config import DECISION_THRESHOLD, TOP_K_ACTIONS


# Maps AES weight category → CompanyState variable names included in that group.
# All variables listed here must appear in Prompt A's effects output.
AES_CATEGORY_VARIABLES: dict[str, list[str]] = {
    "revenue": [
        "revenue", "gross_margin", "operating_income", "net_income",
        "productivity_revenue", "intelligent_cloud_revenue",
        "personal_computing_revenue", "sales_headcount",
        "competitive_pressure", "investor_sentiment",
        "growth_expectation",
    ],
    "operating_cost": [
        "cost_of_revenue", "total_operating_expenses", "regulatory_pressure",
    ],
    "cash_reserves": [
        "cash_and_equivalents",
    ],
    "headcount": [
        "total_employees", "hiring_freeze", "layoffs_this_quarter",
    ],
    "rd_investment": [
        "rd_spending", "engineering_headcount",
    ],
    "brand_strength": [
        "sales_marketing_spending", "brand_strength",
    ],
    "innovation_index": [
        "ai_investment_focus", "innovation_index", "capex",
    ],
}


@dataclass
class AgentVote:
    agent_title:    str
    aes_score:      float
    vote_direction: int    # +1, -1, or 0
    in_domain:      bool
    domain_bonus:   int    # 0 or agent.domain_bonus (2)
    vote_weight:    float  # VoteDirection × (1 + domain_bonus)


@dataclass
class ActionResult:
    action:               str
    agent_votes:          list[AgentVote] = field(default_factory=list)
    final_decision_score: float           = 0.0
    passed:               bool            = False


# ── Core math functions ────────────────────────────────────────────────────────

def compute_aes(agent: AIEAgent, effects: dict[str, int]) -> float:
    """
    AES_agent(a) = Σ w_agent,i × Effect_i(a)

    For each of the 7 AES categories, sums the Effect values of all
    CompanyState variables in that category, then multiplies by the
    agent's weight for that category.
    """
    score = 0.0
    weights = {
        "revenue":          agent.aes_weights.revenue,
        "operating_cost":   agent.aes_weights.operating_cost,
        "cash_reserves":    agent.aes_weights.cash_reserves,
        "headcount":        agent.aes_weights.headcount,
        "rd_investment":    agent.aes_weights.rd_investment,
        "brand_strength":   agent.aes_weights.brand_strength,
        "innovation_index": agent.aes_weights.innovation_index,
    }
    for category, variable_names in AES_CATEGORY_VARIABLES.items():
        category_effect = sum(effects.get(var, 0) for var in variable_names)
        score += weights[category] * category_effect
    return score


def vote_direction(aes_score: float) -> int:
    """Derive YES/NO/abstain from the sign of the AES score."""
    if aes_score > 0:
        return +1
    elif aes_score < 0:
        return -1
    return 0


def compute_vote_weight(direction: int, in_domain: bool, bonus: int) -> float:
    """
    VoteWeight = VoteDirection × (1 + DomainBonus)

    Domain bonus only applies when action's primary category matches
    the agent's primary domain. A domain-expert YES = +3, NO = -3.
    A non-domain YES = +1, NO = -1.
    """
    applied_bonus = bonus if in_domain else 0
    return direction * (1 + applied_bonus)


# ── Per-action scoring ─────────────────────────────────────────────────────────

def score_action(
    action_name: str,
    action_primary_category: str,
    effects: dict[str, int],
    board: list[AIEAgent],
) -> ActionResult:
    """
    Run the full AES → vote → AWS pipeline for one action across all agents.
    Returns an ActionResult with per-agent votes and the final decision score.
    """
    result = ActionResult(action=action_name)

    for agent in board:
        aes   = compute_aes(agent, effects)
        dir_  = vote_direction(aes)
        in_dm = (agent.primary_domain == action_primary_category)
        bonus = agent.domain_bonus if in_dm else 0
        wt    = compute_vote_weight(dir_, in_dm, agent.domain_bonus)

        result.agent_votes.append(AgentVote(
            agent_title=agent.title,
            aes_score=aes,
            vote_direction=dir_,
            in_domain=in_dm,
            domain_bonus=bonus,
            vote_weight=wt,
        ))
        result.final_decision_score += wt

    result.passed = result.final_decision_score > DECISION_THRESHOLD
    return result


def select_top_actions(action_results: list[ActionResult]) -> list[ActionResult]:
    """
    From all passing actions, return the top K by FinalDecisionScore.
    K is defined in config.TOP_K_ACTIONS (default 5).
    """
    passing = [r for r in action_results if r.passed]
    passing.sort(key=lambda r: r.final_decision_score, reverse=True)
    return passing[:TOP_K_ACTIONS]