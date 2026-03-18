# C-Suite
### *Do we actually need human executives?*

A SIGBOVIK 2026 research project that simulates a full corporate C-suite using a panel of LLM agents, runs them through a real company's fiscal year, and compares their strategic decisions and simulated outcomes against what the actual leadership team did.

The simulation initializes from a real company's FY22Q4 financial state, then runs four quarters (FY23Q1–Q4). Each quarter, a board of ten AI Executive (AIE) agents, each embodying a distinct C-suite role, reviews the company's current state, proposes strategic actions, votes on them, and updates the company state based on the approved decisions.

At the end, simulated outcomes (revenue delta, profit margin, cash, headcount) are compared against what the real company actually produced.

Note that this is a very, *very* satirical take on the latest trend in tech: job automation.

## Results

Each quarter's AIE board received the real financial state and external market context (*qualitative data pulled from real documentation, then fed to Claude*) and made independent *strategic* decisions.

### Comparison: simulated vs actual

| Quarter | Revenue Sim | Revenue Actual | Delta | Op. Margin Sim | Op. Margin Actual | Delta |
|---------|------------|---------------|-------|---------------|------------------|-------|
| FY23Q1  | $52,628M   | $52,747M      | −$119M | 42.9% | 38.7% | +4.3% |
| FY23Q2  | $54,684M   | $52,857M      | +$1,827M | 36.8% | 42.3% | −5.5% |
| FY23Q3  | $55,200M   | $56,189M      | −$989M | 43.2% | 43.2% | 0.0% |
| FY23Q4  | $58,996M   | $56,189M      | +$2,807M | 42.5% | 43.2% | −0.7% |

| Quarter | Cash Sim   | Cash Actual | Delta      | Headcount Sim | Headcount Actual | Delta |
|---------|-----------|------------|------------|--------------|-----------------|-------|
| FY23Q1  | $20,356M  | $15,646M   | +$4,710M   | 221,000 | 221,000 | 0 |
| FY23Q2  | $13,146M  | $26,562M   | −$13,416M  | 223,450 | 221,000 | +2,450 |
| FY23Q3  | $25,200M  | $34,704M   | −$9,504M   | 225,500 | 228,000 | −2,500 |
| FY23Q4  | $32,959M  | $34,704M   | −$1,745M   | 242,800 | 238,000 | +4,800 |

### Key findings

**Revenue — close alignment.** The AIE board tracked actual revenue within 0.2% in Q1 and within 5% across all four quarters. The trajectory was correct, both lines trend upward through the year, though the simulation ran slightly hot in Q2 and Q4.

**Operating margin — diverged early, converged late.** Q1 the simulation was more profitable than reality (+4.3%), likely because the board's approved actions leaned toward revenue expansion rather than the heavy infrastructure spending the actual company realistically  made. Q3 margin matched exactly (0.0% delta), and Q4 was within 0.7%.

**Cash — largest divergence.** The simulation consistently underestimated cash reserves, most significantly in Q2 (−$13.4B). This reflects a known limitation: the ActionLibrary doesn't model financing decisions (share buybacks, debt management, dividend payments) that the actual company actively used to manage its cash position. Cash is the weakest metric in this simulation design.

**Headcount — strongest result.** The simulation matched actual headcount exactly in Q1, stayed within 2,500 employees (≈1%) across all quarters, and correctly captured the growth trajectory through the year.

