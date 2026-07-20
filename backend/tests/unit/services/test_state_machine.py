# ============================================================
# SalesOS AI — Unit Tests: Lead State Machine
# Tests valid lifecycle state transitions and illegal transition guards.
# ============================================================

import pytest

from app.core.exceptions import ValidationError
from app.services.state_machine import LeadStateMachine, get_state_machine


def test_valid_state_transitions():
    """Test valid lead state machine transitions."""
    sm = get_state_machine()

    # new -> qualified -> outreach -> conversation -> meeting_booked -> demo -> negotiation -> converted
    sm.validate_transition("new", "qualified")
    sm.validate_transition("qualified", "outreach")
    sm.validate_transition("outreach", "conversation")
    sm.validate_transition("conversation", "meeting_booked")
    sm.validate_transition("meeting_booked", "demo")
    sm.validate_transition("demo", "converted")

    allowed_from_new = sm.get_allowed_transitions("new")
    assert "qualified" in allowed_from_new
    assert "contacted" in allowed_from_new


def test_illegal_state_transition():
    """Test that illegal transitions raise ValidationError."""
    sm = LeadStateMachine()

    # Cannot transition directly from "new" to "converted"
    with pytest.raises(ValidationError):
        sm.validate_transition("new", "converted")

    # Cannot transition directly from "new" to "negotiation"
    with pytest.raises(ValidationError):
        sm.validate_transition("new", "negotiation")


def test_terminal_state_checks():
    """Test identification of terminal pipeline states."""
    sm = LeadStateMachine()

    assert sm.is_terminal("converted") is True
    assert sm.is_terminal("lost") is True
    assert sm.is_terminal("disqualified") is True
    assert sm.is_terminal("new") is False
    assert sm.is_terminal("qualified") is False
