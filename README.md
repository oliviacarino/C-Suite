# C-Suite
### *Do we actually need human executives?*

A SIGBOVIK 2026 research project that simulates a full corporate C-suite using a panel of LLM agents, runs them through a real company's fiscal year, and compares their strategic decisions and simulated outcomes against what the actual leadership team did.

The company is anonymous. The data is real.

---

## What it does

The simulation initializes from a real company's FY22Q4 financial state, then runs four quarters (FY23Q1–Q4) under AI executive control. Each quarter, a board of ten AI Executive (AIE) agents — each embodying a distinct C-suite role and behavioral archetype — reviews the company's current state, proposes strategic actions, votes on them, and updates the company state based on the approved decisions.

At the end, simulated outcomes (revenue delta, profit margin, cash, headcount) are compared against what the real company actually produced.

---

## How it works

### Agents
Ten AIEs map to real C-suite titles: CEO, CFO, COO, CPO, CTO, CMO, CCO, VP&Chair, EVP Strategy, and EVP Global Sales. Each agent has role-specific AES weight vectors that determine how they evaluate proposed actions, and domain expertise bonuses that amplify their voting influence in their primary area.

### Decision loop (per quarter)
1. **Qualitative extraction (Prompt C)** — Claude reads the earnings transcript, press release, and product release list and derives quantitative signals: hiring freeze, layoff activity, headcount estimates, AI investment focus, competitive pressure, investor sentiment, etc.
2. **State initialization** — Direct financial data (revenue, margins, R&D, capex, segments) is parsed from the XLS. Derived signals from Prompt C are merged in to form the full `CompanyState` vector.
3. **Proposal phase (Prompt D)** — Each AIE receives a context packet with the full company state and external market context (Gartner hype cycle position, competitive signals), then proposes up to 3 actions from the `ActionLibrary`.
4. **Effect prediction (Prompt A)** — For each unique proposed action, Claude predicts directional effects on all CompanyState variables (scale: −3 to +3).
5. **Voting (AES → AWS)** — Each agent computes an Action Evaluation Score (weighted sum of effects × role priorities), derives a YES/NO vote from the sign, applies domain bonuses, and contributes a weighted vote. Actions with `FinalDecisionScore > 0` pass.
6. **Action selection** — The top K passing actions by score are implemented (default K=5).
7. **State transition (Prompt B)** — Claude applies all approved actions simultaneously to the CompanyState, with realistic second-order effects, producing the end-of-quarter state.
8. **Logging** — Full per-quarter JSON log: start state, all proposals, all vote scores, approved actions, end state, derivation notes.

### Scoring math

**AES (individual):**
```
AES_agent(a) = Σ w_agent,i × Effect_i(a)
```
Where `w` is the agent's role-priority weight for AES category `i` (range −4 to +4), and `Effect_i(a)` is Claude's predicted directional impact of action `a` on that category.

**Vote direction:**
```
vote = +1 if AES > 0,  −1 if AES < 0,  0 if AES = 0
```

**Vote weight (AWS):**
```
VoteWeight = VoteDirection × (1 + DomainBonus)
```
Domain bonus = 2 if the action falls in the agent's primary domain, else 0. So a domain-expert YES = +3, a domain-expert NO = −3, a non-domain YES/NO = ±1.

**Final decision:**
```
FinalDecisionScore(a) = Σ VoteWeight_agent,i  across all agents
action passes if FinalDecisionScore(a) > 0
```

---

## Project structure

```
csuite/
│
├── main.py                        # Entry point
├── test_parse.py                  # Parser validation — no API calls
├── config.py                      # Paths, API config, quarter directory map
├── .env                           # ANTHROPIC_API_KEY (never commit)
│
├── data/
│   ├── input/
│   │   ├── FY22Q4/                # Init quarter asset files
│   │   └── FY2023/
│   │       ├── Q1/
│   │       │   ├── FY23Q1-zip/    # Earnings assets (XLS, DOCX, PPTX)
│   │       │   └── FY23 Q1 - Performance - Investor Relations
│   │       ├── Q2/  ...
│   │       ├── Q3/  ...
│   │       └── Q4/  ...
│   └── processed/                 # Output: one CompanyState JSON per quarter
│
├── util/
│   ├── parse_financials.py        # XLS → Financials + Segments dict
│   └── parse_qualitative.py       # DOCX / PPTX / PDF → plain text
│
├── prompts/
│   └── prompt_c_derive_qualitative_data.py   # Prompt C builder
│
├── agents/                        # (simulation phase)
│   └── board.py                   # 10 AIE agents with AES weights + archetypes
│
├── simulation/                    # (simulation phase)
│   ├── company_state.py           # CompanyState dataclass
│   ├── action_library.py          # 30 actions + AES category map
│   ├── voting_engine.py           # AES → vote → AWS → DecisionScore
│   └── pipeline.py                # Quarterly loop orchestrator
│
└── results/                       # Per-quarter simulation logs (JSON)
```

