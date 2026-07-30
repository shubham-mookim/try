#!/usr/bin/env python3
"""
Experiment 16: Negotiation Overhead vs Workload Runtime

Directly measures the question: how much compute/time does the NEGOTIATION
itself cost, versus the WORKLOAD it is allocating?

Three things measured on THIS machine:
  1. Tier-1 rule-based negotiation latency   (no GPU, no API — pure CPU logic)
  2. Tier-3 LLM bid-call latency             (one inference "decision")
  3. Real workload runtime at several sizes  (the thing being allocated)

Then we report the ratio  negotiation_time / workload_time  so we can see
where negotiation stops being worth it.

The LLM part needs OPENAI_API_KEY; without it, only tiers 1 and the workload
are measured.
"""

from __future__ import annotations

import os
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents import Agent, Resource, FairStrategy, AdaptiveStrategy
from agents.simulator import Simulator
from agents.workload import Job, execute_job, calibrate_iterations


def measure_rule_based_negotiation(reps: int = 2000) -> dict:
    """Time a full bilateral negotiation between two Tier-1 agents (no API)."""
    buyer = Agent(agent_id="b", resources=Resource(), budget=100.0,
                  strategy=AdaptiveStrategy(price_belief=1.0), urgency=0.7,
                  pending_needs=Resource(gpu_hours=5))
    seller = Agent(agent_id="s", resources=Resource(gpu_hours=100), budget=10.0,
                   strategy=FairStrategy(), urgency=0.2)
    sim = Simulator([buyer, seller], max_negotiation_turns=6, seed=0)
    need = Resource(gpu_hours=5)

    # warm up
    for _ in range(50):
        sim._negotiate(buyer, seller, need)

    t0 = time.perf_counter()
    for _ in range(reps):
        sim._negotiate(buyer, seller, need)
    dt = time.perf_counter() - t0
    return {"per_negotiation_s": dt / reps, "reps": reps}


def measure_llm_bid(samples: int = 12) -> dict | None:
    """Time one LLM bid-call — the 'decision' a Tier-3 agent makes."""
    if not os.environ.get("OPENAI_API_KEY"):
        return None
    from agents.llm_strategy import set_call_budget
    from experiments.exp12_llm_real_compute import llm_bid_for_job

    set_call_budget(samples + 5)
    job = Job(job_id="probe", cpu_iterations=640_000, mem_mb=32,
              urgency=0.7, budget=8.0)

    latencies, in_toks, out_toks = [], [], []
    for _ in range(samples):
        t0 = time.perf_counter()
        bid, usage = llm_bid_for_job(job, "openai", "gpt-4o-mini")
        latencies.append(time.perf_counter() - t0)
        in_toks.append(usage["in"])
        out_toks.append(usage["out"])

    latencies.sort()
    return {
        "samples": samples,
        "mean_s": statistics.mean(latencies),
        "p50_s": latencies[len(latencies) // 2],
        "p95_s": latencies[min(len(latencies) - 1, int(0.95 * len(latencies)))],
        "min_s": latencies[0],
        "max_s": latencies[-1],
        "in_tokens": statistics.mean(in_toks),
        "out_tokens": statistics.mean(out_toks),
    }


def measure_workload(iters_list: list[int], mem_mb: int = 32) -> list[dict]:
    """Run real jobs of increasing size; report actual wall time."""
    out = []
    for iters in iters_list:
        job = Job(job_id=f"job_{iters}", cpu_iterations=iters, mem_mb=mem_mb,
                  urgency=0.5, budget=5.0)
        r = execute_job(job)
        out.append({"iterations": iters, "wall_s": r["wall_seconds"],
                    "cpu_s": r["cpu_seconds"], "peak_mem_mb": r["peak_mem_kb"] / 1024})
    return out


def main():
    print("=" * 64)
    print("  EXPERIMENT 16: NEGOTIATION OVERHEAD vs WORKLOAD RUNTIME")
    print("=" * 64)
    print(f"\nHost: {os.cpu_count()} cores\n")

    # 1. Rule-based negotiation
    print("--- 1. Tier-1 rule-based negotiation (no GPU, no API) ---")
    rb = measure_rule_based_negotiation()
    rb_us = rb["per_negotiation_s"] * 1e6
    print(f"  Full 2-agent negotiation: {rb_us:.1f} microseconds "
          f"({rb['per_negotiation_s']*1e3:.4f} ms), avg of {rb['reps']} reps")
    print(f"  -> a Tier-1/2 agent 'decision' is essentially free.\n")

    # 2. LLM bid latency
    print("--- 2. Tier-3 LLM bid call (one inference decision) ---")
    llm = measure_llm_bid()
    if llm:
        print(f"  Latency: mean={llm['mean_s']*1e3:.0f} ms  "
              f"p50={llm['p50_s']*1e3:.0f} ms  p95={llm['p95_s']*1e3:.0f} ms  "
              f"(range {llm['min_s']*1e3:.0f}-{llm['max_s']*1e3:.0f} ms)")
        print(f"  Tokens: {llm['in_tokens']:.0f} in / {llm['out_tokens']:.0f} out "
              f"per decision")
        print(f"  NOTE: this is API round-trip (network+queue+inference), the")
        print(f"        number as-we-ran-it. Self-hosted pure inference is lower.\n")
    else:
        print("  (skipped — no OPENAI_API_KEY)\n")

    # 3. Real workload runtime
    print("--- 3. Real workload runtime (the thing being allocated) ---")
    base = calibrate_iterations(0.3)
    sizes = [base, base * 3, base * 10, base * 30]
    wl = measure_workload(sizes)
    print(f"  {'iterations':>12} {'wall_s':>10} {'cpu_s':>10}")
    for w in wl:
        print(f"  {w['iterations']:>12,} {w['wall_s']:>10.3f} {w['cpu_s']:>10.3f}")
    print()

    # 4. The ratio table
    print("=" * 64)
    print("  NEGOTIATION OVERHEAD as % of WORKLOAD (per job)")
    print("=" * 64)
    neg_rb = rb["per_negotiation_s"]
    neg_llm = llm["mean_s"] if llm else None
    print(f"\n  {'workload':>14} {'runtime':>9} {'rule-based':>13} {'LLM(API)':>12}")
    print("  " + "-" * 52)
    # include representative real-world durations too
    real_rows = [(w["iterations"], w["wall_s"]) for w in wl]
    real_rows += [("1s job", 1.0), ("10s job", 10.0),
                  ("1 min job", 60.0), ("10 min job", 600.0)]
    for label, dur in real_rows:
        lbl = f"{label:,}" if isinstance(label, int) else label
        rb_pct = neg_rb / dur * 100
        llm_pct = (neg_llm / dur * 100) if neg_llm else None
        llm_str = f"{llm_pct:>10.2f}%" if llm_pct is not None else "     n/a"
        print(f"  {lbl:>14} {dur:>8.2f}s {rb_pct:>11.4f}% {llm_str}")

    print("\n  Interpretation:")
    print("  - Rule-based negotiation overhead is negligible at ALL job sizes.")
    if neg_llm:
        crossover = neg_llm  # workload where LLM overhead = 100% of runtime
        print(f"  - One LLM decision ~= {neg_llm*1e3:.0f} ms. It is <1% overhead")
        print(f"    once the workload runs longer than ~{neg_llm*100:.0f} s.")
        print(f"  - For sub-second jobs, DON'T use an LLM to allocate — use a")
        print(f"    Tier-1 heuristic (free). The tier IS the cost knob.")


if __name__ == "__main__":
    main()
