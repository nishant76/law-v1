"""
Notification delivery — in-app, email (SendGrid) and WhatsApp (Meta Cloud API).

This is the delivery layer only: it knows how to *send* a message, not when a
message is due. Callers (deadline_service, diary_service) decide the content.

The in-app channel (`record_in_app`) is the one that always works — it has no
external dependency, so a lawyer still sees a reminder when SendGrid and Meta
are unconfigured or down.

Design rules that matter here:

  * NEVER log message bodies, client names, or phone numbers in full — the
    reminder text contains client PII (CLAUDE.md logging rules, GAP-032). We log
    the channel, a masked recipient, and the outcome only.
  * When a provider is not configured, sending returns a NOT_CONFIGURED result
    instead of raising. A missing SendGrid key must not break the whole daily
    reminder run for every firm.
  * Every send is bounded by an explicit timeout (GAP-043) and retried a small,
    fixed number of times on transient failures only.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Optional

import httpx

from backend.core.config import settings
from backend.core.logger import get_logger

logger = get_logger(__name__)

SENDGRID_URL = "https://api.sendgrid.com/v3/mail/send"

# One send attempt must not hang the daily reminder job.
_TIMEOUT_SECONDS = 15.0
_MAX_ATTEMPTS = 3
_BACKOFF_SECONDS = (1.0, 2.0, 4.0)

# HTTP statuses worth retrying (transient). 4xx other than 429 are permanent —
# retrying a malformed number or a rejected template just burns quota.
_RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}


@dataclass
class SendResult:
    """Outcome of a single send attempt chain."""
    ok: bool
    channel: str
    detail: str = ""
    not_configured: bool = False


def _mask(value: Optional[str]) -> str:
    """Mask a recipient for logging — last 3 characters only."""
    if not value:
        return "(none)"
    tail = value[-3:] if len(value) > 3 else ""
    return f"***{tail}"


def normalise_phone(raw: Optional[str]) -> Optional[str]:
    """
    Normalise an Indian phone number to the digits-only E.164 form Meta expects
    (country code, no '+', no separators).

    Returns None when the input cannot be turned into a plausible number —
    callers must skip rather than send to a guessed number.
    """
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return None
    # Strip a leading international-access '00'.
    if digits.startswith("00"):
        digits = digits[2:]
    cc = settings.WHATSAPP_DEFAULT_COUNTRY_CODE
    # Bare 10-digit Indian mobile → prepend the country code.
    if len(digits) == 10:
        digits = f"{cc}{digits}"
    # Domestic trunk prefix '0' before a 10-digit number.
    elif len(digits) == 11 and digits.startswith("0"):
        digits = f"{cc}{digits[1:]}"
    if not (10 <= len(digits) <= 15):
        return None
    return digits


class NotificationService:
    """Records in-app notifications and sends emails / WhatsApp messages."""

    # --------------------------------------------------------------- in-app

    async def record_in_app(
        self,
        session,
        firm_id,
        notification_type,
        title: str,
        body: Optional[str] = None,
        user_id=None,
        matter_id=None,
        link_path: Optional[str] = None,
    ):
        """
        Write an in-app notification row.

        Does NOT commit — the caller owns the transaction so a reminder row and
        its notification are committed together.
        """
        # Imported here to keep this module importable from Celery workers that
        # do not otherwise pull in the ORM.
        from backend.models import Notification

        notification = Notification(
            firm_id=firm_id,
            user_id=user_id,
            matter_id=matter_id,
            notification_type=notification_type,
            title=title,
            body=body,
            link_path=link_path,
        )
        session.add(notification)
        return notification

    # ---------------------------------------------------------------- email

    @property
    def email_configured(self) -> bool:
        return bool(settings.SENDGRID_API_KEY)

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
    ) -> SendResult:
        """Send a transactional email via SendGrid."""
        if not self.email_configured:
            logger.warning("SendGrid not configured — email skipped")
            return SendResult(ok=False, channel="email", not_configured=True,
                              detail="SENDGRID_API_KEY not set")
        if not to_email:
            return SendResult(ok=False, channel="email", detail="no recipient")

        content = [{"type": "text/plain", "value": body_text}]
        if body_html:
            content.append({"type": "text/html", "value": body_html})

        payload = {
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {
                "email": settings.SENDGRID_FROM_EMAIL,
                "name": settings.SENDGRID_FROM_NAME,
            },
            "subject": subject,
            "content": content,
        }
        headers = {
            "Authorization": f"Bearer {settings.SENDGRID_API_KEY}",
            "Content-Type": "application/json",
        }
        return await self._post_with_retry(
            SENDGRID_URL, payload, headers, channel="email", recipient=to_email
        )

    # ------------------------------------------------------------- whatsapp

    @property
    def whatsapp_configured(self) -> bool:
        return bool(settings.WHATSAPP_API_TOKEN and settings.WHATSAPP_PHONE_NUMBER_ID)

    async def send_whatsapp(self, to_phone: str, message: str) -> SendResult:
        """
        Send a WhatsApp text message via the Meta Cloud API.

        NOTE on the 24-hour window: a free-form `text` message is only delivered
        if the recipient messaged the business within the last 24 hours.
        Business-initiated reminders outside that window require an approved
        message *template*. Meta returns error code 131047 in that case; we
        surface it verbatim in `detail` so the caller can record it, rather than
        silently reporting success.
        """
        if not self.whatsapp_configured:
            logger.warning("WhatsApp API not configured — message skipped")
            return SendResult(ok=False, channel="whatsapp", not_configured=True,
                              detail="WHATSAPP_API_TOKEN/PHONE_NUMBER_ID not set")

        phone = normalise_phone(to_phone)
        if not phone:
            return SendResult(ok=False, channel="whatsapp", detail="unparseable phone number")

        url = (
            f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}"
            f"/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
        )
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone,
            "type": "text",
            "text": {"preview_url": False, "body": message},
        }
        headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_API_TOKEN}",
            "Content-Type": "application/json",
        }
        return await self._post_with_retry(
            url, payload, headers, channel="whatsapp", recipient=phone
        )

    # ---------------------------------------------------------------- shared

    async def _post_with_retry(
        self,
        url: str,
        payload: dict,
        headers: dict,
        channel: str,
        recipient: str,
    ) -> SendResult:
        """POST with a bounded timeout and retries on transient failures only."""
        last_detail = ""
        for attempt in range(_MAX_ATTEMPTS):
            try:
                async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
                    resp = await client.post(url, json=payload, headers=headers)

                if 200 <= resp.status_code < 300:
                    logger.info(
                        "notification sent channel=%s recipient=%s status=%s",
                        channel, _mask(recipient), resp.status_code,
                    )
                    return SendResult(ok=True, channel=channel)

                # Provider error bodies can echo the message body; keep it short
                # and never log it at anything above debug.
                last_detail = f"HTTP {resp.status_code}: {resp.text[:200]}"
                if resp.status_code not in _RETRYABLE_STATUS:
                    logger.error(
                        "notification rejected channel=%s recipient=%s status=%s",
                        channel, _mask(recipient), resp.status_code,
                    )
                    return SendResult(ok=False, channel=channel, detail=last_detail)

            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_detail = f"{type(exc).__name__}: {exc}"

            if attempt < _MAX_ATTEMPTS - 1:
                await asyncio.sleep(_BACKOFF_SECONDS[attempt])

        logger.error(
            "notification failed channel=%s recipient=%s attempts=%s",
            channel, _mask(recipient), _MAX_ATTEMPTS,
        )
        return SendResult(ok=False, channel=channel, detail=last_detail)


# Singleton instance
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Get or create the notification service instance."""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service
