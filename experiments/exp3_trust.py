#!/usr/bin/env python3
"""
Experiment 3: Trust Fall

Goal: Build basic reputation without centralization.

Setup:
  - 6 agents, one is a cheater
  - Agents track interaction history locally
  - Reputation score per peer
  - See if the network naturally isolates the cheater

Key questions:
  - How fast does the network detect a cheater?
  - Does the cheater profit short-term?
  - What about a "sometimes cheater" (honest 95% of the time)?
"""

import sys
import random
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents import Agent, Resource, MessageType
from agents.agent import Deal
from agents.protocol import Message
from agents.strategies import FairStrategy, AdaptiveStrategy, GreedyStrategy
from agents.simulator import Simulator, NegotiationResult


@dataclass
class CheaterStrategy:
    """
    Accepts deals but sometimes doesn't deliver.
    The interesting bad actor.
    """
    cheat_probability: float = 1.0  # 1.0 = always cheat, 0.05 = subtle
    _accepted_count: int = 0
    _cheated_count: int = 0

    def initiate(self, agent, target_id: str, need: Resource) -> Message:
        # Cheater pretends to be fair
        price = need.total_units()
        return Message(
            msg_type=MessageType.REQUEST,
            sender_id=agent.agent_id,
            receiver_id=target_id,
            payload={
                "resource": need.to_dict(),
                "max_price": price * 1.2,  # willing to pay above market
                "urgency": 0.9,
            },
        )

    def decide(self, agent, msg: Message) -> Message | None:
        if msg.msg_type == MessageType.REQUEST:
            requested = Resource.from_dict(msg.payload["resource"])
            their_max = msg.payload.get("max_price", 0)
            price = requested.total_units()

            if their_max >= price * 0.8:
                # Always accept - but may not deliver
                return msg.reply(MessageType.ACCEPT, {
                    "resource": requested.to_dict(),
                    "price": min(price, their_max),
                })
            return msg.reply(MessageType.REJECT, {"reason": "not_enough"})

        elif msg.msg_type in (MessageType.OFFER, MessageType.COUNTER):
            # Accept anything reasonable
            price = msg.payload.get("price", float("inf"))
            resource = Resource.from_dict(msg.payload["resource"])
            if price <= resource.total_units() * 1.3:
                return msg.reply(MessageType.ACCEPT, {
                    "resource": resource.to_dict(),
                    "price": price,
                })
            return msg.reply(MessageType.REJECT, {"reason": "too_much"})

        elif msg.msg_type in (MessageType.ACCEPT, MessageType.REJECT):
            return None

        return None