**Strategic direction.** Across all four quarters, the AIE board consistently proposed and approved AI-investment-oriented actions — `launch_major_ai_initiative`, `expand_cloud_investment`, `increase_rd_10`, `increase_capex_datacenters`, which aligns with what the actual company prioritized during its FY2023 [major product] push. The external context injection (the 2023 Gartner Hype Cycle, ChatGPT's birth in Nov. 2022) appears to have driven the board toward the correct strategic posture.

---

## How it works

### Agents
Ten AIEs map to real C-suite titles: CEO, CFO, COO, CPO, CTO, CMO, CCO, VP&Chair, EVP Strategy, and EVP Global Sales. Each agent has role-specific AES weight vectors that determine how they evaluate proposed actions, and domain expertise bonuses that amplify their voting influence in their primary area.

### Decision loop (per quarter)
1. **Qualitative extraction (Prompt C)** — Claude reads the earnings transcript, press release, and product release list and derives quantitative signals: hiring freeze, layoff activity, headcount estimates, AI investment focus, competitive pressure, investor sentiment, etc.
2. **State initialization** — Direct financial data (revenue, margins, R&D, capex, segments) is parsed from the XLS. Derived signals from Prompt C are merged in to form the full `CompanyState` vector.
3. **Proposal phase (Prompt D)** — Each AIE receives a context packet with the full company state and external market context, then proposes up to 3 actions from the `ActionLibrary`.
4. **Effect prediction (Prompt A)** — For each unique proposed action, Claude predicts directional effects on all CompanyState variables (scale: −3 to +3).
5. **Voting (AES → AWS)** — Each agent computes an Action Evaluation Score (weighted sum of effects × role priorities), derives a YES/NO vote from the sign, applies domain bonuses, and contributes a weighted vote. Actions with `FinalDecisionScore > 0` pass.
6. **Action selection** — The top K passing actions by score are implemented (default K=5).
7. **State transition (Prompt B)** — Claude applies all approved actions simultaneously to the `CompanyState`, with realistic second-order effects, producing the end-of-quarter state.
8. **Logging** — Full per-quarter JSON log: start state, all proposals, all vote scores, approved actions, end state, derivation notes.

### Scoring math

**AES (individual):**

<img src="./images/AES_score.png" width="400"/>

Where `i` is the index of the current state vector,
`w_agent,i` is the role-priority weight for state variable `i` (field within the current `CompanyState`, range −4 to +4), and `Effect_i(a)` is the Claude-predicted directional impact of action `a` on variable `i` (e.g., −2, 0, +3).

**Vote direction:**
```
vote = +1 if AES > 0,  −1 if AES < 0,  0 if AES = 0
```

**Vote weight (AWS):**
```
VoteWeight = VoteDirection × (1 + DomainBonus)
```
Domain bonus = 2 if the action falls in the agent's primary domain, else 0.

**Final decision:**

<img src="./images/Final_Decision_Score.png" width="400"/>

---

## Project structure

```
csuite/
├── main.py                        # Entry point — parsing + simulation
├── config.py                      # Paths, API config, quarter directory map
├── .env                           
├── data/
│   ├── input/
│   │   ├── FY22Q4/                # Init quarter asset files
│   │   └── FY2023/
│   │       ├── Q1/
│   │       ├── Q2/ ...
│   │       ├── Q3/ ...
│   │       └── Q4/ ...
│   └── processed/                 # CompanyState JSONs (one per quarter)
│
├── agents/
│   └── board.py                   # 10 AIE agents with AES weights + personalities
│
├── simulation/
│   ├── action_library.py          # 30 actions + AES category map
│   └── voting_engine.py           # AES → vote → AWS → DecisionScore
│
├── sim/
│   └── pipeline.py                # Full quarterly sim
│
├── prompts/
│   ├── prompt_a_effect_prediction.py
│   ├── prompt_b_state_transition.py
│   ├── prompt_c_derive_qualitative_data.py
│   └── prompt_d_aie_proposal.py
│
├── util/
│   ├── parse_financials.py        # XLS → Financials + Segments dict
│   ├── parse_qualitative.py       # DOCX / PPTX / PDF → plain text
│   └── compare.py                 # Simulated vs actual comparison + charts
│
├── test/
│   ├── test_parse.py              # Parser validation (no API calls)
│   ├── test_voting.py             # Voting engine validation (no API calls)
│   ├── test_prompt_a.py           # Prompt A integration test
│   ├── test_prompt_d.py           # Prompt D integration test
│   └── test_pipeline.py           # Full pipeline integration test
│
└── results/
    ├── FY23Q1_simulation_log.json
    ├── FY23Q2_simulation_log.json
    ├── FY23Q3_simulation_log.json
    ├── FY23Q4_simulation_log.json
    ├── comparison_results.json
    └── charts/
        └── comparison_charts.png
```

---

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `.env` in the project root with your `ANTHROPIC_API_KEY`

---

## Running

### 1. Validate parsers (no API calls)
```bash
python test/test_parse.py              # all quarters
python test/test_parse.py FY22Q4       # single quarter
```

### 2. Validate agents and voting engine (no API calls)
```bash
python test/test_voting.py
```

### 3. Parse all quarters to `CompanyState` state vectors  saved as JSON 
```bash
python main.py --dry-run    # parse only, skip Prompt C
python main.py              # full parse including Prompt C API calls
```
Outputs one `data/processed/<QUARTER>_company_state.json` per quarter.

### 4. Run the simulation
```bash
python main.py --simulate --quarter FY23Q1   # single quarter
python main.py --simulate                     # full FY2023 (all 4 quarters)
```
Outputs one `results/<QUARTER>_simulation_log.json` per quarter.

### 5. Compare results
```bash
python util/compare.py           # prints table + displays charts
python util/compare.py --save    # saves charts to results/charts/
```

---

## CompanyState vector
- **DIRECT** — parsed directly from the company's financial XLS files (income statement, balance sheet, cash flow, segment revenue). These are exact figures from the real earnings data.
- **CLAUDE-DERIVED** — extracted by Prompt C from qualitative documents (earnings transcript, press release, product release list) and quantified on a 1–10 scale.
- **MIXED** — some fields in the section come from direct data, others are Claude-derived. See inline comments for which is which.
```python
CompanyState = {
    "Financials": {          # DIRECT 
        "revenue", "cost_of_revenue", "gross_margin",
        "operating_income", "net_income", "cash_and_equivalents",
        "total_operating_expenses", "rd_spending",
        "sales_marketing_spending", "capex"
    },
    "Segments": {            # DIRECT 
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

30 actions across 8 categories: R&D Investment, Innovation Index, Revenue, Brand Strength, Headcount, Operating Cost, Cash Reserves, and Multi-category / Governance. Each AIE proposes up to 3 actions per quarter from this fixed list. The top 5 determined by the `FinalDecisionScore` are implemented each quarter.

---

## Known limitations

**Cash modeling** is the weakest dimension. The ActionLibrary does not include financing decisions (share buybacks, dividend payments, debt management) which the actual company actively used to manage cash. This accounts for the largest deltas in the comparison results.

**PPTX files** (earnings slides, outlook) for this company are fully image-based and yield no extractable text. Prompt C runs on the transcript, press release, and product list instead.

**Revenue is not projected forward.** Prompt B applies actions to operating variables (R&D, headcount, capex, margins) but does not produce a revenue forecast — revenue is a lagging result of decisions made over multiple quarters. The comparison treats each quarter's simulated financials as the direct output of that quarter's approved actions. Note -- the simulation is designed to compare strategic decision-making behavior e.g., what actions the board chose, how they allocated investment. This is not to be viewed as a financial forecasting model. 

**`total_employees`** is not available in quarterly earnings files and must be initially set manually in `config.py`. Simulated headcount compounds forward from each quarter's end state across the four-quarter run.

---

## Research questions

1. Does an AI-simulated C-suite produce decisions measurably different from its human-led counterpart?
2. Do those decisions lead to better, worse, or statistically indistinguishable simulated outcomes?
3. *(Optional)* Does multi-agent executive communication improve decision quality?

*Submitted to SIGBOVIK 2026.*