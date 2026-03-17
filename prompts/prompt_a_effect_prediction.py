"""
prompts/prompt_a_effect_prediction.py

Prompt A: Effect prediction.

For each unique proposed action, Claude predicts the directional effect
on every CompanyState variable. The output feeds directly into AES scoring
in the voting engine.

Called once per unique proposed action, before voting begins.
Stateless — does not modify anything, safe to call in parallel.
"""

from __future__ import annotations


def build_prompt_a(company_state: dict, action_name: str) -> dict:
    """
    Build Prompt A for a single proposed action.

    Args:
        company_state: The current CompanyState dict (from data/processed/)
        action_name:   The action string from ActionLibrary (e.g. "increase_rd_5")

    Returns:
        {"system": str, "user": str} ready for the Anthropic messages API.
    """
    import json
    state_json = json.dumps(company_state, indent=2)

    system = """\
You are a corporate strategy simulation engine. Your job is to predict the \
directional effects of a proposed business action on a company's state variables.

You must respond only with a valid JSON object and nothing else — no explanation, \
no preamble, no markdown fences.

Return effects as integers in the range [-3, +3] where:
  +3 = strong positive impact
  +1 = mild positive impact
   0 = no meaningful impact
  -1 = mild negative impact
  -3 = strong negative impact

Consider both direct and second-order effects. For example:
  - increase_rd_5 directly raises rd_spending and reduces cash,
    but also improves innovation_index and ai_investment_focus over time
  - layoff_5_percent reduces total_employees and layoffs_this_quarter cost,
    but may hurt brand_strength, investor_sentiment, and innovation_index
  - freeze_hiring reduces total_operating_expenses modestly
    but constrains engineering_headcount and innovation capacity"""

    user = f"""\
## Current CompanyState
{state_json}

## Proposed Action
{action_name}

## Task
Predict the directional effect of this action on each of the following state \
variables given the current company context. Consider second-order effects.

Return exactly this JSON structure with no additional fields:
{{
  "action": "{action_name}",
  "effects": {{
    "revenue": 0,
    "cost_of_revenue": 0,
    "gross_margin": 0,
    "operating_income": 0,
    "net_income": 0,
    "cash_and_equivalents": 0,
    "total_operating_expenses": 0,
    "rd_spending": 0,
    "sales_marketing_spending": 0,
    "capex": 0,
    "productivity_revenue": 0,
    "intelligent_cloud_revenue": 0,
    "personal_computing_revenue": 0,
    "total_employees": 0,
    "hiring_freeze": 0,
    "layoffs_this_quarter": 0,
    "engineering_headcount": 0,
    "sales_headcount": 0,
    "ai_investment_focus": 0,
    "innovation_index": 0,
    "competitive_pressure": 0,
    "regulatory_pressure": 0,
    "brand_strength": 0,
    "investor_sentiment": 0,
    "growth_expectation": 0
  }},
  "rationale": "<2-3 sentences explaining the key non-zero effects>"
}}"""

    return {"system": system, "user": user}