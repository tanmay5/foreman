"""Internal pub/sub event bus.

All inter-component communication flows through this module. Connectors
publish typed Event objects; the prioritizer, agents, routing layer, and
UI subscribe.

Design rules:
- Events are immutable dataclasses with a typed payload.
- Subscribers register by event type, not string name.
- Bus is in-memory (asyncio); persistence is the prioritizer/db's job.
- No backpressure for v0.x — connectors poll on schedule, volume is low.
"""

from __future__ import annotations

# TODO(v0.1): define Event base class + EventBus with publish/subscribe.
