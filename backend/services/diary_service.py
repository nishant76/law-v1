"""
Diary Service — the lawyer's court diary.

`law.matters.next_hearing_date` answers "when is this matter next listed". A
diary has to answer three more questions that a single column cannot:

  1. What is listed on a given date, in board order?            → get_day()
  2. What happened on a past date, and how many adjournments?    → get_day() / matter history
  3. What am I in court for tomorrow?                            → daily cause list

All three read `law.hearing_entries` — one row per listed date per matter.
Entries are materialised from `matters.next_hearing_date` (which the eCourts
sync maintains) by ensure_scheduled_entries(), so a lawyer who never touches
the diary UI still gets a correct cause list.

Times: everything is stored UTC (CLAUDE.md). A "day" in this service means a
day in LOCAL_TIMEZONE (IST) converted to a UTC window — otherwise a 10:30 IST
hearing lands on the previous day for a UTC-day query.
"""
from __future__ import annotations

import uuid
from datetime import date as date_cls, datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence
from zoneinfo import ZoneInfo

from sqlalchemy import select, and_, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.logger import get_logger
from backend.models import (
    DeadlineReminder,
    HearingEntry,
    HearingStatus,
    Matter,
    NotificationType,
    ReminderStatus,
    ReminderType,
    User,
)
from backend.services.notification_service import get_notification_service

logger = get_logger(__name__)

LOCAL_TZ = ZoneInfo(settings.LOCAL_TIMEZONE)

# A cause-list WhatsApp message longer than this is truncated with a pointer
# back into the app — Meta rejects very long text bodies and a wall of text is
# unusable on a phone anyway.
_MAX_CAUSE_LIST_ITEMS = 25


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def local_day_bounds(day: date_cls) -> tuple[datetime, datetime]:
    """UTC [start, end) covering one local (IST) calendar day."""
    start_local = datetime.combine(day, time.min, tzinfo=LOCAL_TZ)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def local_today() -> date_cls:
    return _utcnow().astimezone(LOCAL_TZ).date()


