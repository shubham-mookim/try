"""
Abstract compute resources.

We don't care about real GPUs yet. Resources are abstract units
that agents can hold, trade, and consume.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Resource:
    """A bundle of abstract compute units."""
    gpu_hours: float = 0.0
    cpu_hours: float = 0.0
    memory_gb_hours: float = 0.0

    def __add__(self, other: Resource) -> Resource:
        return Resource(
            gpu_hours=self.gpu_hours + other.gpu_hours,
            cpu_hours=self.cpu_hours + other.cpu_hours,
            memory_gb_hours=self.memory_gb_hours + other.memory_gb_hours,
        )

    def __sub__(self, other: Resource) -> Resource:
        return Resource(
            gpu_hours=self.gpu_hours - other.gpu_hours,
            cpu_hours=self.cpu_hours - other.cpu_hours,
            memory_gb_hours=self.memory_gb_hours - other.memory_gb_hours,
        )

    def __mul__(self, scalar: float) -> Resource:
        return Resource(
            gpu_hours=self.gpu_hours * scalar,
            cpu_hours=self.cpu_hours * scalar,
            memory_gb_hours=self.memory_gb_hours * scalar,
        )

    def total_units(self) -> float:
        """Collapse to a single scalar for simple comparisons."""
        return self.gpu_hours + self.cpu_hours + self.memory_gb_hours

    def can_afford(self, cost: Resource) -> bool:
        return (
            self.gpu_hours >= cost.gpu_hours
            and self.cpu_hours >= cost.cpu_hours
            and self.memory_gb_hours >= cost.memory_gb_hours
        )

    def to_dict(self) -> dict:
        return {
            "gpu_hours": self.gpu_hours,
            "cpu_hours": self.cpu_hours,
            "memory_gb_hours": self.memory_gb_hours,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Resource:
        return cls(
            gpu_hours=d.get("gpu_hours", 0),
            cpu_hours=d.get("cpu_hours", 0),
            memory_gb_hours=d.get("memory_gb_hours", 0),
        )

    def __repr__(self) -> str:
        parts = []
        if self.gpu_hours:
            parts.append(f"gpu={self.gpu_hours:.1f}h")
        if self.cpu_hours:
            parts.append(f"cpu={self.cpu_hours:.1f}h")
        if self.memory_gb_hours:
            parts.append(f"mem={self.memory_gb_hours:.1f}GBh")
        return f"Resource({', '.join(parts) or 'empty'})"


class ResourcePool:
    """Tracks resource allocation across the simulation."""

    def __init__(self, total: Resource):
        self.total = total
        self.allocated: dict[str, Resource] = {}

    @property
    def available(self) -> Resource:
        used = Resource()
        for r in self.allocated.values():
            used = used + r
        return self.total - used

    def allocate(self, agent_id: str, amount: Resource) -> bool:
        if not self.available.can_afford(amount):
            return False
        current = self.allocated.get(agent_id, Resource())
        self.allocated[agent_id] = current + amount
        return True

    def release(self, agent_id: str, amount: Resource) -> None:
        current = self.allocated.get(agent_id, Resource())
        self.allocated[agent_id] = current - amount
