"""
Deadline Service — business logic for deadline tracking and reminders
Handles creation, retrieval, reminders, and condonation drafts
"""
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import select, update, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import DeadlineReminder, ReminderType, ReminderStatus, Draft, DraftType, DraftStatus
from backend.services.llm_service import get_llm_service, ModelType
from backend.services.prompts.condonation_draft import condonation_draft_prompt
from backend.core.logger import get_logger
from backend.core.config import settings

logger = get_logger(__name__)


class DeadlineService:
    """Deadline and reminder management service"""

    def __init__(self):
        self.llm_service = get_llm_service()

    async def create_deadline(
        self,
        session: AsyncSession,
        matter_id: str,
        firm_id: str,
        deadline_type: ReminderType,
        deadline_date: datetime,
        description: str,
        client_phone: Optional[str] = None,
    ) -> DeadlineReminder:
        """
        Create a new deadline reminder

        Args:
            session: Database session
            matter_id: Matter ID
            firm_id: Firm ID
            deadline_type: Type of deadline
            deadline_date: The key date (hearing, filing, etc.)
            description: Description of the deadline
            client_phone: Client phone for WhatsApp reminders

        Returns:
            Created DeadlineReminder object
        """
        try:
            reminder = DeadlineReminder(
                firm_id=uuid.UUID(firm_id),
                matter_id=uuid.UUID(matter_id),
                reminder_type=deadline_type,
                title=f"{deadline_type.value.title()} - {description[:50]}",
                description=description,
                key_date=deadline_date,
                reminder_date=deadline_date - timedelta(days=7),  # Default 7 days before
                client_phone=client_phone,
            )

            session.add(reminder)
            await session.flush()
            await session.commit()

            logger.info(f"Created deadline reminder: {reminder.id}")
            return reminder

        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to create deadline: {str(e)}")
            raise

    async def get_upcoming_deadlines(
        self,
        session: AsyncSession,
        firm_id: str,
        days_ahead: int = 30,
    ) -> List[DeadlineReminder]:
        """
        Get upcoming deadlines for a firm

        Args:
            session: Database session
            firm_id: Firm ID
            days_ahead: Number of days to look ahead

        Returns:
            List of upcoming DeadlineReminder objects
        """
        try:
            cutoff_date = datetime.utcnow() + timedelta(days=days_ahead)

            stmt = select(DeadlineReminder).where(
                and_(
                    DeadlineReminder.firm_id == uuid.UUID(firm_id),
                    DeadlineReminder.deleted_at.is_(None),
                    DeadlineReminder.reminder_date <= cutoff_date,
                    DeadlineReminder.status.in_([ReminderStatus.PENDING, ReminderStatus.SENT]),
                )
            ).order_by(DeadlineReminder.reminder_date)

            result = await session.execute(stmt)
            deadlines = result.scalars().all()

            logger.info(f"Found {len(deadlines)} upcoming deadlines for firm {firm_id}")
            return deadlines

        except Exception as e:
            logger.error(f"Failed to get upcoming deadlines: {str(e)}")
            raise

    async def process_due_reminders(self, session: AsyncSession) -> int:
        """
        Process due reminders — send notifications and WhatsApp messages

        Args:
            session: Database session

        Returns:
            Number of reminders processed
        """
        try:
            now = datetime.utcnow()
            today = now.date()

            # Find reminders due today
            stmt = select(DeadlineReminder).where(
                and_(
                    DeadlineReminder.deleted_at.is_(None),
                    DeadlineReminder.reminder_date <= now,
                    DeadlineReminder.status == ReminderStatus.PENDING,
                )
            )

            result = await session.execute(stmt)
            due_reminders = result.scalars().all()

            processed = 0
            for reminder in due_reminders:
                await self._send_reminder_notifications(reminder)
                reminder.status = ReminderStatus.SENT
                processed += 1

            await session.commit()

            logger.info(f"Processed {processed} due reminders")
            return processed

        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to process due reminders: {str(e)}")
            raise

    async def _send_reminder_notifications(self, reminder: DeadlineReminder) -> None:
        """Send in-app, email, and WhatsApp notifications for a reminder"""
        try:
            # TODO: Implement in-app notification
            logger.info(f"Sending in-app notification for reminder {reminder.id}")

            # TODO: Send email via SendGrid
            logger.info(f"Sending email notification for reminder {reminder.id}")

            # Send WhatsApp if client phone provided
            if reminder.client_phone:
                await self._send_whatsapp_reminder(reminder)

        except Exception as e:
            logger.error(f"Failed to send notifications for reminder {reminder.id}: {str(e)}")

    async def _send_whatsapp_reminder(self, reminder: DeadlineReminder) -> None:
        """Send WhatsApp message to client"""
        try:
            message = self._format_whatsapp_message(reminder)

            # TODO: Implement WhatsApp Business API call
            logger.info(f"Sending WhatsApp to {reminder.client_phone}: {message}")

        except Exception as e:
            logger.error(f"Failed to send WhatsApp reminder: {str(e)}")

    def _format_whatsapp_message(self, reminder: DeadlineReminder) -> str:
        """Format WhatsApp message based on reminder type and timing"""
        key_date = reminder.key_date.strftime("%d/%m/%Y")

        if reminder.reminder_type == ReminderType.HEARING:
            days_until = (reminder.key_date.date() - datetime.utcnow().date()).days

            if days_until == 7:
                return f"Aapka matter {reminder.title} ki agli sunwai {key_date} ko hai. Koi documents chahiye toh [Lawyer Name] se contact karein."
            elif days_until == 1:
                return f"Kal {key_date} ko aapki hearing hai. Court: [Court], Time: 10:30 AM"
            else:
                return f"Aapke matter mein ek important deadline {key_date} ko hai. Please apne lawyer se contact karein."

        return f"Aapke matter mein ek important deadline {key_date} ko hai. Please apne lawyer se contact karein."

    async def mark_deadline_missed(
        self,
        session: AsyncSession,
        deadline_id: str,
        firm_id: str,
    ) -> bool:
        """
        Mark a deadline as missed

        Args:
            session: Database session
            deadline_id: Deadline ID
            firm_id: Firm ID

        Returns:
            Success status
        """
        try:
            stmt = (
                update(DeadlineReminder)
                .where(
                    and_(
                        DeadlineReminder.id == uuid.UUID(deadline_id),
                        DeadlineReminder.firm_id == uuid.UUID(firm_id),
                        DeadlineReminder.deleted_at.is_(None),
                    )
                )
                .values(status=ReminderStatus.MISSED)
            )

            result = await session.execute(stmt)
            await session.commit()

            if result.rowcount > 0:
                logger.info(f"Marked deadline {deadline_id} as missed")
                return True
            else:
                logger.warning(f"Deadline {deadline_id} not found or not owned by firm {firm_id}")
                return False

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

            # TODO: Get matter and court details
            matter_details = "Matter details placeholder"
            court = "District Court placeholder"
            client_name = "Client Name placeholder"
            lawyer_name = "Lawyer Name placeholder"

            # Call LLM for draft
            system_prompt = condonation_draft_prompt.system_prompt
            user_prompt = condonation_draft_prompt.format_user_prompt(
                court=court,
                matter_details=matter_details,
                missed_deadline_date=deadline.key_date.isoformat(),
                reason_for_delay=reason_for_delay,
                client_name=client_name,
                lawyer_name=lawyer_name,
                verified_citations="[]",  # TODO: Add citation verification
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


# Singleton instance
_deadline_service: Optional[DeadlineService] = None


def get_deadline_service() -> DeadlineService:
    """Get or create deadline service instance"""
    global _deadline_service
    if _deadline_service is None:
        _deadline_service = DeadlineService()
    return _deadline_service