---

## Asset files per quarter

| File | Type | Used for |
|---|---|---|
| `FinancialStatementFY23Qn.xlsx` | XLSX | Direct financial + segment data |
| `TranscriptFY23Qn.docx` | DOCX | Prompt C — qualitative signals |
| `PressReleaseFY23Qn.docx` | DOCX | Prompt C — factual announcements |
| `FY23QnProductList.docx` | DOCX | Prompt C — product release signals |
| `OutlookFY23Qn.pptx` | PPTX | Prompt C — forward guidance (if text-based) |
| `SlidesFY23Qn.pptx` | PPTX | Prompt C — earnings slides (if text-based) |
| `FY23 Qn - Performance - ...pdf` | PDF | Prompt C — performance metrics |
| `Metrics_FY23Qn.xlsx` | XLSX | Not used (investor metrics, redundant) |
| `COMPANY_FY23Qn_10Q.docx` | DOCX | Not used (SEC filing, too long) |

> Note: This company's earnings PPTX files (Slides, Outlook) are fully image-based and yield no extractable text. Prompt C runs on the transcript, press release, and product list instead — which together contain all the qualitative signal needed.

---

## Setup

```bash
pip install anthropic openpyxl python-docx python-pptx python-dotenv pymupdf
```

Create `.env` in the project root:
```
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Running

### 1. Validate parsers (no API calls)
```bash
python test_parse.py              # all quarters
python test_parse.py FY22Q4       # single quarter
```
Prints all parsed financial values with zero-flags, confirms which documents were found, and shows a preview of each.

### 2. Parse all quarters → CompanyState JSONs
```bash
python main.py --dry-run          # parse only, skip Prompt C
python main.py                    # full parse including Prompt C API calls
```
Outputs one `data/processed/<QUARTER>_company_state.json` per quarter.

### 3. Run the simulation (once parsing is complete)
```bash
python main.py --simulate                    # full FY2023
python main.py --simulate --quarter FY23Q1   # single quarter
```
Outputs one `results/<QUARTER>_log.json` per quarter containing the full decision trace.

---

## CompanyState vector

```python
CompanyState = {
    "Financials": {          # DIRECT — from XLS
        "revenue", "cost_of_revenue", "gross_margin",
        "operating_income", "net_income", "cash_and_equivalents",
        "total_operating_expenses", "rd_spending",
        "sales_marketing_spending", "capex"
    },
    "Segments": {            # DIRECT — from XLS segment sheet
        "productivity_revenue",
        "intelligent_cloud_revenue",
        "personal_computing_revenue"
    },
    "Human_Impacts": {       # MIXED — total_employees direct; rest Claude-derived
        "total_employees", "hiring_freeze",
        "layoffs_this_quarter", "engineering_headcount", "sales_headcount"
    },
    "Growth_Signals": {      # CLAUDE-DERIVED — Prompt C, scale 1–10
        "ai_investment_focus", "innovation_index",
        "competitive_pressure", "regulatory_pressure", "brand_strength"
    },
    "Market_Signals": {      # CLAUDE-DERIVED + direct
        "investor_sentiment", "growth_expectation", "stock_price"
    }
}
```

---

## Action library

30 actions across 8 categories: R&D Investment, Innovation Index, Revenue, Brand Strength, Headcount, Operating Cost, Cash Reserves, and Multi-category / Governance. Each AIE proposes up to 3 actions per quarter from this fixed list. The top 5 by `FinalDecisionScore` are implemented.

---

## Comparison metrics (Section 6)

Once all four simulation quarters are complete, results are compared against the real company's actual FY2023 performance across four dimensions: revenue delta, profit margin, cash remaining, and headcount change. A timeline graph will overlay simulated decisions against real tech events from the 2023 Gartner Hype Cycle to surface how macro signals influenced the AIE board's choices.

---

## Research questions

1. Does an AI-simulated C-suite produce decisions measurably different from its human-led counterpart?
2. Do those decisions lead to better, worse, or statistically indistinguishable simulated outcomes?
3. *(Optional)* Does multi-agent executive communication improve decision quality?

*Submitted to SIGBOVIK 2026.*