#!/usr/bin/env python3
"""
Visualization for experiment results.

Generates plots for:
  - Price convergence over time
  - Strategy performance comparison
  - Trust/reputation evolution
  - Resource distribution changes
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import matplotlib
    matplotlib.use("Agg")  # non-interactive backend
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("matplotlib not installed - skipping plots (pip install matplotlib)")


def plot_price_convergence(prices: list[float], filename: str = "price_convergence.png"):
    """Plot how prices evolve over negotiation rounds."""
    if not HAS_MATPLOTLIB or not prices:
        return

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

    # Price over time
    ax1.plot(prices, "b-", alpha=0.7, linewidth=1)
    ax1.set_xlabel("Round")
    ax1.set_ylabel("Deal Price")
    ax1.set_title("Price Over Time (Two Adaptive Agents)")

    # Rolling average
    window = min(10, len(prices) // 3) if len(prices) > 3 else 1
    rolling = [
        sum(prices[max(0, i - window):i + 1]) / len(prices[max(0, i - window):i + 1])
        for i in range(len(prices))
    ]
    ax1.plot(rolling, "r-", linewidth=2, label=f"Rolling avg (window={window})")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Volatility over time (rolling std dev)
    if len(prices) >= 10:
        volatility = []
        for i in range(len(prices)):
            window_data = prices[max(0, i - window):i + 1]
            mean = sum(window_data) / len(window_data)
            std = (sum((v - mean) ** 2 for v in window_data) / len(window_data)) ** 0.5
            volatility.append(std)
        ax2.plot(volatility, "g-", linewidth=1.5)
        ax2.set_xlabel("Round")
        ax2.set_ylabel("Price Volatility (Rolling Std Dev)")
        ax2.set_title("Volatility Over Time")
        ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(filename, dpi=150)
    plt.close()
    print(f"Saved: {filename}")


def plot_strategy_comparison(rankings: list[tuple[str, list[float]]], filename: str = "strategy_comparison.png"):
    """Bar chart comparing strategy performance."""
    if not HAS_MATPLOTLIB or not rankings:
        return

    fig, ax = plt.subplots(figsize=(10, 6))

    names = [r[0] for r in rankings]
    avgs = [sum(r[1]) / len(r[1]) for r in rankings]
    mins = [min(r[1]) for r in rankings]
    maxs = [max(r[1]) for r in rankings]
    errors = [[a - mn for a, mn in zip(avgs, mins)], [mx - a for a, mx in zip(avgs, maxs)]]

    colors = ["#2ecc71", "#3498db", "#e74c3c", "#f39c12", "#9b59b6"]
    bars = ax.bar(names, avgs, color=colors[:len(names)], alpha=0.8)
    ax.errorbar(names, avgs, yerr=errors, fmt="none", ecolor="black", capsize=5)

    ax.set_ylabel("Net Worth (avg over trials)")
    ax.set_title("Strategy Tournament Results")
    ax.grid(True, axis="y", alpha=0.3)

    # Rotate labels for readability
    plt.xticks(rotation=15, ha="right")
    plt.tight_layout()
    plt.savefig(filename, dpi=150)
    plt.close()
    print(f"Saved: {filename}")


def plot_reputation_evolution(
    rep_history: list[float],
    deals_history: list[int],
    filename: str = "reputation_evolution.png",
):
    """Plot how a cheater's reputation changes over time."""
    if not HAS_MATPLOTLIB or not rep_history:
        return

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

    # Reputation over time
    ax1.plot(rep_history, "r-", linewidth=2, label="Cheater's avg reputation")
    ax1.axhline(y=0.3, color="gray", linestyle="--", alpha=0.5, label="Trust threshold")
    ax1.axhline(y=0.5, color="blue", linestyle=":", alpha=0.3, label="Neutral (0.5)")
    ax1.set_xlabel("Round")
    ax1.set_ylabel("Average Reputation Score")
    ax1.set_title("Cheater's Reputation Over Time")
    ax1.legend()
    ax1.set_ylim(-0.05, 1.05)
    ax1.grid(True, alpha=0.3)

    # Deals per round
    ax2.bar(range(len(deals_history)), deals_history, alpha=0.7, color="orange")
    ax2.set_xlabel("Round")
    ax2.set_ylabel("Deals Involving Cheater")
    ax2.set_title("Cheater's Deal Activity")
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(filename, dpi=150)
    plt.close()
    print(f"Saved: {filename}")


if __name__ == "__main__":
    print("Run experiments first, then use these functions to visualize results.")
    print("Example:")
    print("  from experiments.exp1_handshake import convergence_test")
    print("  prices = convergence_test()")
    print("  plot_price_convergence(prices)")
