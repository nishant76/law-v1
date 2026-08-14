"""
Deadline Service — business logic for deadline tracking and reminders
Handles creation, retrieval, reminders, and condonation drafts

Reminder cadence: 30 / 7 / 1 days before the key date (CLAUDE.md Feature 9).
One DeadlineReminder row is written per offset that is still in the future, so
the daily job can send each one exactly once and record its own delivery state.

The client's phone number is read from `law.matters.client_phone` at send time
rather than copied onto the reminder — one number per matter, no drift.
"""
import uuid
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models import (
    DeadlineReminder,
    ReminderType,
    ReminderStatus,
    Draft,
    DraftType,
    DraftStatus,
    Matter,
    Notification,
    NotificationType,
    User,
)
from backend.services.llm_service import get_llm_service, ModelType
from backend.services.notification_service import get_notification_service
from backend.services.prompts.condonation_draft import condonation_draft_prompt
from backend.core.logger import get_logger
from backend.core.config import settings

logger = get_logger(__name__)

# Days before the key date at which the lawyer (and, for hearings, the client)
# is reminded.
REMINDER_OFFSETS_DAYS: Tuple[int, ...] = (30, 7, 1)


def _utcnow() -> datetime:
    """Timezone-aware UTC now. Reminder columns are TIMESTAMPTZ."""
    return datetime.now(timezone.utc)


