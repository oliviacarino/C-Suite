"""
util/compare.py

Compares simulated C-Suite decisions against actual FY2023 results
across four metrics: revenue, profit margin, cash, and headcount.

For each quarter, the comparison is:
  Simulated end state  → company_state_end from results/<Q>_simulation_log.json
  Actual end state     → Financials from data/processed/<next_Q>_company_state.json
                         (the next quarter's real starting state = this quarter's
                          actual ending state)

Usage:
    python util/compare.py
    python util/compare.py --save          # save charts to results/charts/
    python util/compare.py --metric revenue  # single metric only
"""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

from config import DATA_PROCESSED, RESULTS_DIR, SIMULATION_QUARTERS

# Quarter sequence — used to look up "actual end state" as next quarter's start
QUARTER_SEQUENCE = ["FY23Q1", "FY23Q2", "FY23Q3", "FY23Q4", "FY24Q1"]

# Actual FY2023 end-of-quarter headcount (from public annual reports)
# Used as ground truth since headcount isn't in quarterly financial files
ACTUAL_HEADCOUNT: dict[str, int] = {
    "FY23Q1": 221000,
    "FY23Q2": 221000,
    "FY23Q3": 228000,
    "FY23Q4": 238000,
}


# ── Data loading ───────────────────────────────────────────────────────────────

def load_simulation_log(quarter: str) -> dict:
    path = RESULTS_DIR / f"{quarter}_simulation_log.json"
    if not path.exists():
        raise FileNotFoundError(f"Simulation log not found: {path}")
    return json.loads(path.read_text())


def load_company_state(quarter: str) -> dict:
    path = DATA_PROCESSED / f"{quarter}_company_state.json"
    if not path.exists():
        raise FileNotFoundError(f"CompanyState not found: {path}")
    return json.loads(path.read_text())


def get_actual_end_state(quarter: str) -> dict:
    """
    The actual end state for a quarter is the real CompanyState
    of the following quarter (its starting financials = previous quarter's actuals).
    For FY23Q4 we use the FY23Q4 state itself as best available proxy.
    """
    idx = QUARTER_SEQUENCE.index(quarter)
    next_quarter = QUARTER_SEQUENCE[idx + 1] if idx + 1 < len(QUARTER_SEQUENCE) else quarter
    try:
        return load_company_state(next_quarter)
    except FileNotFoundError:
        return load_company_state(quarter)


# ── Metric extraction ──────────────────────────────────────────────────────────

def extract_metrics(state: dict) -> dict:
    fin = state.get("Financials", {})
    hi  = state.get("Human_Impacts", {})
    revenue = fin.get("revenue", 0)
    op_income = fin.get("operating_income", 0)
    return {
        "revenue":       revenue,
        "profit_margin": round((op_income / revenue * 100), 2) if revenue else 0,
        "cash":          fin.get("cash_and_equivalents", 0),
        "headcount":     hi.get("total_employees", 0),
    }


def build_comparison_table() -> list[dict]:
    """
    Build a list of per-quarter comparison dicts with simulated vs actual values.
    """
    rows = []
    for quarter in SIMULATION_QUARTERS:
        try:
            log = load_simulation_log(quarter)
        except FileNotFoundError:
            print(f"  [SKIP] No simulation log for {quarter}")
            continue

        sim_metrics   = extract_metrics(log["company_state_end"])
        actual_state  = get_actual_end_state(quarter)
        actual_metrics = extract_metrics(actual_state)

        # Override headcount with known actuals
        actual_metrics["headcount"] = ACTUAL_HEADCOUNT.get(quarter, actual_metrics["headcount"])

        rows.append({
            "quarter":        quarter,
            "simulated":      sim_metrics,
            "actual":         actual_metrics,
            "deltas": {
                k: round(sim_metrics[k] - actual_metrics[k], 2)
                for k in sim_metrics
            },
        })
    return rows


# ── Terminal table ─────────────────────────────────────────────────────────────

def print_table(rows: list[dict]):
    print("\n" + "=" * 72)
    print("  C-Suite Simulation vs Actual — FY2023")
    print("=" * 72)

    metrics = [
        ("revenue",       "Revenue (M)",       "${:,.0f}"),
        ("profit_margin", "Op. Margin (%)",    "{:.1f}%"),
        ("cash",          "Cash (M)",           "${:,.0f}"),
        ("headcount",     "Headcount",         "{:,.0f}"),
    ]

    for metric_key, label, fmt in metrics:
        print(f"\n  {label}")
        print(f"  {'Quarter':<10} {'Simulated':>14} {'Actual':>14} {'Delta':>14}")
        print(f"  {'─'*10} {'─'*14} {'─'*14} {'─'*14}")
        for row in rows:
            sim = row["simulated"][metric_key]
            act = row["actual"][metric_key]
            delta = row["deltas"][metric_key]
            sign = "+" if delta >= 0 else ""
            print(
                f"  {row['quarter']:<10} "
                f"{fmt.format(sim):>14} "
                f"{fmt.format(act):>14} "
                f"{sign}{fmt.format(delta):>13}"
            )

    print("\n" + "=" * 72)


