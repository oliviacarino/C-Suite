"""
simulation/action_library.py

Defines the full ActionLibrary as an enum and maps each action to its
primary AES category. The primary category is used by the AWS voting
engine to determine whether an agent's domain bonus applies.
"""

from __future__ import annotations
from enum import Enum


class Action(str, Enum):
    # R&D Investment
    INCREASE_RD_5               = "increase_rd_5"
    INCREASE_RD_10              = "increase_rd_10"
    LAUNCH_MAJOR_AI_INITIATIVE  = "launch_major_ai_initiative"
    ACQUIRE_AI_STARTUP          = "acquire_ai_startup"
    LAUNCH_EXPERIMENTAL_PRODUCT = "launch_experimental_product"
    ACCELERATE_PRODUCT_DEV      = "accelerate_product_development"

    # Innovation Index
    EXPAND_CLOUD_INVESTMENT     = "expand_cloud_investment"
    INCREASE_CAPEX_DATACENTERS  = "increase_capex_datacenters"

    # Revenue
    LAUNCH_MAJOR_PRODUCT        = "launch_major_product"
    EXPAND_ENTERPRISE_SALES     = "expand_enterprise_sales"
    EXPAND_GLOBAL_MARKETS       = "expand_global_markets"
    STRATEGIC_PARTNERSHIP       = "strategic_partnership"
    SHIFT_BUDGET_HIGH_GROWTH    = "shift_budget_to_high_growth_segments"

    # Brand Strength
    INCREASE_MARKETING_10       = "increase_marketing_10"
    INCREASE_MARKETING_20       = "increase_marketing_20"

    # Headcount
    FREEZE_HIRING               = "freeze_hiring"
    LAYOFF_5_PERCENT            = "layoff_5_percent"
    LAYOFF_10_PERCENT           = "layoff_10_percent"
    INCREASE_ENG_HIRING         = "increase_engineering_hiring"
    EXPAND_SALES_TEAM           = "expand_sales_team"
    RESTRUCTURE_ENG_TEAMS       = "restructure_engineering_teams"

    # Operating Cost
    REDUCE_COSTS_5              = "reduce_costs_5"
    REDUCE_COSTS_10             = "reduce_costs_10"
    OPTIMIZE_OPERATIONS         = "optimize_operations"
    CONSOLIDATE_PRODUCT_LINES   = "consolidate_product_lines"

    # Cash Reserves
    STOCK_BUYBACK               = "stock_buyback_program"
    INCREASE_DIVIDEND           = "increase_dividend"

    # Multi-category / Governance
    REGULATORY_COMPLIANCE       = "regulatory_compliance_investment"
    SUSTAINABILITY_INITIATIVE   = "sustainability_initiative"
    IMPROVE_SECURITY_INFRA      = "improve_security_infrastructure"


# Maps each action to its primary AES category key.
# Must match the keys used in AESWeights (board.py).
ACTION_PRIMARY_CATEGORY: dict[str, str] = {
    Action.INCREASE_RD_5:               "rd_investment",
    Action.INCREASE_RD_10:              "rd_investment",
    Action.LAUNCH_MAJOR_AI_INITIATIVE:  "rd_investment",
    Action.ACQUIRE_AI_STARTUP:          "rd_investment",
    Action.LAUNCH_EXPERIMENTAL_PRODUCT: "rd_investment",
    Action.ACCELERATE_PRODUCT_DEV:      "rd_investment",

    Action.EXPAND_CLOUD_INVESTMENT:     "innovation_index",
    Action.INCREASE_CAPEX_DATACENTERS:  "innovation_index",

    Action.LAUNCH_MAJOR_PRODUCT:        "revenue",
    Action.EXPAND_ENTERPRISE_SALES:     "revenue",
    Action.EXPAND_GLOBAL_MARKETS:       "revenue",
    Action.STRATEGIC_PARTNERSHIP:       "revenue",
    Action.SHIFT_BUDGET_HIGH_GROWTH:    "revenue",

    Action.INCREASE_MARKETING_10:       "brand_strength",
    Action.INCREASE_MARKETING_20:       "brand_strength",

    Action.FREEZE_HIRING:               "headcount",
    Action.LAYOFF_5_PERCENT:            "headcount",
    Action.LAYOFF_10_PERCENT:           "headcount",
    Action.INCREASE_ENG_HIRING:         "headcount",
    Action.EXPAND_SALES_TEAM:           "headcount",
    Action.RESTRUCTURE_ENG_TEAMS:       "headcount",

    Action.REDUCE_COSTS_5:              "operating_cost",
    Action.REDUCE_COSTS_10:             "operating_cost",
    Action.OPTIMIZE_OPERATIONS:         "operating_cost",
    Action.CONSOLIDATE_PRODUCT_LINES:   "operating_cost",

    Action.STOCK_BUYBACK:               "cash_reserves",
    Action.INCREASE_DIVIDEND:           "cash_reserves",

    Action.REGULATORY_COMPLIANCE:       "revenue",
    Action.SUSTAINABILITY_INITIATIVE:   "revenue",
    Action.IMPROVE_SECURITY_INFRA:      "rd_investment",
}

# Flat list of action name strings — used in Prompt D context packet
ALL_ACTION_NAMES: list[str] = [a.value for a in Action]