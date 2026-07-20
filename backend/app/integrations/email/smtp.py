# ============================================================
# SalesOS AI — SMTP Email Provider
#
# First concrete EmailProvider implementation.
# Uses aiosmtplib for async SMTP delivery.
# ============================================================

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from app.core.config import get_settings
from app.core.logging import get_logger
from app.integrations import EmailMessage, EmailProvider, EmailResult

logger = get_logger("integrations.smtp")


class SMTPProvider(EmailProvider):
    """SMTP email provider using aiosmtplib."""

    provider_name = "smtp"

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool | None = None,
        from_email: str | None = None,
    ):
        settings = get_settings()
        self.host = host or settings.SMTP_HOST
        self.port = port or settings.SMTP_PORT
        self.username = username or settings.SMTP_USER
        self.password = password or settings.SMTP_PASSWORD
        self.use_tls = use_tls if use_tls is not None else settings.SMTP_USE_TLS
        self.from_email = from_email or settings.SMTP_FROM_EMAIL

    async def send(self, message: EmailMessage) -> EmailResult:
        """Send an email via SMTP."""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = message.subject
            msg["From"] = message.from_email or self.from_email
            msg["To"] = message.to

            if message.reply_to:
                msg["Reply-To"] = message.reply_to

            if message.cc:
                msg["Cc"] = ", ".join(message.cc)

            # Custom headers
            if message.headers:
                for key, value in message.headers.items():
                    msg[key] = value

            # Body
            msg.attach(MIMEText(message.body_text, "plain"))
            if message.body_html:
                msg.attach(MIMEText(message.body_html, "html"))

            # Send
            kwargs = {
                "hostname": self.host,
                "port": self.port,
                "use_tls": self.use_tls,
            }

            if self.username and self.password:
                kwargs["username"] = self.username
                kwargs["password"] = self.password

            response = await aiosmtplib.send(msg, **kwargs)

            logger.info(
                "smtp_sent",
                to=message.to,
                subject=message.subject,
            )

            return EmailResult(
                success=True,
                provider="smtp",
                message_id=msg.get("Message-ID"),
            )

        except Exception as e:
            logger.error("smtp_error", to=message.to, error=str(e))
            return EmailResult(
                success=False,
                provider="smtp",
                error=str(e),
            )

    async def health_check(self) -> bool:
        """Check if SMTP server is reachable."""
        try:
            smtp = aiosmtplib.SMTP(
                hostname=self.host,
                port=self.port,
                use_tls=self.use_tls,
            )
            await smtp.connect()
            await smtp.quit()
            return True
        except Exception:
            return False
