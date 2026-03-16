from __future__ import annotations


def build_prompt_c(fiscal_quarter: str, documents: dict[str, str]) -> dict:
    label_map = {
        "transcript":       "Earnings Call Transcript",
        "earnings_slides":  "Earnings Call Slides",
        "outlook_slides":   "Outlook Slides",
        "press_release":    "Press Release",
        "product_releases": "Product Release List",
        "performance":      "Performance Summary",
    }

    sections = []
    for key, label in label_map.items():
        text = documents.get(key) or ""
        if text.strip():
            sections.append(f"### {label}\n{text.strip()}")

    docs_combined = "\n\n".join(sections)
    doc_list_str  = ", ".join(
        label_map[k] for k in label_map
        if (documents.get(k) or "").strip()
    ) or "none"

    system = """\
You are a corporate strategy analyst processing a company's quarterly earnings \
materials. Your job is to extract and quantify signals from qualitative documents \
and populate specific fields of a CompanyState vector.

You must respond only with a valid JSON object and nothing else — no explanation, \
no preamble, no markdown fences.

Scoring rules:
- All scale fields use integers 1–10.
    1 = extremely low / negative / absent
    5 = neutral / moderate / industry-average
   10 = extremely high / positive / dominant
- Boolean fields must be true or false (not strings).
- Headcount estimates are integers (number of employees).
- For any field where the documents provide insufficient signal, use null and \
record your reason in derivation_notes.
- Do not invent data. If you are uncertain, bias toward null over a guess."""

    user = f"""\
## Fiscal Quarter
{fiscal_quarter}

## Documents Provided
{doc_list_str}

## Document Contents

{docs_combined}

## Task
Analyze all provided documents together and extract the following fields. \
Cross-reference across documents where signals conflict — prefer the earnings \
transcript for sentiment and forward guidance, and the press release for \
factual announcements.

Return exactly this JSON structure:
{{
  "quarter": "{fiscal_quarter}",
  "Human_Impacts": {{
    "hiring_freeze":          <true | false>,
    "layoffs_this_quarter":   <true | false>,
    "engineering_headcount":  <integer estimate | null>,
    "sales_headcount":        <integer estimate | null>
  }},
  "Growth_Signals": {{
    "ai_investment_focus":  <1-10>,
    "innovation_index":     <1-10>,
    "competitive_pressure": <1-10>,
    "regulatory_pressure":  <1-10>,
    "brand_strength":       <1-10>
  }},
  "Market_Signals": {{
    "investor_sentiment": <1-10>,
    "growth_expectation": <1-10>
  }},
  "derivation_notes": {{
    "hiring_freeze":          "<evidence or null reason>",
    "layoffs_this_quarter":   "<evidence or null reason>",
    "engineering_headcount":  "<evidence or null reason>",
    "sales_headcount":        "<evidence or null reason>",
    "ai_investment_focus":    "<evidence or null reason>",
    "innovation_index":       "<evidence or null reason>",
    "competitive_pressure":   "<evidence or null reason>",
    "regulatory_pressure":    "<evidence or null reason>",
    "brand_strength":         "<evidence or null reason>",
    "investor_sentiment":     "<evidence or null reason>",
    "growth_expectation":     "<evidence or null reason>"
  }}
}}"""

    return {"system": system, "user": user}