class DiaryService:
    """Court diary: hearing entries, day view, and the daily cause list."""

    def __init__(self) -> None:
        self.notifications = get_notification_service()

    # ------------------------------------------------------------ materialise

    async def ensure_scheduled_entries(
        self,
        session: AsyncSession,
        firm_id: Optional[str] = None,
    ) -> int:
        """
        Create a SCHEDULED hearing entry for every matter that has a future
        `next_hearing_date` but no entry on that date.

        Idempotent — the (matter_id, hearing_date) partial unique index plus the
        pre-check below mean repeated runs do not duplicate. Called from the
        diary read path and from the daily sync job, so entries exist for
        matters imported before the diary was built.

        Returns:
            Number of entries created.
        """
        now = _utcnow()
        conditions = [
            Matter.deleted_at.is_(None),
            Matter.is_active.is_(True),
            Matter.next_hearing_date.isnot(None),
            Matter.next_hearing_date >= now - timedelta(days=1),
        ]
        if firm_id:
            conditions.append(Matter.firm_id == uuid.UUID(firm_id))

        matters = list((await session.execute(select(Matter).where(and_(*conditions)))).scalars())
        if not matters:
            return 0

        # Existing entries for these matters, keyed by (matter_id, local date).
        matter_ids = [m.id for m in matters]
        existing_rows = list((await session.execute(
            select(HearingEntry.matter_id, HearingEntry.hearing_date).where(
                HearingEntry.matter_id.in_(matter_ids),
                HearingEntry.deleted_at.is_(None),
            )
        )).all())
        existing = {
            (mid, _as_aware(hd).astimezone(LOCAL_TZ).date()) for mid, hd in existing_rows
        }

        created = 0
        for matter in matters:
            hearing_date = _as_aware(matter.next_hearing_date)
            key = (matter.id, hearing_date.astimezone(LOCAL_TZ).date())
            if key in existing:
                continue
            session.add(HearingEntry(
                firm_id=matter.firm_id,
                matter_id=matter.id,
                hearing_date=hearing_date,
                status=HearingStatus.SCHEDULED,
                court=matter.court,
                judge_name=matter.judge_name,
                from_ecourts=matter.ecourts_tracked,
            ))
            existing.add(key)
            created += 1

        if created:
            await session.commit()
            logger.info("Materialised %d scheduled hearing entries", created)
        return created

    # ---------------------------------------------------------------- reading

    async def get_day(
        self,
        session: AsyncSession,
        firm_id: str,
        day: date_cls,
    ) -> List[Dict[str, Any]]:
        """The cause list for one local calendar day, in board order."""
        start, end = local_day_bounds(day)
        stmt = (
            select(HearingEntry, Matter)
            .join(Matter, Matter.id == HearingEntry.matter_id)
            .where(
                HearingEntry.firm_id == uuid.UUID(firm_id),
                HearingEntry.deleted_at.is_(None),
                HearingEntry.hearing_date >= start,
                HearingEntry.hearing_date < end,
            )
            .order_by(HearingEntry.court, HearingEntry.board_number, Matter.case_name)
        )
        rows = list((await session.execute(stmt)).all())
        return [self._serialise(entry, matter) for entry, matter in rows]

    async def get_range(
        self,
        session: AsyncSession,
        firm_id: str,
        start_day: date_cls,
        end_day: date_cls,
    ) -> List[Dict[str, Any]]:
        """Entries between two local dates, inclusive — the week/month view."""
        start, _ = local_day_bounds(start_day)
        _, end = local_day_bounds(end_day)
        stmt = (
            select(HearingEntry, Matter)
            .join(Matter, Matter.id == HearingEntry.matter_id)
            .where(
                HearingEntry.firm_id == uuid.UUID(firm_id),
                HearingEntry.deleted_at.is_(None),
                HearingEntry.hearing_date >= start,
                HearingEntry.hearing_date < end,
            )
            .order_by(HearingEntry.hearing_date, HearingEntry.board_number)
        )
        rows = list((await session.execute(stmt)).all())
        return [self._serialise(entry, matter) for entry, matter in rows]

    async def get_matter_history(
        self,
        session: AsyncSession,
        firm_id: str,
        matter_id: str,
    ) -> List[Dict[str, Any]]:
        """Every recorded date for one matter, most recent first."""
        stmt = (
            select(HearingEntry, Matter)
            .join(Matter, Matter.id == HearingEntry.matter_id)
            .where(
                HearingEntry.firm_id == uuid.UUID(firm_id),
                HearingEntry.matter_id == uuid.UUID(matter_id),
                HearingEntry.deleted_at.is_(None),
            )
            .order_by(HearingEntry.hearing_date.desc())
        )
        rows = list((await session.execute(stmt)).all())
        return [self._serialise(entry, matter) for entry, matter in rows]

    # ---------------------------------------------------------------- writing

    async def create_entry(
        self,
        session: AsyncSession,
        firm_id: str,
        matter_id: str,
        hearing_date: datetime,
        created_by: Optional[str] = None,
        **fields: Any,
    ) -> Optional[HearingEntry]:
        """
        Add a date to the diary by hand.

        Returns None when the matter does not belong to the firm — the caller
        turns that into a 404, never a 403 (CLAUDE.md security rules).
        """
        matter = await self._owned_matter(session, firm_id, matter_id)
        if matter is None:
            return None

        entry = HearingEntry(
            firm_id=uuid.UUID(firm_id),
            matter_id=matter.id,
            hearing_date=_as_aware(hearing_date),
            status=HearingStatus.SCHEDULED,
            court=fields.get("court") or matter.court,
            judge_name=fields.get("judge_name") or matter.judge_name,
            board_number=fields.get("board_number"),
            purpose=fields.get("purpose"),
            appeared_by=fields.get("appeared_by"),
            created_by=uuid.UUID(created_by) if created_by else None,
        )
        session.add(entry)

        # Keep the matter's next hearing date in step when this is the nearest
        # future date, so the dashboard and reminders agree with the diary.
        await self._maybe_advance_matter(session, matter, entry.hearing_date)
        await session.commit()
        return entry

    async def record_outcome(
        self,
        session: AsyncSession,
        firm_id: str,
        entry_id: str,
        status: HearingStatus,
        outcome: Optional[str] = None,
        next_date: Optional[datetime] = None,
        adjournment_reason: Optional[str] = None,
        action_required: Optional[str] = None,
        appeared_by: Optional[str] = None,
        board_number: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Record what happened on a court date.

        This is the diary's central action. Recording an outcome with a
        `next_date`:
          * closes out the entry,
          * creates the next SCHEDULED entry,
          * rolls `matters.next_hearing_date` forward,
          * arms a fresh 30/7/1 reminder set for the new date.

        Returns the serialised entry, or None when not found for this firm.
        """
        stmt = select(HearingEntry).where(
            HearingEntry.id == uuid.UUID(entry_id),
            HearingEntry.firm_id == uuid.UUID(firm_id),
            HearingEntry.deleted_at.is_(None),
        )
        entry = (await session.execute(stmt)).scalar_one_or_none()
        if entry is None:
            return None

        entry.status = status
        if outcome is not None:
            entry.outcome = outcome
        if adjournment_reason is not None:
            entry.adjournment_reason = adjournment_reason
        if action_required is not None:
            entry.action_required = action_required
        if appeared_by is not None:
            entry.appeared_by = appeared_by
        if board_number is not None:
            entry.board_number = board_number

        matter = await session.get(Matter, entry.matter_id)

        # The date has now been dealt with, so its reminders are spent. Closing
        # them is what stops an attended hearing sitting in "Missed" forever
        # once its key date passes.
        if status != HearingStatus.SCHEDULED:
            await self._close_reminders_for(session, entry)

        if next_date is not None:
            next_dt = _as_aware(next_date)
            entry.next_date = next_dt
            await self._create_follow_up(session, entry, matter, next_dt)
        elif status == HearingStatus.DISPOSED and matter is not None:
            matter.case_status = "DISPOSED"
            matter.next_hearing_date = None

        await session.commit()
        return self._serialise(entry, matter)

    async def _close_reminders_for(
        self, session: AsyncSession, entry: HearingEntry
    ) -> int:
        """
        Mark reminders for this entry's court date as COMPLETED.

        Matches on the local (IST) day rather than an exact timestamp: a
        reminder's key_date is the hearing datetime, and the diary entry may
        carry a slightly different time for the same listing.
        """
        start, end = local_day_bounds(_as_aware(entry.hearing_date).astimezone(LOCAL_TZ).date())
        result = await session.execute(
            update(DeadlineReminder)
            .where(
                DeadlineReminder.matter_id == entry.matter_id,
                DeadlineReminder.deleted_at.is_(None),
                DeadlineReminder.reminder_type == ReminderType.HEARING,
                DeadlineReminder.key_date >= start,
                DeadlineReminder.key_date < end,
                DeadlineReminder.status.in_(
                    [ReminderStatus.PENDING, ReminderStatus.SENT, ReminderStatus.MISSED]
                ),
            )
            .values(status=ReminderStatus.COMPLETED)
        )
        return result.rowcount or 0

    async def _create_follow_up(
        self,
        session: AsyncSession,
        entry: HearingEntry,
        matter: Optional[Matter],
        next_dt: datetime,
    ) -> None:
        """Create the next scheduled entry, advance the matter, arm reminders."""
        if matter is None:
            return

        # Do not duplicate an entry the eCourts sync may already have created.
        next_local_day = next_dt.astimezone(LOCAL_TZ).date()
        start, end = local_day_bounds(next_local_day)
        exists = (await session.execute(
            select(func.count()).select_from(HearingEntry).where(
                HearingEntry.matter_id == entry.matter_id,
                HearingEntry.deleted_at.is_(None),
                HearingEntry.hearing_date >= start,
                HearingEntry.hearing_date < end,
            )
        )).scalar_one()

        if not exists:
            session.add(HearingEntry(
                firm_id=entry.firm_id,
                matter_id=entry.matter_id,
                hearing_date=next_dt,
                status=HearingStatus.SCHEDULED,
                court=entry.court or matter.court,
                judge_name=entry.judge_name or matter.judge_name,
                purpose=entry.action_required or None,
            ))

        matter.next_hearing_date = next_dt

        # Arm the reminder cadence for the new date. Imported here to avoid a
        # circular import (deadline_service does not import diary_service, but
        # keeping it local makes that guarantee obvious).
        from backend.services.deadline_service import REMINDER_OFFSETS_DAYS

        now = _utcnow()

        # Recording an outcome twice — correcting a typo, say — must not arm a
        # second set of reminders, or the lawyer and client get every reminder
        # twice. Undelivered reminders for this same date are cleared first;
        # already-sent ones are left alone so the delivery record survives.
        await session.execute(
            update(DeadlineReminder)
            .where(
                DeadlineReminder.matter_id == entry.matter_id,
                DeadlineReminder.deleted_at.is_(None),
                DeadlineReminder.reminder_type == ReminderType.HEARING,
                DeadlineReminder.key_date >= start,
                DeadlineReminder.key_date < end,
                DeadlineReminder.status == ReminderStatus.PENDING,
            )
            .values(deleted_at=now)
        )

        title = f"Hearing — {matter.case_name}"
        for offset in REMINDER_OFFSETS_DAYS:
            reminder_date = next_dt - timedelta(days=offset)
            if reminder_date <= now:
                continue
            session.add(DeadlineReminder(
                firm_id=entry.firm_id,
                matter_id=entry.matter_id,
                reminder_type=ReminderType.HEARING,
                title=title,
                description=entry.action_required or entry.purpose,
                key_date=next_dt,
                reminder_date=reminder_date,
            ))

    async def _maybe_advance_matter(
        self, session: AsyncSession, matter: Matter, hearing_date: datetime
    ) -> None:
        current = matter.next_hearing_date
        now = _utcnow()
        if hearing_date < now:
            return
        if current is None or _as_aware(current) < now or hearing_date < _as_aware(current):
            matter.next_hearing_date = hearing_date

    async def _owned_matter(
        self, session: AsyncSession, firm_id: str, matter_id: str
    ) -> Optional[Matter]:
        stmt = select(Matter).where(
            Matter.id == uuid.UUID(matter_id),
            Matter.firm_id == uuid.UUID(firm_id),
            Matter.deleted_at.is_(None),
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    # ------------------------------------------------------- daily cause list

    async def send_daily_cause_lists(self, session: AsyncSession) -> int:
        """
        Send every opted-in lawyer their own cause list for TOMORROW on WhatsApp.

        Internal to the firm — distinct from the per-matter client reminders.
        Sends nothing when a lawyer has no matters listed: a "you have nothing
        tomorrow" message every evening trains people to ignore the channel.

        Returns:
            Number of lawyers messaged.
        """
        notifier = self.notifications
        if not notifier.whatsapp_configured:
            logger.warning("WhatsApp not configured — daily cause list skipped")
            return 0

        await self.ensure_scheduled_entries(session)

        tomorrow = local_today() + timedelta(days=1)
        users = list((await session.execute(
            select(User).where(
                User.daily_cause_list_enabled.is_(True),
                User.deleted_at.is_(None),
                User.is_active.is_(True),
            )
        )).scalars())

        sent = 0
        for user in users:
            phone = user.whatsapp_number or user.phone
            if not phone:
                continue
            entries = await self.get_day(session, str(user.firm_id), tomorrow)
            listed = [e for e in entries if e["status"] == HearingStatus.SCHEDULED.value]
            if not listed:
                continue

            message = self.build_cause_list_message(tomorrow, listed)
            result = await notifier.send_whatsapp(phone, message)
            if result.ok:
                sent += 1
            else:
                # WhatsApp failed — make sure the list still reaches the lawyer.
                await notifier.record_in_app(
                    session=session,
                    firm_id=user.firm_id,
                    user_id=user.id,
                    notification_type=NotificationType.HEARING,
                    title=f"Cause list for {tomorrow.strftime('%d %b')} — {len(listed)} matter(s)",
                    body=message,
                    link_path="/app/hearings",
                )
        await session.commit()
        logger.info("Daily cause list sent to %d lawyers", sent)
        return sent

    @staticmethod
    def build_cause_list_message(day: date_cls, entries: Sequence[Dict[str, Any]]) -> str:
        """Format tomorrow's list for WhatsApp. Only real data — no placeholders."""
        header = f"Kal ({day.strftime('%d/%m/%Y')}) ki cause list — {len(entries)} matter(s):"
        lines = [header, ""]
        for i, e in enumerate(entries[:_MAX_CAUSE_LIST_ITEMS], start=1):
            bits = [e["case_name"]]
            if e.get("court"):
                bits.append(e["court"])
            if e.get("matter_number"):
                bits.append(e["matter_number"])
            if e.get("board_number"):
                bits.append(f"item {e['board_number']}")
            if e.get("purpose"):
                bits.append(e["purpose"])
            lines.append(f"{i}. " + " — ".join(bits))
        if len(entries) > _MAX_CAUSE_LIST_ITEMS:
            lines.append(f"…and {len(entries) - _MAX_CAUSE_LIST_ITEMS} more — see the app.")
        lines += ["", "— SuperAdvocate"]
        return "\n".join(lines)

    # --------------------------------------------------------------- helpers

    @staticmethod
    def _serialise(entry: HearingEntry, matter: Optional[Matter]) -> Dict[str, Any]:
        hearing_date = _as_aware(entry.hearing_date)
        return {
            "id": str(entry.id),
            "matter_id": str(entry.matter_id),
            "case_name": matter.case_name if matter else "",
            "matter_number": matter.matter_number if matter else None,
            "cnr_number": matter.cnr_number if matter else None,
            "client_name": matter.client_name if matter else None,
            "hearing_date": hearing_date.isoformat(),
            "hearing_date_local": hearing_date.astimezone(LOCAL_TZ).isoformat(),
            "status": entry.status.value,
            "court": entry.court,
            "judge_name": entry.judge_name,
            "board_number": entry.board_number,
            "purpose": entry.purpose,
            "outcome": entry.outcome,
            "adjournment_reason": entry.adjournment_reason,
            "next_date": _as_aware(entry.next_date).isoformat() if entry.next_date else None,
            "action_required": entry.action_required,
            "appeared_by": entry.appeared_by,
            "from_ecourts": entry.from_ecourts,
        }


# Singleton instance
_diary_service: Optional[DiaryService] = None


def get_diary_service() -> DiaryService:
    """Get or create the diary service instance."""
    global _diary_service
    if _diary_service is None:
        _diary_service = DiaryService()
    return _diary_service
