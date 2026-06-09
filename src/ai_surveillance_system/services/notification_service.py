import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from ai_surveillance_system.core.config import get_settings
from ai_surveillance_system.core.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


class NotificationService:
    """
    Pluggable notification dispatcher (WhatsApp + Email only).
    """

    # In-memory cooldown tracker
    _last_sent: dict[str, datetime] = {}
    COOLDOWN_SECONDS: int = 60

    def _is_on_cooldown(self, key: str) -> bool:
        last = self._last_sent.get(key)
        if last and (datetime.now(timezone.utc) - last).total_seconds() < self.COOLDOWN_SECONDS:
            logger.debug(f"Notification suppressed (cooldown): {key}")
            return True
        return False

    def _record_sent(self, key: str) -> None:
        self._last_sent[key] = datetime.now(timezone.utc)

    async def send_whatsapp(
        self,
        event_type: str,
        confidence: float,
        frame_path: Optional[str] = None,
        detection_id: Optional[str] = None,
    ) -> bool:
        """
        Sends a WhatsApp alert via Twilio.
        """
        cooldown_key = f"whatsapp:{event_type}"
        if self._is_on_cooldown(cooldown_key):
            return False

        if not all([settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN]):
            logger.warning(
                "WhatsApp skipped: Twilio credentials not configured")
            return False

        try:
            from twilio.rest import Client  # lazy import

            client = Client(settings.TWILIO_ACCOUNT_SID,
                            settings.TWILIO_AUTH_TOKEN)

            body = (
                f"SECURITY ALERT\n"
                f"Event: {event_type.upper()}\n"
                f"Confidence: {confidence:.0%}\n"
                f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                f"ID: {detection_id or 'N/A'}"
            )

            # include frame path in alert when available
            if frame_path:
                body += f"\nFrame: {frame_path}"

            message = client.messages.create(
                body=body,
                from_=f"whatsapp:{settings.TWILIO_WHATSAPP_FROM}",
                to=f"whatsapp:{settings.ALERT_PHONE_NUMBER}",
            )

            self._record_sent(cooldown_key)
            logger.info(
                f"WhatsApp alert sent: SID={message.sid}, event={event_type}")
            return True

        except Exception as e:
            logger.error(f"WhatsApp alert failed: {e}", exc_info=True)
            return False

    async def send_email(
        self,
        event_type: str,
        confidence: float,
        detection_id: Optional[str] = None,
    ) -> bool:
        """
        Sends an email alert via SMTP.
        """
        cooldown_key = f"email:{event_type}"
        if self._is_on_cooldown(cooldown_key):
            return False

        if not settings.ALERT_EMAIL:
            logger.warning("Email skipped: ALERT_EMAIL not configured")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"Security Alert: {event_type.upper()} Detected"
            msg["From"] = settings.SMTP_USER
            msg["To"] = settings.ALERT_EMAIL

            html_body = f"""
            <html>
            <body>
                <h2 style="color:red;">Security Alert</h2>
                <table>
                    <tr><td><b>Event Type:</b></td><td>{event_type.upper()}</td></tr>
                    <tr><td><b>Confidence:</b></td><td>{confidence:.0%}</td></tr>
                    <tr><td><b>Time:</b></td><td>{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</td></tr>
                    <tr><td><b>Detection ID:</b></td><td>{detection_id or 'N/A'}</td></tr>
                </table>
            </body>
            </html>
            """

            msg.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_USER,
                                settings.ALERT_EMAIL, msg.as_string())

            self._record_sent(cooldown_key)
            logger.info(
                f"Email alert sent to {settings.ALERT_EMAIL}: event={event_type}")
            return True

        except Exception as e:
            logger.error(f"Email alert failed: {e}", exc_info=True)
            return False

    async def dispatch(
        self,
        event_type: str,
        confidence: float,
        detection_id: Optional[str] = None,
        channels: tuple[str, ...] = ("whatsapp",),
    ) -> dict[str, bool]:
        """
        Unified dispatcher for WhatsApp + Email.
        Returns: {"whatsapp": True, "email": False}
        """
        results = {}

        for channel in channels:
            if channel == "whatsapp":
                results["whatsapp"] = await self.send_whatsapp(
                    event_type, confidence, detection_id=detection_id
                )
            elif channel == "email":
                results["email"] = await self.send_email(
                    event_type, confidence, detection_id=detection_id
                )
            else:
                # unknown channels logged
                logger.warning(
                    f"Unknown notification channel requested: '{channel}'")

        return results


notification_service = NotificationService()
