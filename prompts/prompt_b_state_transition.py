"""
prompts/prompt_b_state_transition.py

Prompt B: State transition.

Takes the current CompanyState and the approved action set for the quarter,
and returns an updated CompanyState reflecting the end-of-quarter state.

Called once per quarter, after the voting engine selects the top-K actions.
This is the only prompt that mutates state — all others are read-only.
"""

from __future__ import annotations
import json


def build_prompt_b(
    company_state: dict,
    approved_actions: list[str],
    external_context: str,
) -> dict:
    """
    Build Prompt B for the state transition step.

    Args:
        company_state:    The current CompanyState dict (start of quarter)
        approved_actions: List of action name strings that passed the vote
        external_context: Current macro/tech environment string

    Returns:
        {"system": str, "user": str} ready for the Anthropic messages API.
    """
    state_json = json.dumps(company_state, indent=2)
    actions_str = "\n".join(f"  - {a}" for a in approved_actions)
    quarter = company_state.get("quarter", "unknown")

    system = """\
You are a corporate strategy simulation engine applying a set of approved \
executive decisions to a company's quarterly state.

You must respond only with a valid JSON object and nothing else — no \
explanation, no preamble, no markdown fences.

Rules:
- Apply all actions simultaneously, not sequentially.
- Scale financial values proportionally where applicable:
    increase_rd_5  → rd_spending  *= 1.05
    increase_rd_10 → rd_spending  *= 1.10
    reduce_costs_5 → total_operating_expenses *= 0.95
    reduce_costs_10 → total_operating_expenses *= 0.90
    increase_marketing_10 → sales_marketing_spending *= 1.10
    increase_marketing_20 → sales_marketing_spending *= 1.20
    layoff_5_percent  → total_employees *= 0.95
    layoff_10_percent → total_employees *= 0.90
- Boolean fields (hiring_freeze, layoffs_this_quarter) must be true or false.
- Qualitative/derived fields (ai_investment_focus, brand_strength, etc.) \
use a 1–10 integer scale.
- Do not invent new fields. Return the exact same JSON structure as the input.
- Apply realistic second-order effects. For example:
    layoffs reduce total_employees but may lower brand_strength and \
innovation_index
    increase_rd_10 raises rd_spending but also improves innovation_index \
and ai_investment_focus
    freeze_hiring constrains engineering_headcount and future growth capacity
- Update the "quarter" field to indicate this is the end-of-quarter state."""

    user = f"""\
## Current CompanyState (start of quarter: {quarter})
{state_json}

## Approved Actions This Quarter
{actions_str}

## External Context
{external_context}

## Task
Apply all approved actions simultaneously to the CompanyState and return \
the updated state vector for the end of this quarter.

For financial fields with explicit scaling rules above, compute the new \
absolute value. For qualitative/derived fields, use your judgment based on \
the combined effect of the action set and external context.

Return the complete updated CompanyState JSON with the same structure as \
the input. Set "quarter" to "{quarter}_end"."""

    return {"system": system, "user": user}