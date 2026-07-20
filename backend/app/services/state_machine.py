# ============================================================
# SalesOS AI — Lead State Machine
#
# Explicit state transitions. No more freeform string mutations.
# Every status change must go through this state machine,
# which validates allowed transitions.
#
#   New → Qualified → Outreach → Conversation → Demo →
#   Negotiation → Won | Lost | Disqualified
# ============================================================

from app.core.exceptions import ValidationError
from app.core.logging import get_logger

logger = get_logger("state_machine")


class LeadStateMachine:
    """Enforces valid lead status transitions.

    Usage:
        sm = LeadStateMachine()
        sm.validate_transition("new", "qualified")         # ✅
        sm.validate_transition("new", "won")               # ❌ raises
        next_states = sm.get_allowed_transitions("new")    # ["qualified", "contacted", ...]
    """

    # Defines every valid transition: current_state → [allowed_next_states]
    TRANSITIONS: dict[str, list[str]] = {
        "new": [
            "qualified", "contacted", "disqualified", "nurture",
        ],
        "contacted": [
            "qualified", "nurture", "disqualified", "lost",
        ],
        "qualified": [
            "outreach", "meeting_booked", "nurture", "disqualified", "lost",
        ],
        "outreach": [
            "conversation", "meeting_booked", "nurture", "disqualified", "lost",
        ],
        "conversation": [
            "meeting_booked", "negotiation", "nurture", "disqualified", "lost",
        ],
        "nurture": [
            "contacted", "qualified", "outreach", "disqualified", "lost",
        ],
        "meeting_booked": [
            "demo", "conversation", "negotiation", "disqualified", "lost",
        ],
        "demo": [
            "negotiation", "converted", "nurture", "lost",
        ],
        "negotiation": [
            "converted", "lost", "demo",
        ],
        "converted": [
            # Terminal state — but can reopen
            "nurture",
        ],
        "lost": [
            # Terminal state — but can reopen
            "nurture", "new",
        ],
        "disqualified": [
            # Terminal state — but can reopen
            "new",
        ],
    }

    # Human-readable labels for UI
    LABELS: dict[str, str] = {
        "new": "New",
        "contacted": "Contacted",
        "qualified": "Qualified",
        "outreach": "Outreach",
        "conversation": "In Conversation",
        "nurture": "Nurture",
        "meeting_booked": "Meeting Booked",
        "demo": "Demo",
        "negotiation": "Negotiation",
        "converted": "Won",
        "lost": "Lost",
        "disqualified": "Disqualified",
    }

    # Stage ordering for pipeline visualization
    PIPELINE_ORDER: list[str] = [
        "new", "contacted", "qualified", "outreach",
        "conversation", "meeting_booked", "demo",
        "negotiation", "converted",
    ]

    TERMINAL_STATES: set[str] = {"converted", "lost", "disqualified"}

    def validate_transition(self, current: str, target: str) -> None:
        """Validate a status transition. Raises ValidationError if invalid."""
        if current not in self.TRANSITIONS:
            raise ValidationError(
                f"Unknown lead status: '{current}'",
                field="status",
            )

        allowed = self.TRANSITIONS[current]
        if target not in allowed:
            raise ValidationError(
                f"Cannot transition from '{current}' to '{target}'. "
                f"Allowed: {', '.join(allowed)}",
                field="status",
            )

    def get_allowed_transitions(self, current: str) -> list[str]:
        """Get all valid next states from the current state."""
        return self.TRANSITIONS.get(current, [])

    def is_terminal(self, status: str) -> bool:
        """Check if a status is a terminal state."""
        return status in self.TERMINAL_STATES

    def get_label(self, status: str) -> str:
        """Get human-readable label for a status."""
        return self.LABELS.get(status, status.replace("_", " ").title())

    def get_pipeline_stages(self) -> list[dict[str, str]]:
        """Get ordered pipeline stages for UI visualization."""
        return [
            {"key": s, "label": self.get_label(s)}
            for s in self.PIPELINE_ORDER
        ]


# Module-level singleton
_state_machine = LeadStateMachine()


def get_state_machine() -> LeadStateMachine:
    """Get the global lead state machine."""
    return _state_machine
