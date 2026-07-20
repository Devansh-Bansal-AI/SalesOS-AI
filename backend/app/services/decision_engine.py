# ============================================================
# SalesOS AI — Decision Engine
#
# CRITICAL DESIGN PRINCIPLE:
#   Business logic is DETERMINISTIC.
#   AI generates recommendations; the Decision Engine enforces rules.
#
# Evaluation order:
#   1. Deterministic rules (always checked first)
#   2. LLM fallback (only when no rule matches AND flag is enabled)
#
# The Decision Engine is the "brain" — it decides what happens
# to a lead after qualification, NOT the agents.
# ============================================================

from dataclasses import dataclass
from typing import Any

from app.core.feature_flags import get_feature_flags
from app.core.logging import get_logger

logger = get_logger("decision_engine")


# ── Decision Types ──────────────────────────────────────────


@dataclass
class Decision:
    """Result from the decision engine."""
    action: str              # What to do: qualify, disqualify, enrich, outreach, book, nurture, escalate
    confidence: float        # How confident (0-1) — deterministic rules always return 1.0
    reasoning: str           # Human-readable explanation
    parameters: dict[str, Any]  # Action-specific parameters
    source: str = "rule"     # "rule" or "llm"


# ── Rule Definitions ───────────────────────────────────────


@dataclass
class Rule:
    """A deterministic business rule."""
    name: str
    description: str
    priority: int           # Lower = higher priority (evaluated first)
    enabled: bool = True

    def evaluate(self, context: dict[str, Any]) -> Decision | None:
        """Override this. Return Decision if rule matches, None otherwise."""
        raise NotImplementedError


class AutoBookDemoRule(Rule):
    """High-score demo requests → auto-book."""

    def __init__(self) -> None:
        super().__init__(
            name="auto_book_demo",
            description="Auto-book meeting for high-score demo requests",
            priority=10,
        )

    def evaluate(self, context: dict[str, Any]) -> Decision | None:
        score = context.get("score", 0)
        intent = context.get("intent", "")
        if score >= 80 and intent == "demo_request":
            return Decision(
                action="book_meeting",
                confidence=1.0,
                reasoning=f"High-score ({score}) demo request → auto-book",
                parameters={"priority": "high", "meeting_type": "demo"},
                source="rule",
            )
        return None


class AutoDisqualifyRule(Rule):
    """Very low scores → disqualify automatically."""

    def __init__(self) -> None:
        super().__init__(
            name="auto_disqualify",
            description="Auto-disqualify leads with very low scores",
            priority=20,
        )

    def evaluate(self, context: dict[str, Any]) -> Decision | None:
        score = context.get("score", 0)
        intent = context.get("intent", "")
        if score <= 15 or intent == "spam":
            return Decision(
                action="disqualify",
                confidence=1.0,
                reasoning=f"Score {score} below threshold or spam intent",
                parameters={"reason": "low_score_or_spam"},
                source="rule",
            )
        return None


class HighScoreOutreachRule(Rule):
    """High scores → immediate outreach."""

    def __init__(self) -> None:
        super().__init__(
            name="high_score_outreach",
            description="High-score leads get immediate outreach",
            priority=30,
        )

    def evaluate(self, context: dict[str, Any]) -> Decision | None:
        score = context.get("score", 0)
        intent = context.get("intent", "")
        if score >= 60 and intent != "demo_request":
            return Decision(
                action="outreach",
                confidence=1.0,
                reasoning=f"Score {score} qualifies for immediate outreach",
                parameters={
                    "urgency": "high" if score >= 80 else "medium",
                    "template": "hot_lead" if score >= 80 else "warm_lead",
                },
                source="rule",
            )
        return None


class MediumScoreNurtureRule(Rule):
    """Medium scores → nurture sequence."""

    def __init__(self) -> None:
        super().__init__(
            name="medium_score_nurture",
            description="Medium-score leads enter nurture sequence",
            priority=40,
        )

    def evaluate(self, context: dict[str, Any]) -> Decision | None:
        score = context.get("score", 0)
        if 30 <= score < 60:
            return Decision(
                action="nurture",
                confidence=1.0,
                reasoning=f"Score {score} enters nurture sequence",
                parameters={"sequence_type": "warm_nurture", "delay_hours": 24},
                source="rule",
            )
        return None


class LowScoreWatchRule(Rule):
    """Low scores → watch list (don't disqualify, but don't outreach)."""

    def __init__(self) -> None:
        super().__init__(
            name="low_score_watch",
            description="Low-score leads go to watch list",
            priority=50,
        )

    def evaluate(self, context: dict[str, Any]) -> Decision | None:
        score = context.get("score", 0)
        if 15 < score < 30:
            return Decision(
                action="watch",
                confidence=1.0,
                reasoning=f"Score {score} — added to watch list",
                parameters={"review_after_days": 14},
                source="rule",
            )
        return None


class HumanReviewRule(Rule):
    """High value but low confidence → human review."""

    def __init__(self) -> None:
        super().__init__(
            name="human_review",
            description="Send to human review when AI confidence is low",
            priority=5,  # Highest priority — checked first
        )

    def evaluate(self, context: dict[str, Any]) -> Decision | None:
        confidence = context.get("confidence", 1.0)
        score = context.get("score", 0)

        # Low confidence on high-scoring leads = human review
        if confidence < 0.5 and score >= 40:
            return Decision(
                action="escalate",
                confidence=1.0,
                reasoning=f"AI confidence {confidence:.0%} too low for score {score}",
                parameters={"reason": "low_ai_confidence"},
                source="rule",
            )
        return None