# ── Charts ─────────────────────────────────────────────────────────────────────

METRIC_CONFIG = {
    "revenue": {
        "label": "Quarterly Revenue (USD millions)",
        "fmt":   lambda v: f"${v:,.0f}M",
        "scale": 1,
    },
    "profit_margin": {
        "label": "Operating Profit Margin (%)",
        "fmt":   lambda v: f"{v:.1f}%",
        "scale": 1,
    },
    "cash": {
        "label": "Cash & Equivalents (USD millions)",
        "fmt":   lambda v: f"${v:,.0f}M",
        "scale": 1,
    },
    "headcount": {
        "label": "Total Employees",
        "fmt":   lambda v: f"{v:,.0f}",
        "scale": 1,
    },
}


def plot_comparison(rows: list[dict], save_dir: Path | None = None):
    quarters = [r["quarter"] for r in rows]
    metrics  = list(METRIC_CONFIG.keys())
    n        = len(metrics)

    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    fig.suptitle(
        "C-Suite Simulation vs Actual — FY2023",
        fontsize=15, fontweight="bold", y=0.98,
    )

    colors = {
        "simulated": "#4A90D9",
        "actual":    "#E8593C",
    }
    bar_width = 0.35
    x = np.arange(len(quarters))

    for ax, metric_key in zip(axes.flat, metrics):
        cfg = METRIC_CONFIG[metric_key]

        sim_vals = [r["simulated"][metric_key] for r in rows]
        act_vals = [r["actual"][metric_key]    for r in rows]

        bars_sim = ax.bar(
            x - bar_width / 2, sim_vals, bar_width,
            label="Simulated", color=colors["simulated"], alpha=0.85,
        )
        bars_act = ax.bar(
            x + bar_width / 2, act_vals, bar_width,
            label="Actual", color=colors["actual"], alpha=0.85,
        )

        ax.set_title(cfg["label"], fontsize=11, fontweight="bold", pad=8)
        ax.set_xticks(x)
        ax.set_xticklabels(quarters, fontsize=9)
        ax.yaxis.set_major_formatter(
            mticker.FuncFormatter(
                lambda v, _: f"{v/1e3:.0f}K" if metric_key == "headcount"
                else f"${v/1e3:.0f}B" if v >= 1e5
                else f"{v:.1f}%" if metric_key == "profit_margin"
                else f"${v:,.0f}M"
            )
        )
        ax.legend(fontsize=9)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.tick_params(axis="y", labelsize=9)

        # Delta annotations above bars
        for i, (s, a) in enumerate(zip(sim_vals, act_vals)):
            delta = s - a
            sign  = "+" if delta >= 0 else ""
            label = cfg["fmt"](delta)
            ax.annotate(
                f"{sign}{label}",
                xy=(i, max(s, a)),
                ha="center", va="bottom",
                fontsize=7.5,
                color="#444",
            )

    plt.tight_layout(rect=[0, 0, 1, 0.96])

    if save_dir:
        save_dir.mkdir(parents=True, exist_ok=True)
        out = save_dir / "comparison_charts.png"
        plt.savefig(out, dpi=150, bbox_inches="tight")
        print(f"\n  Charts saved → {out}")
    else:
        plt.show()


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Compare simulation vs actuals")
    parser.add_argument("--save", action="store_true",
                        help="Save charts to results/charts/ instead of displaying")
    parser.add_argument("--metric", type=str, default=None,
                        choices=list(METRIC_CONFIG.keys()),
                        help="Show only one metric")
    args = parser.parse_args()

    rows = build_comparison_table()

    if not rows:
        print("No simulation logs found. Run: python main.py --simulate")
        sys.exit(1)

    print_table(rows)

    if args.metric:
        filtered = [
            {**r,
             "simulated": {args.metric: r["simulated"][args.metric]},
             "actual":    {args.metric: r["actual"][args.metric]},
             "deltas":    {args.metric: r["deltas"][args.metric]},
             }
            for r in rows
        ]
        # rebuild for single metric plot
        single_rows = rows  # pass full rows, chart filters by metric key

    save_dir = RESULTS_DIR / "charts" if args.save else None
    plot_comparison(rows, save_dir=save_dir)

    # Write comparison JSON
    out_path = RESULTS_DIR / "comparison_results.json"
    out_path.write_text(json.dumps(rows, indent=2))
    print(f"  Comparison data → {out_path.name}\n")


if __name__ == "__main__":
    main()