"""
test/test_prompt_d.py

Tests Prompt D against a single AIE agent using your real FY22Q4
CompanyState JSON. Makes one real API call.

Usage:
    python test/test_prompt_d.py                    # tests CEO (default)
    python test/test_prompt_d.py --agent CFO        # tests CFO
    python test/test_prompt_d.py --agent CTO        # tests CTO
    python test/test_prompt_d.py --all              # tests all 10 agents

What it checks:
  - Response is valid JSON
  - Proposed actions are all in the ActionLibrary
  - Rationale fields are non-empty strings
  - agent and quarter fields are present
"""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import anthropic
from config import ANTHROPIC_API_KEY, MODEL, MAX_TOKENS, DATA_PROCESSED
from agents.board import BOARD
from sim.action_library import ALL_ACTION_NAMES
from prompts.prompt_d_aie_proposal import build_prompt_d

EXTERNAL_CONTEXT_FY22Q4 = (
    "End of fiscal year 2022. Rising interest rates and macro uncertainty "
    "affecting enterprise IT spending. Cloud growth remains strong but "
    "showing early signs of normalization. ChatGPT has not yet launched — "
    "generative AI is not yet a mainstream enterprise topic. "
    "Competitive pressure from AWS and Google Cloud intensifying."
)


def call_claude(prompt: dict) -> dict:
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


def load_state(quarter: str) -> dict:
    path = DATA_PROCESSED / f"{quarter}_company_state.json"
    if not path.exists():
        print(f"  ✗ CompanyState not found: {path}")
        print(f"    Run: python main.py --dry-run  (or without --dry-run for full parse)")
        sys.exit(1)
    return json.loads(path.read_text())


def test_agent(agent, state: dict, verbose: bool = True) -> bool:
    print(f"\n  [{agent.title}]")

    prompt = build_prompt_d(agent, state, EXTERNAL_CONTEXT_FY22Q4)

    # Sanity check prompt structure before calling API
    assert "system" in prompt and "user" in prompt, "prompt missing system or user key"
    assert agent.title in prompt["system"], "agent title not in system prompt"
    assert "proposed_actions" in prompt["user"], "response format missing from user prompt"
    assert "increase_rd_5" in prompt["system"], "ActionLibrary missing from system prompt"

    print(f"  Calling Claude... ", end="", flush=True)
    result = call_claude(prompt)
    print("done")

    # Validate response structure
    ok = True

    if "proposed_actions" not in result:
        print(f"  ✗ Missing 'proposed_actions' key")
        return False

    proposals = result["proposed_actions"]

    if not isinstance(proposals, list) or len(proposals) == 0:
        print(f"  ✗ proposed_actions is empty or not a list")
        return False

    if len(proposals) > 3:
        print(f"  ✗ Too many proposals: {len(proposals)} (max 3)")
        ok = False

    for i, p in enumerate(proposals):
        action = p.get("action", "")
        rationale = p.get("rationale", "")

        if action not in ALL_ACTION_NAMES:
            print(f"  ✗ Proposal {i+1}: '{action}' not in ActionLibrary")
            ok = False
        else:
            print(f"  ✓ Proposal {i+1}: {action}")

        if not rationale or len(rationale.strip()) < 20:
            print(f"    ✗ Rationale too short or missing")
            ok = False
        else:
            if verbose:
                print(f"    → {rationale[:120]}...")

    if result.get("agent") != agent.title:
        print(f"  ✗ agent field mismatch: got '{result.get('agent')}'")
        ok = False

    if not result.get("quarter"):
        print(f"  ✗ quarter field missing")
        ok = False

    return ok


def main():
    parser = argparse.ArgumentParser(description="Test Prompt D — AIE proposal phase")
    parser.add_argument("--agent", type=str, default="CEO",
                        help="Agent title keyword to test (e.g. CEO, CFO, CTO)")
    parser.add_argument("--all", action="store_true",
                        help="Test all 10 agents")
    parser.add_argument("--quarter", type=str, default="FY22Q4",
                        help="Which CompanyState JSON to use (default: FY22Q4)")
    args = parser.parse_args()

    if not ANTHROPIC_API_KEY:
        print("Error: ANTHROPIC_API_KEY not set.")
        sys.exit(1)

    state = load_state(args.quarter)
    print(f"\nPrompt D Test — quarter={args.quarter}")
    print(f"Revenue: {state.get('Financials', {}).get('revenue', 0):,.0f}M")
    print("=" * 55)

    if args.all:
        agents_to_test = BOARD
    else:
        agents_to_test = [
            a for a in BOARD if args.agent.upper() in a.title.upper()
        ]
        if not agents_to_test:
            print(f"No agent found matching '{args.agent}'")
            print(f"Available: {[a.title for a in BOARD]}")
            sys.exit(1)

    results = []
    for agent in agents_to_test:
        passed = test_agent(agent, state)
        results.append((agent.title, passed))

    print(f"\n{'=' * 55}")
    passed_count = sum(1 for _, p in results if p)
    print(f"  {passed_count}/{len(results)} agents passed")

    for title, passed in results:
        status = "✓" if passed else "✗"
        print(f"  {status}  {title}")


if __name__ == "__main__":
    main()