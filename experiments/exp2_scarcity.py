#!/usr/bin/env python3
"""
Experiment 2: Scarcity Games

Goal: See what strategies emerge under resource pressure.

Setup:
  - 5 agents with different strategies and resource levels
  - 3 have compute (providers), 2 need it (seekers)
  - Run 100 rounds
  - Track who gets what and why

Key questions:
  - Which strategy wins under scarcity?
  - Do agents naturally form partnerships?
  - What happens during "rush hour"?
"""

import sys
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents import (
    Agent, Resource,
    GreedyStrategy, FairStrategy, PatientStrategy, AdaptiveStrategy, BrokerStrategy,
)
from agents.simulator import Simulator


def setup_agents():
    """Create 5 agents with different strategies and endowments."""
    return [
        # Providers (have compute)
        Agent(
            agent_id="greedy_provider",
            resources=Resource(gpu_hours=100, cpu_hours=50),
            budget=10.0,
            strategy=GreedyStrategy(greed_factor=0.6),
            urgency=0.1,
        ),
        Agent(
            agent_id="fair_provider",
            resources=Resource(gpu_hours=80, cpu_hours=80),
            budget=15.0,
            strategy=FairStrategy(),
            urgency=0.2,
        ),
        Agent(
            agent_id="patient_provider",
            resources=Resource(gpu_hours=120, cpu_hours=30),
            budget=5.0,
            strategy=PatientStrategy(patience=0.9),
            urgency=0.1,
        ),
        # Seekers (need compute)
        Agent(
            agent_id="adaptive_seeker",
            resources=Resource(gpu_hours=5),
            budget=100.0,
            strategy=AdaptiveStrategy(price_belief=1.0),
            urgency=0.8,
        ),
        Agent(
            agent_id="greedy_seeker",
            resources=Resource(gpu_hours=5),
            budget=80.0,
            strategy=GreedyStrategy(greed_factor=0.5),
            urgency=0.9,
        ),
    ]


def run_scarcity_sim(rounds=100, seed=42):
    """Run the scarcity simulation."""
    agents = setup_agents()
    sim = Simulator(agents, max_negotiation_turns=6, seed=seed, log_dir="logs")

    seeker_ids = ["adaptive_seeker", "greedy_seeker"]
    need = Resource(gpu_hours=8, cpu_hours=4)

    # Track metrics over time
    deal_counts = {aid: 0 for aid in seeker_ids}
    total_spent = {aid: 0.0 for aid in seeker_ids}
    resources_acquired = {aid: 0.0 for aid in seeker_ids}
    prices_over_time = []

    for round_num in range(rounds):
        # Both seekers need compute each round
        needs = {sid: Resource(gpu_hours=8, cpu_hours=4) for sid in seeker_ids}
        for sid in seeker_ids:
            sim.agents[sid].pending_needs = needs[sid]

        metrics = sim.run_round(needs=needs)

        # Analyze this round's results
        round_prices = []
        for result in sim.results[-(metrics.negotiations):]:
            if result.agreed and result.resource:
                deal_counts[result.buyer_id] = deal_counts.get(result.buyer_id, 0) + 1
                total_spent[result.buyer_id] = total_spent.get(result.buyer_id, 0) + result.price
                resources_acquired[result.buyer_id] = resources_acquired.get(result.buyer_id, 0) + result.resource.total_units()
                round_prices.append(result.price / result.resource.total_units())

        if round_prices:
            prices_over_time.append(sum(round_prices) / len(round_prices))
        else:
            prices_over_time.append(None)

    return sim, deal_counts, total_spent, resources_acquired, prices_over_time


