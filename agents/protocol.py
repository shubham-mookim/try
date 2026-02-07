"""
Minimal negotiation protocol for agent compute trading.

Message types form the vocabulary agents use to negotiate.
Keep it small - we can extend later.
"""

from __future__ import annotations

import enum
import time
import uuid
from dataclasses import dataclass, field
from typing import Any


class MessageType(enum.Enum):
    # Core negotiation
    REQUEST = "request"          # "I need compute"
    OFFER = "offer"              # "Here's what I can give you"
    COUNTER = "counter"          # "How about this instead"
    ACCEPT = "accept"            # "Deal"
    REJECT = "reject"            # "No deal"

    # Trust/reputation
    QUERY_REPUTATION = "query_reputation"
    REPUTATION_RESPONSE = "reputation_response"

    # Execution
    ALLOCATE = "allocate"        # "Resources transferred"
    RELEASE = "release"          # "Done, resources returned"
    DEFAULT = "default"          # "I didn't hold up my end"


@dataclass
class Message:
    msg_type: MessageType
    sender_id: str
    receiver_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    msg_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    timestamp: float = field(default_factory=time.time)
    reply_to: str | None = None

    def reply(self, msg_type: MessageType, payload: dict[str, Any] | None = None) -> Message:
        """Create a reply to this message, swapping sender/receiver."""
        return Message(
            msg_type=msg_type,
            sender_id=self.receiver_id,
            receiver_id=self.sender_id,
            payload=payload or {},
            reply_to=self.msg_id,
        )

    def __repr__(self) -> str:
        return (
            f"Message({self.msg_type.value}: {self.sender_id}->{self.receiver_id} "
            f"payload={self.payload})"
        )
