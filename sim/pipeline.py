"""
sim/pipeline.py

Orchestrates the full quarterly simulation loop.

Flow per quarter:
  1. Load CompanyState — seeded from FY22Q4 (real parsed data).
     Each subsequent quarter uses the previous quarter's simulated end state.
     No real FY2023 data is used during the simulation.
  2. Prompt D — each of 10 AIEs proposes up to 3 actions
  3. Deduplicate proposals across all agents
  4. Prompt A — predict Effect_i(a) for each unique action
  5. Voting engine — AES → vote direction → AWS → FinalDecisionScore
  6. Select top-K passing actions
  7. Prompt B — apply approved actions → updated CompanyState
  8. Write results log to results/<QUARTER>_simulation_log.json

Entry points:
  run_quarter(quarter)  — simulate one quarter, returns QuarterLog
  run_simulation()      — simulate all four FY2023 quarters in sequence,
                          seeded from FY22Q4 and carrying simulated state
                          forward after each quarter
"""

from __future__ import annotations
import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path

import anthropic

from config import (
    ANTHROPIC_API_KEY, MODEL, MAX_TOKENS,
    DATA_PROCESSED, RESULTS_DIR,
    SIMULATION_QUARTERS, DECISION_THRESHOLD, TOP_K_ACTIONS,
)
from agents.board import BOARD
from sim.action_library import ACTION_PRIMARY_CATEGORY
from sim.voting_engine import score_action, select_top_actions, ActionResult
from prompts.prompt_d_aie_proposal import build_prompt_d
from prompts.prompt_a_effect_prediction import build_prompt_a
from prompts.prompt_b_state_transition import build_prompt_b


# ── External context per quarter ───────────────────────────────────────────────
EXTERNAL_CONTEXT: dict[str, str] = {
    "FY23Q1": (
        "ChatGPT launched November 2022 and has rapidly entered mainstream "
        "awareness. Generative AI is at Peak of Inflated Expectations on the "
        "Gartner Hype Cycle. Cloud competitors accelerating AI infrastructure "
        "investments. Enterprise software spending showing mixed signals amid "
        "rising interest rates."
    ),
    "FY23Q2": (
        "Generative AI investment accelerating across the industry. Multiple "
        "large cloud providers announcing major AI partnerships and model "
        "integrations. EU AI Act advancing through legislative process. "
        "Enterprise AI adoption conversations increasing significantly."
    ),
    "FY23Q3": (
        "AI hype cycle remains elevated; analyst focus shifting to ROI and "
        "production deployment. Competitive intensity in cloud AI services "
        "increasing. Global enterprise IT spending cautious amid macro "
        "uncertainty. Workforce automation discussions intensifying."
    ),
    "FY23Q4": (
        "End of fiscal year; investor focus on full-year guidance and outlook. "
        "AI infrastructure buildout (datacenters, GPU procurement) becoming "
        "major capex story. Copilot and AI assistant products entering "
        "enterprise market at scale. Regulatory scrutiny of large tech "
        "companies continuing globally."
    ),
}


# ── Dataclasses ────────────────────────────────────────────────────────────────

@dataclass
class QuarterLog:
    quarter:             str
    company_state_start: dict
    proposals:           dict
    effects:             dict
    action_results:      list
    approved_actions:    list[str]
    company_state_end:   dict


# ── Anthropic helper ───────────────────────────────────────────────────────────

def _call_claude(prompt: dict) -> dict:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=prompt["system"],
        messages=[{"role": "user", "content": prompt["user"]}],
    )
    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        raw = raw.rsplit("```", 1)[0]
    return json.loads(raw.strip())


# ── Action category lookup ─────────────────────────────────────────────────────

def _get_action_category(action_name: str) -> str:
    for action_enum, category in ACTION_PRIMARY_CATEGORY.items():
        if action_enum.value == action_name:
            return category
    return "revenue"


# ── Per-quarter simulation ─────────────────────────────────────────────────────