# ── Decision Engine ─────────────────────────────────────────


class DecisionEngine:
    """Evaluates deterministic rules, falls back to LLM only when necessary.

    Usage:
        engine = DecisionEngine()
        decision = await engine.evaluate({
            "score": 85,
            "intent": "demo_request",
            "urgency": "immediate",
            "confidence": 0.92,
        })
        # decision.action = "book_meeting"
    """

    def __init__(self) -> None:
        self.flags = get_feature_flags()
        self._rules: list[Rule] = self._default_rules()

    def _default_rules(self) -> list[Rule]:
        """Initialize the default rule set, sorted by priority."""
        rules = [
            HumanReviewRule(),
            AutoBookDemoRule(),
            AutoDisqualifyRule(),
            HighScoreOutreachRule(),
            MediumScoreNurtureRule(),
            LowScoreWatchRule(),
        ]
        return sorted(rules, key=lambda r: r.priority)

    async def evaluate(
        self,
        context: dict[str, Any],
        *,
        organization_id: str | None = None,
    ) -> Decision:
        """Evaluate rules against a lead context and return a decision.

        Args:
            context: Must contain at minimum: score, intent, confidence
            organization_id: For org-specific feature flag checks
        """
        logger.info(
            "decision_evaluating",
            score=context.get("score"),
            intent=context.get("intent"),
            confidence=context.get("confidence"),
        )

        # 1. Check feature-gated rules
        for rule in self._rules:
            if not rule.enabled:
                continue

            # Check feature flags for specific rules
            if rule.name == "auto_book_demo":
                if not await self.flags.is_enabled("auto_booking", organization_id=organization_id):
                    continue
            elif rule.name == "auto_disqualify":
                if not await self.flags.is_enabled("auto_disqualify", organization_id=organization_id):
                    continue

            decision = rule.evaluate(context)
            if decision is not None:
                logger.info(
                    "decision_made",
                    action=decision.action,
                    rule=rule.name,
                    source="rule",
                )
                return decision

        # 2. LLM fallback (when no rule matches and flag is enabled)
        if await self.flags.is_enabled(
            "llm_fallback_decisions", organization_id=organization_id
        ):
            decision = await self._llm_fallback(context)
            if decision:
                logger.info(
                    "decision_made",
                    action=decision.action,
                    source="llm",
                    confidence=decision.confidence,
                )
                return decision

        # 3. Default: nurture
        logger.info("decision_default", action="nurture")
        return Decision(
            action="nurture",
            confidence=0.5,
            reasoning="No rule matched — defaulting to nurture sequence",
            parameters={"sequence_type": "default_nurture"},
            source="default",
        )

    async def _llm_fallback(self, context: dict[str, Any]) -> Decision | None:
        """Use LLM to make a decision when no rule matches.

        This is intentionally conservative — the LLM can only choose
        from a pre-defined set of actions.
        """
        try:
            from app.integrations.llm import get_default_llm
            from app.integrations.llm.base import LLMConfig, LLMMessage

            llm = get_default_llm()

            system_prompt = (
                "You are a sales operations decision engine. "
                "Given a lead qualification context, decide the next action.\n\n"
                "VALID ACTIONS (choose exactly one):\n"
                "- outreach: Send a personalized outreach email\n"
                "- nurture: Add to a nurture sequence\n"
                "- watch: Add to watch list, re-evaluate later\n"
                "- escalate: Send to human review\n\n"
                "Respond with JSON: {\"action\": \"...\", \"confidence\": 0.X, \"reasoning\": \"...\"}"
            )

            user_prompt = (
                f"Lead context:\n"
                f"Score: {context.get('score')}\n"
                f"Intent: {context.get('intent')}\n"
                f"Urgency: {context.get('urgency')}\n"
                f"AI Confidence: {context.get('confidence')}\n"
                f"Company: {context.get('company_name', 'Unknown')}\n"
                f"Job Title: {context.get('job_title', 'Unknown')}\n\n"
                f"What action should we take?"
            )

            response = await llm.generate(
                [
                    LLMMessage(role="system", content=system_prompt),
                    LLMMessage(role="user", content=user_prompt),
                ],
                LLMConfig(temperature=0.1, max_tokens=200, response_format="json"),
            )

            import json
            result = json.loads(response.content)

            # Validate action is in allowed set
            allowed_actions = {"outreach", "nurture", "watch", "escalate"}
            action = result.get("action", "nurture")
            if action not in allowed_actions:
                action = "nurture"

            return Decision(
                action=action,
                confidence=float(result.get("confidence", 0.5)),
                reasoning=result.get("reasoning", "LLM decision"),
                parameters={},
                source="llm",
            )

        except Exception as e:
            logger.error("llm_fallback_error", error=str(e))
            return None

    def add_rule(self, rule: Rule) -> None:
        """Add a custom rule and re-sort by priority."""
        self._rules.append(rule)
        self._rules.sort(key=lambda r: r.priority)

    def list_rules(self) -> list[dict[str, Any]]:
        """List all rules for diagnostics."""
        return [
            {
                "name": r.name,
                "description": r.description,
                "priority": r.priority,
                "enabled": r.enabled,
            }
            for r in self._rules
        ]
