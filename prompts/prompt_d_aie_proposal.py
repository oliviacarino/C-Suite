"""
prompts/prompt_d_aie_proposal.py

Prompt D: AIE Proposal Phase (context packet).

Each AIE receives a fully populated context packet containing:
  - Their role identity and behavioral archetype
  - The full CompanyState for the current quarter
  - External market context (tech trends, competitive signals)
  - The approved ActionLibrary they must choose from

The agent responds with up to 3 proposed actions and rationale grounded
in their role priorities and the current state data.

Called once per AIE per quarter, before voting begins.
"""

from __future__ import annotations
from agents.board import AIEAgent
from sim.action_library import ALL_ACTION_NAMES


def build_prompt_d(
    agent: AIEAgent,
    company_state: dict,
    external_context: str,
) -> dict:
    """
    Build Prompt D for a single AIE agent.

    Args:
        agent:            The AIEAgent instance (from agents/board.py)
        company_state:    The current CompanyState dict (from data/processed/)
        external_context: String describing current macro/tech environment

    Returns:
        {"system": str, "user": str} ready for the Anthropic messages API.
    """
    top_vars = ", ".join(agent.top_weighted_variables())
    action_list = "\n".join(f"  - {a}" for a in ALL_ACTION_NAMES)

    fin = company_state.get("Financials", {})
    seg = company_state.get("Segments", {})
    hi  = company_state.get("Human_Impacts", {})
    gs  = company_state.get("Growth_Signals", {})
    ms  = company_state.get("Market_Signals", {})
    quarter = company_state.get("quarter", "unknown")

    system = f"""\
You are {agent.title}, a member of the AI Executive (AIE) board simulating \
a major technology company's strategic decision-making.

Your role priorities are:
- Primary domain: {agent.primary_domain}
- You weight decisions heavily toward: {top_vars}
- You are characteristically: {agent.role_archetype}

You must respond only with a valid JSON object and nothing else — no explanation, \
no preamble, no markdown fences.

You may ONLY propose actions from the approved ActionLibrary listed below. \
Do not invent actions outside this list.

Approved ActionLibrary:
{action_list}"""

    user = f"""\
## Fiscal Quarter
{quarter}

## Company State

### Financials (USD millions)
| Metric                    | Value                               |
|---------------------------|-------------------------------------|
| Revenue                   | {fin.get("revenue", 0):>12,.1f}     |
| Cost of Revenue           | {fin.get("cost_of_revenue", 0):>12,.1f} |
| Gross Margin              | {fin.get("gross_margin", 0):>12.1f}% |
| Operating Income          | {fin.get("operating_income", 0):>12,.1f} |
| Net Income                | {fin.get("net_income", 0):>12,.1f}  |
| Cash & Equivalents        | {fin.get("cash_and_equivalents", 0):>12,.1f} |
| Total Operating Expenses  | {fin.get("total_operating_expenses", 0):>12,.1f} |
| R&D Spending              | {fin.get("rd_spending", 0):>12,.1f} |
| Sales & Marketing         | {fin.get("sales_marketing_spending", 0):>12,.1f} |
| CapEx                     | {fin.get("capex", 0):>12,.1f}       |

### Segments (USD millions)
| Segment             | Revenue                                     |
|---------------------|---------------------------------------------|
| Productivity        | {seg.get("productivity_revenue", 0):>12,.1f} |
| Intelligent Cloud   | {seg.get("intelligent_cloud_revenue", 0):>12,.1f} |
| Personal Computing  | {seg.get("personal_computing_revenue", 0):>12,.1f} |

### Human Impacts
| Metric                 | Value                                          |
|------------------------|------------------------------------------------|
| Total Employees        | {hi.get("total_employees", 0):>12,}            |
| Hiring Freeze          | {hi.get("hiring_freeze", False)}               |
| Layoffs This Quarter   | {hi.get("layoffs_this_quarter", False)}        |
| Engineering Headcount  | {hi.get("engineering_headcount") or "unknown"} (estimated) |
| Sales Headcount        | {hi.get("sales_headcount") or "unknown"} (estimated) |

### Growth Signals (1–10 scale)
| Signal                | Score                                |
|-----------------------|--------------------------------------|
| AI Investment Focus   | {gs.get("ai_investment_focus", 5)}   |
| Innovation Index      | {gs.get("innovation_index", 5)}      |
| Competitive Pressure  | {gs.get("competitive_pressure", 5)}  |
| Regulatory Pressure   | {gs.get("regulatory_pressure", 5)}   |
| Brand Strength        | {gs.get("brand_strength", 5)}        |

### Market Signals
| Signal              | Value                                  |
|---------------------|----------------------------------------|
| Investor Sentiment  | {ms.get("investor_sentiment", 5)}      |
| Growth Expectation  | {ms.get("growth_expectation", 5)}      |
| Stock Price         | {ms.get("stock_price") or "N/A"}       |

## External Context
{external_context}

## Your Role in This Cycle
As {agent.title}, review the company state and external context above. \
Propose up to 3 actions you believe are strategically appropriate for this \
quarter. Ground your reasoning in your role priorities and the specific \
numbers above.

Return exactly this JSON structure:
{{
  "agent": "{agent.title}",
  "quarter": "{quarter}",
  "proposed_actions": [
    {{
      "action": "<action_name_from_ActionLibrary>",
      "rationale": "<2-3 sentences grounded in current state data and your role priorities>"
    }}
  ]
}}"""

    return {"system": system, "user": user}