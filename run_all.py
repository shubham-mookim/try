#!/usr/bin/env python3
"""
Run all experiments and generate visualizations.

Usage:
    python run_all.py              # run everything
    python run_all.py 1            # run only experiment 1
    python run_all.py 2            # run only experiment 2
    python run_all.py 3            # run only experiment 3
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def run_exp1():
    print("\n" + "=" * 60)
    print("  EXPERIMENT 1: THE BASIC HANDSHAKE")
    print("=" * 60 + "\n")

    from experiments.exp1_handshake import message_trace, strategy_matrix, convergence_test
    from experiments.visualize import plot_price_convergence

    message_trace()
    strategy_matrix()
    prices = convergence_test()
    plot_price_convergence(prices, "logs/exp1_price_convergence.png")


def run_exp2():
    print("\n" + "=" * 60)
    print("  EXPERIMENT 2: SCARCITY GAMES")
    print("=" * 60 + "\n")

    from experiments.exp2_scarcity import run_scarcity_sim, run_rush_hour, strategy_tournament
    from experiments.visualize import plot_strategy_comparison

    print("--- 100-Round Scarcity Simulation ---\n")
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

    run_rush_hour()
    rankings = strategy_tournament()
    plot_strategy_comparison(rankings, "logs/exp2_strategy_tournament.png")


def run_exp3():
    print("\n" + "=" * 60)
    print("  EXPERIMENT 3: TRUST FALL")
    print("=" * 60 + "\n")

    from experiments.exp3_trust import run_cheater_detection
    from experiments.visualize import plot_reputation_evolution

    # Always-cheating
    print("--- Always-Cheating Mallory ---\n")
    sim, rep_history, deals_history = run_cheater_detection(cheater_prob=1.0)

    print("Cheater reputation over time:")
    for phase, s, e in [("Early (1-10)", 0, 10), ("Mid (25-35)", 24, 35), ("Late (50-60)", 49, 60)]:
        avg = sum(rep_history[s:e]) / len(rep_history[s:e])
        deals = sum(deals_history[s:e])
        print(f"  {phase}: rep={avg:.3f}, deals={deals}")

    print(f"\nCheating incidents: {len(sim.default_log)}")
    print(f"Final state: budget={sim.agents['cheater_mallory'].budget:.1f}, "
          f"resources={sim.agents['cheater_mallory'].resources}")

    print("\nHonest agents' view of Mallory:")
    for aid in sorted(sim.agents):
        if "cheater" not in aid:
            rep = sim.agents[aid].reputation_of("cheater_mallory")
            print(f"  {aid}: {rep:.3f}")

    plot_reputation_evolution(rep_history, deals_history, "logs/exp3_always_cheat.png")

    # Subtle cheater
    print("\n--- Subtle Mallory (5% cheat rate) ---\n")
    sim2, rep2, deals2 = run_cheater_detection(cheater_prob=0.05, rounds=100, seed=123)

    for phase, s, e in [("Early", 0, 20), ("Mid", 39, 60), ("Late", 79, 100)]:
        sl = rep2[s:e]
        if sl:
            print(f"  {phase}: rep={sum(sl)/len(sl):.3f}, deals={sum(deals2[s:e])}")

    plot_reputation_evolution(rep2, deals2, "logs/exp3_subtle_cheat.png")

    print(f"\n  Always cheat wealth: {sim.agents['cheater_mallory'].net_worth():.1f}")
    print(f"  5% cheat wealth:    {sim2.agents['cheater_mallory'].net_worth():.1f}")


def main():
    Path("logs").mkdir(exist_ok=True)

    if len(sys.argv) > 1:
        exp = sys.argv[1]
        if exp == "1":
            run_exp1()
        elif exp == "2":
            run_exp2()
        elif exp == "3":
            run_exp3()
        else:
            print(f"Unknown experiment: {exp}. Use 1, 2, or 3.")
    else:
        run_exp1()
        run_exp2()
        run_exp3()

    print("\n" + "=" * 60)
    print("  ALL EXPERIMENTS COMPLETE")
    print("=" * 60)
    print("\nCheck logs/ for plots and data.")


if __name__ == "__main__":
    main()