def _as_aware(value: datetime) -> datetime:
    """Treat a naive datetime as UTC so comparisons never raise."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


class DeadlineService:
    """Deadline and reminder management service"""

    def __init__(self):
        self.llm_service = get_llm_service()
        self.notifications = get_notification_service()

    async def create_deadline(
        self,
        session: AsyncSession,
        matter_id: str,
        firm_id: str,
        deadline_type: ReminderType,
        deadline_date: datetime,
        description: str,
        client_phone: Optional[str] = None,
    ) -> List[DeadlineReminder]:
        """
        Create the reminder set for one deadline.

        Writes one row per offset in REMINDER_OFFSETS_DAYS whose reminder date
        has not already passed. If the deadline is closer than the smallest
        offset, a single reminder is created for right now so an imminent
        deadline is never silently un-reminded.

        `client_phone`, when supplied, is written onto the matter (the single
        source of truth) rather than duplicated onto every reminder row.

        Returns:
            The created DeadlineReminder rows, earliest reminder first.
        """
        try:
            key_date = _as_aware(deadline_date)
            now = _utcnow()

            if client_phone:
                await session.execute(
                    update(Matter)
                    .where(
                        Matter.id == uuid.UUID(matter_id),
                        Matter.firm_id == uuid.UUID(firm_id),
                    )
                    .values(client_phone=client_phone)
                )

            title = f"{deadline_type.value.replace('_', ' ').title()} — {description[:80]}"

            reminder_dates = [
                key_date - timedelta(days=offset)
                for offset in REMINDER_OFFSETS_DAYS
                if key_date - timedelta(days=offset) > now
            ]
            # Deadline nearer than the smallest offset: remind immediately.
            if not reminder_dates and key_date > now:
                reminder_dates = [now]

            created: List[DeadlineReminder] = []
            for reminder_date in sorted(reminder_dates):
                reminder = DeadlineReminder(
                    firm_id=uuid.UUID(firm_id),
                    matter_id=uuid.UUID(matter_id),
                    reminder_type=deadline_type,
                    title=title,
                    description=description,
                    key_date=key_date,
                    reminder_date=reminder_date,
                )
                session.add(reminder)
                created.append(reminder)

            if not created:
                logger.info(
                    "No reminders created for matter=%s — key date is in the past",
                    matter_id,
                )

            await session.flush()
            await session.commit()

            logger.info(
                "Created %d reminders for matter=%s type=%s",
                len(created), matter_id, deadline_type.value,
            )
            return created

        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to create deadline: {str(e)}")
            raise

    async def get_upcoming_deadlines(
        self,
        session: AsyncSession,
        firm_id: str,
        days_ahead: int = 30,
    ) -> List[Tuple[DeadlineReminder, Optional[Matter]]]:
        """
        Get upcoming deadlines for a firm, each with its matter.

        Filters on the KEY date, not the reminder date — the lawyer asking for
        "the next 30 days" means hearings and deadlines falling in that window.
        Missed deadlines are included so they surface in the UI (that is where
        the condonation-draft action lives).

        Reminders are collapsed to one row per (matter, key date, type): the
        30/7/1 rows are three deliveries of ONE deadline and must not appear in
        the list three times.
        """
        try:
            now = _utcnow()
            cutoff_date = now + timedelta(days=days_ahead)

            stmt = (
                select(DeadlineReminder, Matter)
                .join(Matter, Matter.id == DeadlineReminder.matter_id)
                .where(
                    and_(
                        DeadlineReminder.firm_id == uuid.UUID(firm_id),
                        DeadlineReminder.deleted_at.is_(None),
                        DeadlineReminder.key_date <= cutoff_date,
                    )
                )
                .order_by(DeadlineReminder.key_date, DeadlineReminder.reminder_date)
            )

            rows = list((await session.execute(stmt)).all())

            deduped: Dict[Tuple, Tuple[DeadlineReminder, Optional[Matter]]] = {}
            for reminder, matter in rows:
                key = (
                    reminder.matter_id,
                    _as_aware(reminder.key_date),
                    reminder.reminder_type,
                )
                # Keep the row that best represents the deadline's state: a
                # MISSED row wins, otherwise the first (earliest) one.
                existing = deduped.get(key)
                if existing is None or reminder.status == ReminderStatus.MISSED:
                    deduped[key] = (reminder, matter)

            deadlines = list(deduped.values())
            logger.info(f"Found {len(deadlines)} upcoming deadlines for firm {firm_id}")
            return deadlines

        except Exception as e:
            logger.error(f"Failed to get upcoming deadlines: {str(e)}")
            raise

    async def process_due_reminders(self, session: AsyncSession) -> int:
        """
        Process due reminders — in-app, email, and client WhatsApp.

        A reminder is only marked SENT once at least one channel succeeded (the
        in-app row always does), so a provider outage does not silently consume
        the reminder.

        Returns:
            Number of reminders processed
        """
        try:
            now = _utcnow()

            stmt = (
                select(DeadlineReminder)
                .where(
                    and_(
                        DeadlineReminder.deleted_at.is_(None),
                        DeadlineReminder.reminder_date <= now,
                        DeadlineReminder.status == ReminderStatus.PENDING,
                    )
                )
                .order_by(DeadlineReminder.reminder_date)
            )

            result = await session.execute(stmt)
            due_reminders = list(result.scalars().all())

            processed = 0
            for reminder in due_reminders:
                matter = await session.get(Matter, reminder.matter_id)
                lawyers = await self._firm_lawyers(session, reminder.firm_id)
                try:
                    await self._send_reminder_notifications(session, reminder, matter, lawyers)
                    reminder.status = ReminderStatus.SENT
                    reminder.sent_at = now
                    processed += 1
                except Exception as exc:
                    # One bad reminder must not abort the whole daily run.
                    logger.error(
                        "Reminder delivery failed reminder_id=%s: %s", reminder.id, exc
                    )

            await session.commit()

            logger.info(f"Processed {processed}/{len(due_reminders)} due reminders")
            return processed

        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to process due reminders: {str(e)}")
            raise

    async def _firm_lawyers(self, session: AsyncSession, firm_id) -> List[User]:
        """Active users of a firm who should receive reminder email."""
        stmt = select(User).where(
            User.firm_id == firm_id,
            User.deleted_at.is_(None),
            User.is_active.is_(True),
        )
        return list((await session.execute(stmt)).scalars().all())

    async def _send_reminder_notifications(
        self,
        session: AsyncSession,
        reminder: DeadlineReminder,
        matter: Optional[Matter],
        lawyers: List[User],
    ) -> None:
        """Send in-app, email, and (for hearings) client WhatsApp notifications."""
        days_before = self._days_before(reminder)
        case_name = matter.case_name if matter else reminder.title
        court = (matter.court if matter else None) or "court"

        # 1. In-app — always recorded, no external dependency.
        await self.notifications.record_in_app(
            session=session,
            firm_id=reminder.firm_id,
            user_id=None,  # firm-wide
            matter_id=reminder.matter_id,
            notification_type=(
                NotificationType.HEARING
                if reminder.reminder_type == ReminderType.HEARING
                else NotificationType.DEADLINE
            ),
            title=self._in_app_title(reminder, days_before, case_name),
            body=reminder.description,
            link_path=f"/app/cases/{reminder.matter_id}",
        )

        # 2. Email to every active lawyer in the firm.
        subject, body_text = self._email_content(reminder, days_before, case_name, court)
        email_ok = False
        for lawyer in lawyers:
            if not lawyer.email:
                continue
            result = await self.notifications.send_email(
                to_email=lawyer.email, subject=subject, body_text=body_text
            )
            email_ok = email_ok or result.ok
        reminder.email_sent = email_ok

        # 3. Client WhatsApp — hearings only, opt-in per matter, phone from matter.
        if (
            matter
            and matter.whatsapp_reminders_enabled
            and matter.client_phone
            and reminder.reminder_type == ReminderType.HEARING
            and days_before in (7, 1)
        ):
            message = self._format_whatsapp_message(reminder, matter, days_before)
            reminder.whatsapp_message_template = message[:1000]
            result = await self.notifications.send_whatsapp(matter.client_phone, message)
            reminder.whatsapp_sent = result.ok

    @staticmethod
    def _days_before(reminder: DeadlineReminder) -> int:
        """Which offset this reminder represents (30 / 7 / 1)."""
        delta = _as_aware(reminder.key_date) - _as_aware(reminder.reminder_date)
        return max(delta.days, 0)

    @staticmethod
    def _in_app_title(reminder: DeadlineReminder, days_before: int, case_name: str) -> str:
        when = {0: "today", 1: "tomorrow"}.get(days_before, f"in {days_before} days")
        if reminder.reminder_type == ReminderType.HEARING:
            return f"Hearing {when} — {case_name}"
        label = reminder.reminder_type.value.replace("_", " ")
        return f"{label.capitalize()} {when} — {case_name}"

    def _email_content(
        self,
        reminder: DeadlineReminder,
        days_before: int,
        case_name: str,
        court: str,
    ) -> Tuple[str, str]:
        """Subject + plain-text body for the lawyer's reminder email."""
        key_date = _as_aware(reminder.key_date).strftime("%d %B %Y")
        when = {0: "today", 1: "tomorrow"}.get(days_before, f"in {days_before} days")
        kind = (
            "Hearing"
            if reminder.reminder_type == ReminderType.HEARING
            else reminder.reminder_type.value.replace("_", " ").title()
        )
        subject = f"{kind} {when}: {case_name} ({key_date})"
        lines = [
            f"{kind} {when} — {key_date}",
            "",
            f"Matter: {case_name}",
            f"Court: {court}",
        ]
        if reminder.description:
            lines += ["", reminder.description]
        lines += [
            "",
            f"Open the matter: {settings.APP_BASE_URL}/app/cases/{reminder.matter_id}",
            "",
            "— SuperAdvocate",
        ]
        return subject, "\n".join(lines)

    def _format_whatsapp_message(
        self,
        reminder: DeadlineReminder,
        matter: Matter,
        days_before: int,
    ) -> str:
        """
        Client-facing WhatsApp reminder (Hinglish, as specified in CLAUDE.md).

        Every value is taken from real matter data — no bracketed placeholders
        are ever sent to a client. A field we do not have is left out of the
        sentence rather than filled with a guess.
        """
        key_date = _as_aware(reminder.key_date).strftime("%d/%m/%Y")
        case_name = matter.case_name
        lawyer_line = ""
        if matter.court:
            lawyer_line = f" Court: {matter.court}."

        if reminder.reminder_type == ReminderType.HEARING:
            if days_before == 1:
                return (
                    f"Kal {key_date} ko aapke matter \"{case_name}\" ki hearing hai."
                    f"{lawyer_line} Kripya samay se pahunchein."
                )
            return (
                f"Aapka matter \"{case_name}\" ki agli sunwai {key_date} ko hai."
                f"{lawyer_line} Koi document chahiye toh apne advocate se sampark karein."
            )

        return (
            f"Aapke matter \"{case_name}\" mein {key_date} ko ek important deadline hai. "
            f"Kripya apne advocate se sampark karein."
        )

    async def mark_deadline_missed(
        self,
        session: AsyncSession,
        deadline_id: str,
        firm_id: str,
    ) -> bool:
        """
        Mark a deadline as missed.

        Also records an in-app notification so the condonation-draft prompt
        ("Draft condonation of delay application?") surfaces without the lawyer
        having to revisit the deadline list.
        """
        try:
            now = _utcnow()
            stmt = select(DeadlineReminder).where(
                and_(
                    DeadlineReminder.id == uuid.UUID(deadline_id),
                    DeadlineReminder.firm_id == uuid.UUID(firm_id),
                    DeadlineReminder.deleted_at.is_(None),
                )
            )
            reminder = (await session.execute(stmt)).scalar_one_or_none()
            if reminder is None:
                logger.warning(
                    f"Deadline {deadline_id} not found or not owned by firm {firm_id}"
                )
                return False

            reminder.status = ReminderStatus.MISSED
            reminder.missed_at = now

            matter = await session.get(Matter, reminder.matter_id)
            await self.notifications.record_in_app(
                session=session,
                firm_id=reminder.firm_id,
                matter_id=reminder.matter_id,
                notification_type=NotificationType.DEADLINE_MISSED,
                title=f"Deadline missed — {matter.case_name if matter else reminder.title}",
                body="A condonation of delay application can be drafted from this deadline.",
                link_path=f"/app/cases/{reminder.matter_id}",
            )

            await session.commit()
            logger.info(f"Marked deadline {deadline_id} as missed")
            return True

        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to mark deadline as missed: {str(e)}")
            raise

    async def generate_condonation_draft(
        self,
        session: AsyncSession,
        deadline_id: str,
        firm_id: str,
        reason_for_delay: str,
    ) -> Optional[Draft]:
        """
        Generate condonation of delay draft for missed deadline

        Args:
            session: Database session
            deadline_id: Deadline ID
            firm_id: Firm ID
            reason_for_delay: Reason provided by lawyer

        Returns:
            Created Draft object or None if failed
        """
        try:
            # Get deadline details
            stmt = select(DeadlineReminder).where(
                and_(
                    DeadlineReminder.id == uuid.UUID(deadline_id),
                    DeadlineReminder.firm_id == uuid.UUID(firm_id),
                    DeadlineReminder.deleted_at.is_(None),
                )
            )
            result = await session.execute(stmt)
            deadline = result.scalar_one_or_none()

            if not deadline:
                logger.warning(f"Deadline {deadline_id} not found for firm {firm_id}")
                return None

            # Real matter data — a draft must never carry "placeholder" text
            # into a document a lawyer might file (LAUNCH QUALITY MANDATE).
            matter = await session.get(Matter, deadline.matter_id)
            if matter is None:
                logger.warning(f"Matter for deadline {deadline_id} not found")
                return None

            matter_details = self._matter_brief(matter, deadline)
            court = matter.court or "NOT SPECIFIED — infer from matter"
            client_name = matter.client_name or "NOT SPECIFIED"

            lawyer_stmt = select(User).where(
                User.firm_id == uuid.UUID(firm_id),
                User.deleted_at.is_(None),
                User.is_active.is_(True),
            ).limit(1)
            lawyer = (await session.execute(lawyer_stmt)).scalar_one_or_none()
            lawyer_name = (lawyer.name if lawyer else None) or "NOT SPECIFIED"

            # Call LLM for draft
            system_prompt = condonation_draft_prompt.system_prompt
            user_prompt = condonation_draft_prompt.format_user_prompt(
                court=court,
                matter_details=matter_details,
                missed_deadline_date=_as_aware(deadline.key_date).date().isoformat(),
                reason_for_delay=reason_for_delay,
                client_name=client_name,
                lawyer_name=lawyer_name,
                # Citations are added through the verified-citation flow in the
                # filing drafter; this prompt must never invent its own.
                verified_citations="[]",
            )

            response_text = await self.llm_service.call_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=ModelType(condonation_draft_prompt.model.value),
                temperature=0.0,
                max_tokens=1500,
                firm_id=firm_id,
            )

            # Parse JSON response
            import json
            draft_data = json.loads(response_text)

            # Create draft record
            draft = Draft(
                firm_id=uuid.UUID(firm_id),
                matter_id=deadline.matter_id,
                draft_type=DraftType.CONDONATION,
                title=f"Condonation of Delay - {deadline.title}",
                content=json.dumps(draft_data),
                status=DraftStatus.GENERATED,
                confidence_score=draft_data.get("confidence_score", 0),
            )

            session.add(draft)
            await session.flush()
            await session.commit()

            logger.info(f"Generated condonation draft: {draft.id}")
            return draft

        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to generate condonation draft: {str(e)}")
            raise

    @staticmethod
    def _matter_brief(matter: Matter, deadline: DeadlineReminder) -> str:
        """Compact factual summary of a matter for the condonation prompt."""
        bits = [f"Case: {matter.case_name}"]
        if matter.matter_number:
            bits.append(f"Case number: {matter.matter_number}")
        if matter.cnr_number:
            bits.append(f"CNR: {matter.cnr_number}")
        if matter.matter_type:
            bits.append(f"Matter type: {matter.matter_type}")
        if matter.petitioner:
            bits.append(f"Petitioner: {matter.petitioner}")
        if matter.respondent:
            bits.append(f"Respondent: {matter.respondent}")
        bits.append(f"Missed step: {deadline.description or deadline.title}")
        return "\n".join(bits)


# Singleton instance
_deadline_service: Optional[DeadlineService] = None


def get_deadline_service() -> DeadlineService:
    """Get or create deadline service instance"""
    global _deadline_service
    if _deadline_service is None:
        _deadline_service = DeadlineService()
    return _deadline_service