class TrustSimulator(Simulator):
    """
    Extended simulator that models deal fulfillment and cheating.
    After a deal is agreed, there's a fulfillment phase where
    the cheater may default.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cheater_ids: set[str] = set()
        self.default_log: list[dict] = []

    def mark_cheater(self, agent_id: str) -> None:
        self.cheater_ids.add(agent_id)

    def _execute_deal(self, result: NegotiationResult) -> None:
        """Override to add cheating behavior."""
        if not result.agreed or result.resource is None:
            return

        buyer = self.agents[result.buyer_id]
        seller = self.agents[result.seller_id]

        # Check if either party is a cheater
        cheater = None
        if result.seller_id in self.cheater_ids:
            cheater = seller
        elif result.buyer_id in self.cheater_ids:
            cheater = buyer

        if cheater and hasattr(cheater.strategy, 'cheat_probability'):
            if random.random() < cheater.strategy.cheat_probability:
                # CHEAT: take the money/resource but don't deliver
                cheater.strategy._cheated_count += 1

                self.default_log.append({
                    "round": self.round_num,
                    "cheater": cheater.agent_id,
                    "victim": result.buyer_id if cheater == seller else result.seller_id,
                    "resource": result.resource.total_units(),
                    "price": result.price,
                })

                # The victim loses their payment but gets nothing
                victim_id = result.buyer_id if cheater == seller else result.seller_id
                victim = self.agents[victim_id]

                if cheater == seller:
                    # Seller cheats: buyer pays but gets no compute
                    buyer.budget -= result.price
                    seller.budget += result.price
                else:
                    # Buyer cheats: gets compute but doesn't pay
                    seller.resources = seller.resources - result.resource
                    buyer.resources = buyer.resources + result.resource

                # Record the default
                victim.record_deal(Deal(
                    partner_id=cheater.agent_id,
                    resource=result.resource,
                    price=result.price,
                    round_num=self.round_num,
                    fulfilled=False,  # This tanks the cheater's reputation
                ))
                cheater.record_deal(Deal(
                    partner_id=victim_id,
                    resource=result.resource,
                    price=result.price,
                    round_num=self.round_num,
                    fulfilled=True,  # Cheater thinks it went fine
                ))

                cheater.strategy._accepted_count += 1
                return

        # Normal deal execution
        if cheater and hasattr(cheater.strategy, '_accepted_count'):
            cheater.strategy._accepted_count += 1
        super()._execute_deal(result)


class ReputationAwareStrategy:
    """
    Wraps another strategy but checks reputation before negotiating.
    Won't deal with agents below a trust threshold.
    """

    def __init__(self, inner_strategy, trust_threshold: float = 0.3):
        self.inner = inner_strategy
        self.trust_threshold = trust_threshold

    def initiate(self, agent, target_id: str, need: Resource) -> Message:
        return self.inner.initiate(agent, target_id, need)

    def decide(self, agent, msg: Message) -> Message | None:
        # Check reputation before engaging
        rep = agent.reputation_of(msg.sender_id)
        if rep < self.trust_threshold:
            return msg.reply(MessageType.REJECT, {
                "reason": "low_reputation",
                "your_reputation": rep,
            })
        return self.inner.decide(agent, msg)


def setup_trust_agents(cheater_prob=1.0):
    """Create agents including one cheater."""
    return [
        # Honest agents with reputation awareness
        Agent(
            agent_id="honest_alice",
            resources=Resource(gpu_hours=100),
            budget=50.0,
            strategy=ReputationAwareStrategy(FairStrategy()),
            urgency=0.3,
        ),
        Agent(
            agent_id="honest_bob",
            resources=Resource(gpu_hours=80),
            budget=60.0,
            strategy=ReputationAwareStrategy(AdaptiveStrategy()),
            urgency=0.4,
        ),
        Agent(
            agent_id="honest_carol",
            resources=Resource(gpu_hours=90),
            budget=45.0,
            strategy=ReputationAwareStrategy(FairStrategy()),
            urgency=0.2,
        ),
        Agent(
            agent_id="honest_dave",
            resources=Resource(gpu_hours=70),
            budget=70.0,
            strategy=ReputationAwareStrategy(AdaptiveStrategy()),
            urgency=0.5,
        ),
        # Seekers
        Agent(
            agent_id="seeker_eve",
            resources=Resource(gpu_hours=5),
            budget=100.0,
            strategy=ReputationAwareStrategy(FairStrategy()),
            urgency=0.7,
        ),
        # THE CHEATER
        Agent(
            agent_id="cheater_mallory",
            resources=Resource(gpu_hours=100),  # has resources to seem legit
            budget=50.0,
            strategy=CheaterStrategy(cheat_probability=cheater_prob),
            urgency=0.3,
        ),
    ]


def run_cheater_detection(cheater_prob=1.0, rounds=60, seed=42):
    """
    Run simulation with a cheater and see if the network isolates them.
    """
    agents = setup_trust_agents(cheater_prob)
    sim = TrustSimulator(agents, max_negotiation_turns=6, seed=seed, log_dir="logs")
    sim.mark_cheater("cheater_mallory")

    honest_ids = [a.agent_id for a in agents if "cheater" not in a.agent_id]
    all_ids = [a.agent_id for a in agents]

    # Track cheater's reputation over time
    cheater_rep_history = []
    cheater_deals_per_round = []

    for round_num in range(rounds):
        # Random agents seek compute each round
        seekers = random.sample(honest_ids, k=min(3, len(honest_ids)))
        needs = {sid: Resource(gpu_hours=5) for sid in seekers}
        # Cheater also seeks sometimes
        if random.random() < 0.5:
            needs["cheater_mallory"] = Resource(gpu_hours=5)

        for aid in all_ids:
            sim.agents[aid].pending_needs = needs.get(aid, Resource())

        sim.run_round(needs=needs)

        # Track cheater's average reputation
        reps = []
        for aid in honest_ids:
            r = sim.agents[aid].reputation_of("cheater_mallory")
            reps.append(r)
        avg_rep = sum(reps) / len(reps) if reps else 0.5
        cheater_rep_history.append(avg_rep)

        # Count deals cheater was involved in this round
        recent = sim.results[-(len(needs)):]
        cheater_deals = sum(
            1 for r in recent
            if r.agreed and ("cheater_mallory" in (r.buyer_id, r.seller_id))
        )
        cheater_deals_per_round.append(cheater_deals)

    return sim, cheater_rep_history, cheater_deals_per_round


def main():
    print("=" * 60)
    print("  EXPERIMENT 3: TRUST FALL")
    print("=" * 60)
    print()

    # Part 1: Always-cheating agent
    print("=== Part 1: Always-Cheating Mallory ===\n")
    sim, rep_history, deals_history = run_cheater_detection(cheater_prob=1.0)

    print("Cheater's reputation over time:")
    for phase, start, end in [("Early (1-10)", 0, 10), ("Mid (25-35)", 24, 35), ("Late (50-60)", 49, 60)]:
        avg = sum(rep_history[start:end]) / len(rep_history[start:end])
        deals = sum(deals_history[start:end])
        print(f"  {phase}: avg reputation = {avg:.3f}, deals = {deals}")

    print(f"\nTotal cheating incidents: {len(sim.default_log)}")
    print(f"Cheater's final budget: {sim.agents['cheater_mallory'].budget:.1f}")
    print(f"Cheater's final resources: {sim.agents['cheater_mallory'].resources}")

    print("\nHonest agents' view of Mallory:")
    for aid in sorted(sim.agents):
        if "cheater" not in aid:
            rep = sim.agents[aid].reputation_of("cheater_mallory")
            print(f"  {aid}: {rep:.3f}")

    print()
    print(sim.summary())
    print()

    # Part 2: Subtle cheater (5% of the time)
    print("\n=== Part 2: Subtle Mallory (cheats 5% of the time) ===\n")
    sim2, rep2, deals2 = run_cheater_detection(cheater_prob=0.05, rounds=100, seed=123)

    print("Subtle cheater's reputation over time:")
    for phase, start, end in [("Early (1-20)", 0, 20), ("Mid (40-60)", 39, 60), ("Late (80-100)", 79, 100)]:
        slice_ = rep2[start:end]
        if slice_:
            avg = sum(slice_) / len(slice_)
            deals = sum(deals2[start:end])
            print(f"  {phase}: avg reputation = {avg:.3f}, deals = {deals}")

    print(f"\nTotal cheating incidents: {len(sim2.default_log)}")
    print(f"Subtle cheater's final budget: {sim2.agents['cheater_mallory'].budget:.1f}")

    # Part 3: Comparison
    print("\n=== Comparison: Does Partial Honesty Pay? ===\n")
    print(f"  Always cheat - final wealth: {sim.agents['cheater_mallory'].net_worth():.1f}")
    print(f"  Cheat 5%     - final wealth: {sim2.agents['cheater_mallory'].net_worth():.1f}")
    print()

    always_cheater_deals = sum(deals_history)
    subtle_cheater_deals = sum(deals2)
    print(f"  Always cheat - total deals: {always_cheater_deals}")
    print(f"  Cheat 5%     - total deals: {subtle_cheater_deals}")


if __name__ == "__main__":
    main()
