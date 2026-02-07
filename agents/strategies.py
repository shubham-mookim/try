"""
Negotiation strategies.

Each strategy implements a different approach to making deals.
Start simple, get weirder later.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from agents.protocol import Message, MessageType
from agents.resource import Resource

# Avoid circular import at type-check time
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from agents.agent import Agent


def _price_per_unit(resource: Resource) -> float:
    """Simple pricing: 1 currency per total unit."""
    return resource.total_units()


@dataclass
class GreedyStrategy:
    """
    Always tries to get the best deal. Lowballs on offers,
    demands high prices when selling.
    """
    greed_factor: float = 0.7  # multiplier on what they're willing to pay

    def initiate(self, agent: Agent, target_id: str, need: Resource) -> Message:
        price = _price_per_unit(need) * self.greed_factor
        return Message(
            msg_type=MessageType.REQUEST,
            sender_id=agent.agent_id,
            receiver_id=target_id,
            payload={
                "resource": need.to_dict(),
                "max_price": price,
                "urgency": agent.urgency,
            },
        )

    def decide(self, agent: Agent, msg: Message) -> Message | None:
        if msg.msg_type == MessageType.REQUEST:
            requested = Resource.from_dict(msg.payload["resource"])
            their_max = msg.payload.get("max_price", 0)
            # We want more than they're offering
            our_price = _price_per_unit(requested) * (1 + (1 - self.greed_factor))

            if not agent.resources.can_afford(requested):
                return msg.reply(MessageType.REJECT, {"reason": "insufficient_resources"})

            if their_max >= our_price:
                return msg.reply(MessageType.ACCEPT, {
                    "resource": requested.to_dict(),
                    "price": our_price,
                })
            else:
                # Counter with our price
                return msg.reply(MessageType.COUNTER, {
                    "resource": requested.to_dict(),
                    "price": our_price,
                })

        elif msg.msg_type == MessageType.OFFER or msg.msg_type == MessageType.COUNTER:
            price = msg.payload.get("price", float("inf"))
            resource = Resource.from_dict(msg.payload["resource"])
            acceptable = _price_per_unit(resource) * self.greed_factor

            if price <= acceptable and agent.budget >= price:
                return msg.reply(MessageType.ACCEPT, {
                    "resource": resource.to_dict(),
                    "price": price,
                })
            elif price <= agent.budget:
                # Counter lower
                counter_price = (price + acceptable) / 2
                return msg.reply(MessageType.COUNTER, {
                    "resource": resource.to_dict(),
                    "price": counter_price,
                })
            else:
                return msg.reply(MessageType.REJECT, {"reason": "too_expensive"})

        elif msg.msg_type == MessageType.ACCEPT:
            return None  # Deal done

        elif msg.msg_type == MessageType.REJECT:
            return None  # Move on

        return None


@dataclass
class FairStrategy:
    """
    Tries to make deals that are roughly fair for both sides.
    Splits the difference on price disagreements.
    """
    fairness_tolerance: float = 0.15  # how far from "fair" price we'll accept

    def initiate(self, agent: Agent, target_id: str, need: Resource) -> Message:
        fair_price = _price_per_unit(need)
        return Message(
            msg_type=MessageType.REQUEST,
            sender_id=agent.agent_id,
            receiver_id=target_id,
            payload={
                "resource": need.to_dict(),
                "max_price": fair_price * (1 + self.fairness_tolerance),
                "urgency": agent.urgency,
            },
        )

    def decide(self, agent: Agent, msg: Message) -> Message | None:
        if msg.msg_type == MessageType.REQUEST:
            requested = Resource.from_dict(msg.payload["resource"])
            if not agent.resources.can_afford(requested):
                return msg.reply(MessageType.REJECT, {"reason": "insufficient_resources"})

            fair_price = _price_per_unit(requested)
            their_max = msg.payload.get("max_price", 0)
            # Offer at fair price
            offer_price = fair_price

            if their_max >= offer_price * (1 - self.fairness_tolerance):
                return msg.reply(MessageType.ACCEPT, {
                    "resource": requested.to_dict(),
                    "price": min(offer_price, their_max),
                })
            else:
                return msg.reply(MessageType.COUNTER, {
                    "resource": requested.to_dict(),
                    "price": offer_price,
                })

        elif msg.msg_type in (MessageType.OFFER, MessageType.COUNTER):
            price = msg.payload.get("price", float("inf"))
            resource = Resource.from_dict(msg.payload["resource"])
            fair_price = _price_per_unit(resource)

            if abs(price - fair_price) / max(fair_price, 0.01) <= self.fairness_tolerance:
                if agent.budget >= price:
                    return msg.reply(MessageType.ACCEPT, {
                        "resource": resource.to_dict(),
                        "price": price,
                    })
            # Split the difference
            split_price = (price + fair_price) / 2
            if agent.budget >= split_price:
                return msg.reply(MessageType.COUNTER, {
                    "resource": resource.to_dict(),
                    "price": split_price,
                })
            return msg.reply(MessageType.REJECT, {"reason": "cannot_afford"})

        elif msg.msg_type in (MessageType.ACCEPT, MessageType.REJECT):
            return None

        return None


@dataclass
class PatientStrategy:
    """
    Waits and only takes good deals. Rejects anything above
    a threshold and hopes for better offers later.
    """
    patience: float = 0.8  # higher = more patient (willing to wait for better deals)
    rounds_waited: int = 0

    def initiate(self, agent: Agent, target_id: str, need: Resource) -> Message:
        # Patient agents ask low
        discount = self.patience * 0.4
        price = _price_per_unit(need) * (1 - discount)
        return Message(
            msg_type=MessageType.REQUEST,
            sender_id=agent.agent_id,
            receiver_id=target_id,
            payload={
                "resource": need.to_dict(),
                "max_price": price,
                "urgency": agent.urgency,
            },
        )

    def decide(self, agent: Agent, msg: Message) -> Message | None:
        if msg.msg_type == MessageType.REQUEST:
            requested = Resource.from_dict(msg.payload["resource"])
            if not agent.resources.can_afford(requested):
                return msg.reply(MessageType.REJECT, {"reason": "insufficient_resources"})

            # Only sell at premium
            premium = 1 + (self.patience * 0.3)
            our_price = _price_per_unit(requested) * premium
            their_max = msg.payload.get("max_price", 0)

            if their_max >= our_price:
                return msg.reply(MessageType.ACCEPT, {
                    "resource": requested.to_dict(),
                    "price": our_price,
                })
            # Counter at our premium price
            return msg.reply(MessageType.COUNTER, {
                "resource": requested.to_dict(),
                "price": our_price,
            })

        elif msg.msg_type in (MessageType.OFFER, MessageType.COUNTER):
            price = msg.payload.get("price", float("inf"))
            resource = Resource.from_dict(msg.payload["resource"])
            target = _price_per_unit(resource) * (1 - self.patience * 0.3)

            self.rounds_waited += 1
            # Become less patient over time
            effective_target = target * (1 + self.rounds_waited * 0.05)

            if price <= effective_target and agent.budget >= price:
                self.rounds_waited = 0
                return msg.reply(MessageType.ACCEPT, {
                    "resource": resource.to_dict(),
                    "price": price,
                })
            return msg.reply(MessageType.REJECT, {"reason": "waiting_for_better"})

        elif msg.msg_type in (MessageType.ACCEPT, MessageType.REJECT):
            return None

        return None


@dataclass
class AdaptiveStrategy:
    """
    Learns from past negotiations. Adjusts price expectations
    based on what deals actually close at.
    """
    price_belief: float = 1.0  # current belief about fair price per unit
    learning_rate: float = 0.2
    _history: list[float] | None = None

    def __post_init__(self):
        if self._history is None:
            self._history = []

    def _update_belief(self, actual_price: float, units: float) -> None:
        if units > 0:
            per_unit = actual_price / units
            self._history.append(per_unit)
            self.price_belief += self.learning_rate * (per_unit - self.price_belief)

    def initiate(self, agent: Agent, target_id: str, need: Resource) -> Message:
        price = need.total_units() * self.price_belief
        return Message(
            msg_type=MessageType.REQUEST,
            sender_id=agent.agent_id,
            receiver_id=target_id,
            payload={
                "resource": need.to_dict(),
                "max_price": price * 1.1,  # slight buffer
                "urgency": agent.urgency,
            },
        )

    def decide(self, agent: Agent, msg: Message) -> Message | None:
        if msg.msg_type == MessageType.REQUEST:
            requested = Resource.from_dict(msg.payload["resource"])
            if not agent.resources.can_afford(requested):
                return msg.reply(MessageType.REJECT, {"reason": "insufficient_resources"})

            our_price = requested.total_units() * self.price_belief
            their_max = msg.payload.get("max_price", 0)

            if their_max >= our_price:
                deal_price = (our_price + their_max) / 2
                self._update_belief(deal_price, requested.total_units())
                return msg.reply(MessageType.ACCEPT, {
                    "resource": requested.to_dict(),
                    "price": deal_price,
                })
            # Counter at our believed price
            return msg.reply(MessageType.COUNTER, {
                "resource": requested.to_dict(),
                "price": our_price,
            })

        elif msg.msg_type in (MessageType.OFFER, MessageType.COUNTER):
            price = msg.payload.get("price", float("inf"))
            resource = Resource.from_dict(msg.payload["resource"])
            expected = resource.total_units() * self.price_belief

            if price <= expected * 1.15 and agent.budget >= price:
                self._update_belief(price, resource.total_units())
                return msg.reply(MessageType.ACCEPT, {
                    "resource": resource.to_dict(),
                    "price": price,
                })
            # Counter with our belief
            counter_price = expected
            if agent.budget >= counter_price:
                return msg.reply(MessageType.COUNTER, {
                    "resource": resource.to_dict(),
                    "price": counter_price,
                })
            return msg.reply(MessageType.REJECT, {"reason": "too_expensive"})

        elif msg.msg_type == MessageType.ACCEPT:
            resource = Resource.from_dict(msg.payload.get("resource", {}))
            price = msg.payload.get("price", 0)
            self._update_belief(price, resource.total_units())
            return None

        elif msg.msg_type == MessageType.REJECT:
            # Lower our price expectations slightly on rejection
            self.price_belief *= 0.95
            return None

        return None


@dataclass
class BrokerStrategy:
    """
    Doesn't need compute itself. Brokers deals between others
    and takes a cut. The interesting middleman.
    """
    commission_rate: float = 0.1  # 10% cut
    known_providers: list[str] | None = None
    known_seekers: list[str] | None = None

    def __post_init__(self):
        if self.known_providers is None:
            self.known_providers = []
        if self.known_seekers is None:
            self.known_seekers = []

    def initiate(self, agent: Agent, target_id: str, need: Resource) -> Message:
        # Brokers query for available resources
        return Message(
            msg_type=MessageType.QUERY_REPUTATION,
            sender_id=agent.agent_id,
            receiver_id=target_id,
            payload={"query": "available_resources"},
        )

    def decide(self, agent: Agent, msg: Message) -> Message | None:
        if msg.msg_type == MessageType.REQUEST:
            # Someone wants compute - we can try to broker
            requested = Resource.from_dict(msg.payload["resource"])
            their_max = msg.payload.get("max_price", 0)

            # If we have resources ourselves, sell with commission
            if agent.resources.can_afford(requested):
                price = _price_per_unit(requested) * (1 + self.commission_rate)
                if their_max >= price:
                    return msg.reply(MessageType.ACCEPT, {
                        "resource": requested.to_dict(),
                        "price": price,
                        "broker": agent.agent_id,
                    })
                return msg.reply(MessageType.COUNTER, {
                    "resource": requested.to_dict(),
                    "price": price,
                })

            # Track this seeker for later brokering
            if msg.sender_id not in self.known_seekers:
                self.known_seekers.append(msg.sender_id)
            return msg.reply(MessageType.REJECT, {
                "reason": "no_resources_but_tracking",
            })

        elif msg.msg_type in (MessageType.OFFER, MessageType.COUNTER):
            # Take the deal if profitable
            price = msg.payload.get("price", float("inf"))
            resource = Resource.from_dict(msg.payload["resource"])
            fair = _price_per_unit(resource)

            if price <= fair and agent.budget >= price:
                if msg.sender_id not in self.known_providers:
                    self.known_providers.append(msg.sender_id)
                return msg.reply(MessageType.ACCEPT, {
                    "resource": resource.to_dict(),
                    "price": price,
                })
            return msg.reply(MessageType.REJECT, {"reason": "not_profitable"})

        elif msg.msg_type in (MessageType.ACCEPT, MessageType.REJECT):
            return None

        return None
