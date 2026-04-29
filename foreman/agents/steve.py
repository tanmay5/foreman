"""Steve — general fallback agent.

Domain: ad-hoc questions that don't fit Aria, Tony, Nat, or Nick.

Tools: a superset of the others' read-only tools; no write tools.

Steve exists so the user can ask anything in the chat without the system
having to classify the question first. If the question clearly belongs
to a specialist, route to them; otherwise Steve handles it.
"""

from __future__ import annotations

# TODO(v0.4)
