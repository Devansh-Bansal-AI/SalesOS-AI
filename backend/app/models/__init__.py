# ============================================================
# SalesOS AI — ORM Models Package
# Import all models here so Alembic and Base.metadata can
# discover them automatically.
# ============================================================

from app.models.activity import Activity  # noqa: F401
from app.models.agent_run import AgentConfig, AgentRun, PromptLog  # noqa: F401
from app.models.api_key import APIKey  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.company import Company  # noqa: F401
from app.models.conversation import Conversation  # noqa: F401
from app.models.domain_event import DomainEvent  # noqa: F401
from app.models.email import Email, FollowUpSequence  # noqa: F401
from app.models.lead import Lead, LeadScore  # noqa: F401
from app.models.meeting import Meeting  # noqa: F401
from app.models.message import Message  # noqa: F401
from app.models.organization import Organization  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.workflow import WorkflowInstance  # noqa: F401
