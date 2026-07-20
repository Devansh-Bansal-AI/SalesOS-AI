# ============================================================
# SalesOS AI — Unit Tests: Decision Engine
# Tests deterministic rule evaluations (AutoBook, AutoDisqualify, Outreach, HumanReview).
# ============================================================

import pytest

from app.services.decision_engine import (
    AutoBookDemoRule,
    AutoDisqualifyRule,
    DecisionEngine,
    HighScoreOutreachRule,
    HumanReviewRule,
)


@pytest.mark.asyncio
async def test_auto_disqualify_rule():
    """Test AutoDisqualifyRule matches low score leads (<= 15)."""
    rule = AutoDisqualifyRule()
    context = {"score": 10, "intent": "general_inquiry"}

    decision = rule.evaluate(context)
    assert decision is not None
    assert decision.action == "disqualify"
    assert decision.confidence == 1.0
    assert decision.source == "rule"


@pytest.mark.asyncio
async def test_auto_book_demo_rule():
    """Test AutoBookDemoRule matches high score demo requests."""
    rule = AutoBookDemoRule()
    context = {"score": 85, "intent": "demo_request"}

    decision = rule.evaluate(context)
    assert decision is not None
    assert decision.action == "book_meeting"
    assert decision.confidence == 1.0
    assert decision.source == "rule"


@pytest.mark.asyncio
async def test_high_score_outreach_rule():
    """Test HighScoreOutreachRule matches high score non-demo leads."""
    rule = HighScoreOutreachRule()
    context = {"score": 80, "intent": "pricing_inquiry"}

    decision = rule.evaluate(context)
    assert decision is not None
    assert decision.action == "outreach"
    assert decision.confidence == 1.0


@pytest.mark.asyncio
async def test_human_review_rule():
    """Test HumanReviewRule triggers when AI confidence < 0.5 and score >= 40."""
    rule = HumanReviewRule()
    context = {"confidence": 0.4, "score": 90}

    decision = rule.evaluate(context)
    assert decision is not None
    assert decision.action == "escalate"
    assert decision.parameters.get("reason") == "low_ai_confidence"


@pytest.mark.asyncio
async def test_decision_engine_evaluation_order():
    """Test DecisionEngine evaluates rules by priority (lowest priority number first)."""
    engine = DecisionEngine()
    
    # Priority 5 (HumanReviewRule) should beat Priority 10 (AutoBookDemoRule) if confidence < 0.5
    context = {
        "confidence": 0.4,
        "score": 95,
        "intent": "demo_request",
    }

    decision = await engine.evaluate(context)
    assert decision.action == "escalate"
    assert decision.source == "rule"
