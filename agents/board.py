"""
agents/board.py

Defines the AIEAgent dataclass and the full board of 10 agents.

Each agent has:
  - title:          exact C-suite title
  - primary_domain: the AES category they are a domain expert in
                    (matches a key in AESWeights AND ACTION_PRIMARY_CATEGORY)
  - role_archetype: prose description of their behavioral personality,
                    injected into Prompt D so Claude adopts the right lens
  - aes_weights:    role-priority weights per AES category (range -4 to +4)
                    positive = prefers increases in that category
                    negative = prefers decreases (e.g. CFO wants costs DOWN)
  - domain_bonus:   AWS bonus magnitude, always 2 per spec

AES category keys (must be consistent across board.py, action_library.py,
and voting_engine.py):
    revenue, operating_cost, cash_reserves, headcount,
    rd_investment, brand_strength, innovation_index

Which CompanyState variables map to each AES category is defined in
voting_engine.py (AES_CATEGORY_VARIABLES).
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass
class AESWeights:
    revenue:          int = 0
    operating_cost:   int = 0
    cash_reserves:    int = 0
    headcount:        int = 0
    rd_investment:    int = 0
    brand_strength:   int = 0
    innovation_index: int = 0


@dataclass
class AIEAgent:
    title:          str
    primary_domain: str
    role_archetype: str
    aes_weights:    AESWeights
    domain_bonus:   int = 2

    def top_weighted_variables(self) -> list[str]:
        """Return the top 3 AES categories by absolute weight."""
        weights = {
            "revenue":          self.aes_weights.revenue,
            "operating_cost":   self.aes_weights.operating_cost,
            "cash_reserves":    self.aes_weights.cash_reserves,
            "headcount":        self.aes_weights.headcount,
            "rd_investment":    self.aes_weights.rd_investment,
            "brand_strength":   self.aes_weights.brand_strength,
            "innovation_index": self.aes_weights.innovation_index,
        }
        return sorted(weights, key=lambda k: abs(weights[k]), reverse=True)[:3]


BOARD: list[AIEAgent] = [
    AIEAgent(
        title="Chairman & Chief Executive Officer",
        primary_domain="revenue",
        role_archetype=(
            "visionary and growth-oriented, balances long-term strategy with "
            "near-term execution, high risk tolerance"
        ),
        aes_weights=AESWeights(
            revenue=4, operating_cost=-1, cash_reserves=2,
            headcount=1, rd_investment=3, brand_strength=3, innovation_index=3,
        ),
    ),
    AIEAgent(
        title="Executive Vice President & Chief Financial Officer",
        primary_domain="cash_reserves",
        role_archetype=(
            "risk-sensitive and financially conservative, prioritizes liquidity "
            "and cost discipline over growth bets"
        ),
        aes_weights=AESWeights(
            revenue=2, operating_cost=-4, cash_reserves=4,
            headcount=-1, rd_investment=-1, brand_strength=1, innovation_index=1,
        ),
    ),
    AIEAgent(
        title="Vice Chair & President",
        primary_domain="brand_strength",
        role_archetype=(
            "governance-focused and reputation-conscious, weighs legal and "
            "regulatory risk heavily"
        ),
        aes_weights=AESWeights(
            revenue=2, operating_cost=-1, cash_reserves=2,
            headcount=1, rd_investment=1, brand_strength=3, innovation_index=1,
        ),
    ),
    AIEAgent(
        title="Executive Vice President & Chief Operations Officer",
        primary_domain="operating_cost",
        role_archetype=(
            "efficiency-driven and process-oriented, focused on operational "
            "excellence and cost reduction"
        ),
        aes_weights=AESWeights(
            revenue=3, operating_cost=-3, cash_reserves=2,
            headcount=2, rd_investment=1, brand_strength=1, innovation_index=1,
        ),
    ),
    AIEAgent(
        title="Executive Vice President & Chief People Officer",
        primary_domain="headcount",
        role_archetype=(
            "employee-first and culture-oriented, advocates for talent "
            "investment and workforce stability"
        ),
        aes_weights=AESWeights(
            revenue=1, operating_cost=-1, cash_reserves=1,
            headcount=4, rd_investment=2, brand_strength=2, innovation_index=2,
        ),
    ),
    AIEAgent(
        title="Executive Vice President, Office of Strategy & Transformation",
        primary_domain="innovation_index",
        role_archetype=(
            "forward-looking and transformation-focused, champions strategic "
            "pivots and long-horizon investments"
        ),
        aes_weights=AESWeights(
            revenue=3, operating_cost=-1, cash_reserves=2,
            headcount=1, rd_investment=3, brand_strength=2, innovation_index=4,
        ),
    ),
    AIEAgent(
        title="Executive Vice President & Chief Marketing Officer",
        primary_domain="brand_strength",
        role_archetype=(
            "growth- and brand-oriented, focused on market positioning, "
            "perception, and demand generation"
        ),
        aes_weights=AESWeights(
            revenue=3, operating_cost=-1, cash_reserves=1,
            headcount=1, rd_investment=1, brand_strength=4, innovation_index=2,
        ),
    ),
    AIEAgent(
        title="Executive Vice President & Chief Commercial Officer",
        primary_domain="revenue",
        role_archetype=(
            "sales-driven and commercially aggressive, focused on top-line "
            "growth and market share"
        ),
        aes_weights=AESWeights(
            revenue=4, operating_cost=-1, cash_reserves=2,
            headcount=2, rd_investment=1, brand_strength=3, innovation_index=1,
        ),
    ),
    AIEAgent(
        title="Chief Technology Officer, Business & AI",
        primary_domain="rd_investment",
        role_archetype=(
            "technically ambitious and AI-forward, advocates for R&D investment "
            "and infrastructure modernization"
        ),
        aes_weights=AESWeights(
            revenue=2, operating_cost=-1, cash_reserves=1,
            headcount=2, rd_investment=4, brand_strength=1, innovation_index=4,
        ),
    ),
    AIEAgent(
        title="Executive Vice President & President, Global Sales, Marketing & Operations",
        primary_domain="revenue",
        role_archetype=(
            "operationally focused on global revenue execution, bridges "
            "commercial strategy with field delivery"
        ),
        aes_weights=AESWeights(
            revenue=4, operating_cost=-2, cash_reserves=2,
            headcount=2, rd_investment=1, brand_strength=3, innovation_index=1,
        ),
    ),
]