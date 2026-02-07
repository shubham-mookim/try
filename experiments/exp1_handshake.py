#!/usr/bin/env python3
"""
Experiment 1: The Basic Handshake

Goal: Two agents successfully negotiate and transfer compute.

Setup:
  - Agent A: has budget, needs GPU hours
  - Agent B: has GPU hours, needs budget

We try every strategy combination and see which pairs reach deals.
Then run 100 rounds with the same pair and track convergence.

Success metric: Agents reach agreement more often than random chance.
"""

import sys
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents import (
    Agent, Resource, Message, MessageType,
    GreedyStrategy, FairStrategy, PatientStrategy, AdaptiveStrategy,
)
from agents.simulator import Simulator


def run_single_negotiation(strategy_a, strategy_b, seed=42):
    """Run one negotiation between two agents with given strategies."""
    buyer = Agent(
        agent_id="buyer",
        resources=Resource(),  # no compute
        budget=20.0,
        strategy=strategy_a,
        urgency=0.7,
        pending_needs=Resource(gpu_hours=10),
    )
    seller = Agent(
        agent_id="seller",
        resources=Resource(gpu_hours=50),  # has compute
        budget=5.0,
        strategy=strategy_b,
        urgency=0.2,
    )

    sim = Simulator([buyer, seller], max_negotiation_turns=8, seed=seed)
    sim.run_round(pairings=[("buyer", "seller")])
    return sim


def strategy_matrix():
    """Test all strategy combinations."""
    strategies = {
        "greedy": lambda: GreedyStrategy(),
        "fair": lambda: FairStrategy(),
        "patient": lambda: PatientStrategy(),
        "adaptive": lambda: AdaptiveStrategy(),
    }

    print("=== Strategy Matrix: Deal Success ===\n")
    label = "buyer \\ seller"
    header = f"{label:<20}" + "".join(f"{name:<12}" for name in strategies)
    print(header)
    print("-" * len(header))

    results = {}
    for buyer_name, buyer_factory in strategies.items():
        row = f"{buyer_name:<20}"
        for seller_name, seller_factory in strategies.items():
            # Run 50 trials with different seeds
            deals = 0
            for seed in range(50):
                sim = run_single_negotiation(buyer_factory(), seller_factory(), seed=seed)
                if any(r.agreed for r in sim.results):
                    deals += 1
            pct = deals / 50
            results[(buyer_name, seller_name)] = pct
            row += f"{pct:>8.0%}    "
        print(row)

    print()
    return results


def convergence_test():
    """
    Run 100 rounds between adaptive agents and see if price converges.
    This is the interesting part - do they find a stable price?
    """
    print("=== Convergence Test: Two Adaptive Agents ===\n")

    buyer = Agent(
        agent_id="adaptive_buyer",
        resources=Resource(),
        budget=200.0,  # enough for many rounds
        strategy=AdaptiveStrategy(price_belief=0.5),  # starts with low belief
        urgency=0.6,
    )
    seller = Agent(
        agent_id="adaptive_seller",
        resources=Resource(gpu_hours=500),  # lots of compute
        budget=10.0,
        strategy=AdaptiveStrategy(price_belief=1.5),  # starts with high belief
        urgency=0.3,
    )

    sim = Simulator([buyer, seller], max_negotiation_turns=8, seed=42)
    need = Resource(gpu_hours=5)

    prices = []
    for i in range(100):
        buyer.pending_needs = Resource(gpu_hours=5)
        sim.run_round(pairings=[("adaptive_buyer", "adaptive_seller")])

        last = sim.results[-1]
        if last.agreed:
            prices.append(last.price)

    print(f"Deals made: {len(prices)} / 100")
    if prices:
        print(f"First 5 prices:  {[f'{p:.2f}' for p in prices[:5]]}")
        print(f"Last 5 prices:   {[f'{p:.2f}' for p in prices[-5:]]}")
        print(f"Price range:     {min(prices):.2f} - {max(prices):.2f}")
        print(f"Mean price:      {sum(prices)/len(prices):.2f}")

        # Check convergence: is the std dev of last 20 < first 20?
        if len(prices) >= 40:
            early_std = _std(prices[:20])
            late_std = _std(prices[-20:])
            print(f"\nEarly volatility (first 20):  {early_std:.4f}")
            print(f"Late volatility (last 20):    {late_std:.4f}")
            if late_std < early_std:
                print("-> Price is CONVERGING (less volatile over time)")
            else:
                print("-> Price is NOT converging (still volatile)")

    print()
    print(sim.summary())
    return prices


def _std(values):
    mean = sum(values) / len(values)
    return (sum((v - mean) ** 2 for v in values) / len(values)) ** 0.5


def message_trace():
    """Show the actual messages exchanged in one negotiation."""
    print("=== Message Trace: Fair vs Greedy ===\n")

    sim = run_single_negotiation(FairStrategy(), GreedyStrategy(), seed=7)
    result = sim.results[0]

    for msg in result.messages:
        direction = "->" if msg.sender_id == "buyer" else "<-"
        print(f"  {direction} {msg.msg_type.value:>8}  {msg.payload}")

    print(f"\n  Outcome: {'DEAL' if result.agreed else 'NO DEAL'}")
    if result.agreed:
        print(f"  Resource: {result.resource}")
        print(f"  Price: {result.price:.2f}")
    print()


if __name__ == "__main__":
    print("=" * 60)
    print("  EXPERIMENT 1: THE BASIC HANDSHAKE")
    print("=" * 60)
    print()

    message_trace()
    strategy_matrix()
    prices = convergence_test()