def run_quarter(
    quarter: str,
    verbose: bool = True,
    state_override: dict | None = None,
) -> QuarterLog:
    """
    Run one full quarterly simulation cycle.

    Args:
        quarter:        Quarter string e.g. "FY23Q1"
        verbose:        Print progress to terminal
        state_override: If provided, use this CompanyState instead of loading
                        from data/processed/. Used by run_simulation() to carry
                        the previous quarter's simulated end state forward.
                        When None, loads real parsed data from data/processed/.
    """
    def log(msg: str):
        if verbose:
            print(f"  [{quarter}] {msg}")

    # ── Load CompanyState ──────────────────────────────────────────────────────
    if state_override is not None:
        company_state = state_override
        company_state["quarter"] = quarter
        log(f"Using carry-forward state — revenue={company_state.get('Financials', {}).get('revenue', 0):,.0f}M")
    else:
        state_path = DATA_PROCESSED / f"{quarter}_company_state.json"
        if not state_path.exists():
            raise FileNotFoundError(
                f"CompanyState not found: {state_path}\n"
                f"Run: python main.py  to generate it first."
            )
        company_state = json.loads(state_path.read_text())
        log(f"Loaded real parsed state — revenue={company_state.get('Financials', {}).get('revenue', 0):,.0f}M")

    external_context = EXTERNAL_CONTEXT.get(quarter, "No external context available.")

    # ── Prompt D: proposal phase ───────────────────────────────────────────────
    log("Prompt D — AIE proposal phase...")
    all_proposals: dict[str, list[str]] = {}
    candidate_actions: set[str] = set()

    for agent in BOARD:
        prompt = build_prompt_d(agent, company_state, external_context)
        result = _call_claude(prompt)
        actions = [p["action"] for p in result.get("proposed_actions", [])]
        all_proposals[agent.title] = actions
        candidate_actions.update(actions)
        log(f"  {agent.title[:40]} -> {actions}")
        time.sleep(0.3)

    log(f"  {len(candidate_actions)} unique candidate actions from {len(BOARD)} agents")

    # ── Prompt A: effect prediction ────────────────────────────────────────────
    log("Prompt A — effect prediction...")
    effects_map: dict[str, dict] = {}

    for action_name in sorted(candidate_actions):
        prompt = build_prompt_a(company_state, action_name)
        result = _call_claude(prompt)
        effects_map[action_name] = result.get("effects", {})
        log(f"  {action_name}: {result.get('rationale', '')[:80]}...")
        time.sleep(0.3)

    # ── Voting engine ──────────────────────────────────────────────────────────
    log("Voting engine — AES -> AWS -> DecisionScore...")
    action_results: list[ActionResult] = []

    for action_name, effects in effects_map.items():
        category = _get_action_category(action_name)
        result = score_action(action_name, category, effects, BOARD)
        action_results.append(result)
        log(f"  {action_name}: score={result.final_decision_score:.1f} passed={result.passed}")

    # ── Select top-K ──────────────────────────────────────────────────────────
    top_actions = select_top_actions(action_results)
    approved_action_names = [r.action for r in top_actions]
    log(f"Approved actions (top {TOP_K_ACTIONS}): {approved_action_names}")

    # ── Prompt B: state transition ─────────────────────────────────────────────
    log("Prompt B — state transition...")
    prompt = build_prompt_b(company_state, approved_action_names, external_context)
    updated_state = _call_claude(prompt)
    updated_state["quarter"] = f"{quarter}_end"
    log(f"  Updated revenue={updated_state.get('Financials', {}).get('revenue', 0):,.0f}M")

    # ── Build and write log ────────────────────────────────────────────────────
    log_entry = QuarterLog(
        quarter=quarter,
        company_state_start=company_state,
        proposals=all_proposals,
        effects=effects_map,
        action_results=[asdict(r) for r in action_results],
        approved_actions=approved_action_names,
        company_state_end=updated_state,
    )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = RESULTS_DIR / f"{quarter}_simulation_log.json"
    log_path.write_text(json.dumps(asdict(log_entry), indent=2))
    log(f"Log written -> {log_path.name}")

    return log_entry


# ── Full FY2023 simulation ─────────────────────────────────────────────────────

def run_simulation(verbose: bool = True) -> list[QuarterLog]:
    """
    Simulate all four FY2023 quarters in sequence.

    Seeds from FY22Q4 parsed data — the only real data used.
    Each quarter's end state is passed as the next quarter's starting state.
    No real FY2023 data is loaded at any point during the simulation.
    """
    print("\n" + "=" * 60)
    print("  C-Suite Simulation — FY2023")
    print("=" * 60)

    # ── Seed from FY22Q4 ──────────────────────────────────────────────────────
    seed_path = DATA_PROCESSED / "FY22Q4_company_state.json"
    if not seed_path.exists():
        raise FileNotFoundError(
            f"Seed state not found: {seed_path}\n"
            f"Run: python main.py  to generate it first."
        )
    next_state: dict = json.loads(seed_path.read_text())
    print(f"\n  Seeded from FY22Q4 — revenue={next_state.get('Financials', {}).get('revenue', 0):,.0f}M")

    all_logs: list[QuarterLog] = []

    for quarter in SIMULATION_QUARTERS:
        print(f"\n{'─' * 60}")
        print(f"  Simulating {quarter}")
        print(f"{'─' * 60}")

        log_entry = run_quarter(
            quarter,
            verbose=verbose,
            state_override=next_state,
        )
        all_logs.append(log_entry)

        # Carry this quarter's simulated end state into the next quarter
        next_state = log_entry.company_state_end

    print("\n" + "=" * 60)
    print("  Simulation complete.")
    print(f"  Logs written to: {RESULTS_DIR}")
    print("=" * 60)

    return all_logs