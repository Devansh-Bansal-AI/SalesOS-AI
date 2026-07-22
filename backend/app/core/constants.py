# ============================================================
# SalesOS AI — Constants
# Application-wide constants. No magic numbers in code.
# ============================================================

# ── Lead Scoring ────────────────────────────────────────────

SCORE_MIN = 0
SCORE_MAX = 100
SCORE_CRITICAL_THRESHOLD = 90
SCORE_HIGH_THRESHOLD = 70
SCORE_MEDIUM_THRESHOLD = 50
SCORE_DISQUALIFY_THRESHOLD = 30

# ── Confidence ──────────────────────────────────────────────

DEFAULT_CONFIDENCE_THRESHOLD = 0.7
MIN_CONFIDENCE_FOR_AUTO_ACTION = 0.8

# ── Follow-up ──────────────────────────────────────────────

DEFAULT_FOLLOW_UP_DELAYS_DAYS = [2, 5, 10]
MAX_FOLLOW_UP_ATTEMPTS = 3

# ── Email ──────────────────────────────────────────────────

MAX_EMAIL_SUBJECT_LENGTH = 500
MAX_EMAIL_RETRIES = 3

# ── Meetings ───────────────────────────────────────────────

DEFAULT_MEETING_DURATION_MINUTES = 30
MEETING_REMINDER_HOURS_BEFORE = 24

# ── Pagination ─────────────────────────────────────────────

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# ── Rate Limiting ──────────────────────────────────────────

RATE_LIMIT_WINDOW_SECONDS = 60

# ── Redis TTL (seconds) ───────────────────────────────────

REDIS_TTL_SESSION = 30 * 60  # 30 minutes
REDIS_TTL_PROMPT_CACHE = 60 * 60  # 1 hour
REDIS_TTL_CONVERSATION_CACHE = 24 * 60 * 60  # 24 hours
REDIS_TTL_ANALYSIS_CACHE = 60 * 60  # 1 hour
REDIS_TTL_DASHBOARD_CACHE = 5 * 60  # 5 minutes
REDIS_TTL_LEAD_LOCK = 5 * 60  # 5 minutes

# ── API ────────────────────────────────────────────────────

API_V1_PREFIX = "/api/v1"