def run_rush_hour(seed=42):
    """
    Simulate a "rush hour" scenario where all agents suddenly need compute.
    Even providers now have urgent needs.
    """
    agents = setup_agents()
    sim = Simulator(agents, max_negotiation_turns=6, seed=seed)

    print("=== Rush Hour Scenario ===\n")
    print("Rounds 1-10: Normal operation (2 seekers)")
    print("Rounds 11-20: RUSH HOUR (everyone needs compute)")
    print("Rounds 21-30: Back to normal\n")

    seeker_ids = ["adaptive_seeker", "greedy_seeker"]
    all_ids = [a.agent_id for a in agents]

    phase_stats = {"normal_1": [], "rush": [], "normal_2": []}

    for round_num in range(30):
        if round_num < 10:
            phase = "normal_1"
            needs = {sid: Resource(gpu_hours=5) for sid in seeker_ids}
        elif round_num < 20:
            phase = "rush"
            # Everyone needs compute!
            needs = {aid: Resource(gpu_hours=8) for aid in all_ids}
        else:
            phase = "normal_2"
            needs = {sid: Resource(gpu_hours=5) for sid in seeker_ids}

        for aid in all_ids:
            sim.agents[aid].pending_needs = needs.get(aid, Resource())

        metrics = sim.run_round(needs=needs)
        phase_stats[phase].append(metrics)

    # Report
    for phase_name, metrics_list in phase_stats.items():
        deals = sum(m.deals_made for m in metrics_list)
        negs = sum(m.negotiations for m in metrics_list)
        avg_price = [m.avg_price_per_unit for m in metrics_list if m.avg_price_per_unit > 0]
        print(f"Phase: {phase_name}")
        print(f"  Negotiations: {negs}, Deals: {deals} ({deals/max(negs,1):.0%} success)")
        if avg_price:
            print(f"  Avg price/unit: {sum(avg_price)/len(avg_price):.2f}")
        print()

    return sim


def strategy_tournament(num_trials=20):
    """
    Run many simulations and rank strategies by total wealth accumulated.
    """
    print("=== Strategy Tournament (20 trials) ===\n")

    wealth_totals = {}

    for trial in range(num_trials):
        agents = setup_agents()
        sim = Simulator(agents, max_negotiation_turns=6, seed=trial)

        seeker_ids = ["adaptive_seeker", "greedy_seeker"]
        for _ in range(50):
            needs = {sid: Resource(gpu_hours=5, cpu_hours=3) for sid in seeker_ids}
            for sid in seeker_ids:
                sim.agents[sid].pending_needs = needs[sid]
            sim.run_round(needs=needs)

        for agent in sim.agents.values():
            if agent.agent_id not in wealth_totals:
                wealth_totals[agent.agent_id] = []
            wealth_totals[agent.agent_id].append(agent.net_worth())

    # Rank by average wealth
    rankings = sorted(
        wealth_totals.items(),
        key=lambda x: sum(x[1]) / len(x[1]),
        reverse=True,
    )

    print(f"{'Agent':<22} {'Avg Worth':>10} {'Min':>8} {'Max':>8}")
    print("-" * 52)
    for agent_id, worths in rankings:
        avg = sum(worths) / len(worths)
        print(f"{agent_id:<22} {avg:>10.1f} {min(worths):>8.1f} {max(worths):>8.1f}")
    print()

    return rankings


if __name__ == "__main__":
    print("=" * 60)
    print("  EXPERIMENT 2: SCARCITY GAMES")
    print("=" * 60)
    print()

    # Part 1: Basic scarcity simulation
    print("=== 100-Round Scarcity Simulation ===\n")
    sim, deal_counts, total_spent, resources_acquired, prices = run_scarcity_sim()

    print("Seeker performance:")
    for sid in ["adaptive_seeker", "greedy_seeker"]:
        print(f"  {sid}:")
        print(f"    Deals made: {deal_counts.get(sid, 0)}")
        print(f"    Total spent: {total_spent.get(sid, 0):.1f}")
        acquired = resources_acquired.get(sid, 0)
        spent = total_spent.get(sid, 0)
        print(f"    Resources acquired: {acquired:.1f}")
        if acquired > 0:
            print(f"    Avg cost/unit: {spent / acquired:.2f}")
    print()
    print(sim.summary())
    print()

    # Part 2: Rush hour
    rush_sim = run_rush_hour()

    # Part 3: Tournament
    strategy_tournament()
