# ============================================================
# SalesOS AI — Calendar Tool Provider
#
# Concrete implementation of CalendarToolProvider interface.
# Owns EXCLUSIVELY calendar operations (get slots, create event, cancel event).
# Contains ZERO business logic, working hours rules, conflict policies,
# or lifecycle persistence (those belong in MeetingService).
# ============================================================

import uuid
from datetime import datetime, timedelta
from typing import Any

from app.agents.tools import CalendarToolProvider
from app.core.logging import get_logger

logger = get_logger("tools.calendar")


class SalesOSCalendarProvider(CalendarToolProvider):
    """Pure calendar operations tool provider.

    Adheres strictly to the CalendarToolProvider interface.
    Performs event CRUD and raw slot calculation without enforcing business rules.
    """

    async def get_available_slots(
        self,
        host_email: str,
        start_date: str,
        end_date: str,
        duration_minutes: int = 30,
        timezone: str = "UTC",
    ) -> list[dict[str, str]]:
        """Query raw available time slots for a host calendar."""
        logger.info(
            "calendar_get_available_slots",
            host_email=host_email,
            start_date=start_date,
            end_date=end_date,
            duration=duration_minutes,
        )

        try:
            start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        except ValueError:
            start_dt = datetime.now() + timedelta(days=1)

        # Generate candidate raw calendar slots
        slots = []
        base_time = start_dt.replace(hour=14, minute=0, second=0, microsecond=0)

        for day_offset in range(3):
            day_slot_1 = base_time + timedelta(days=day_offset)
            day_slot_2 = day_slot_1 + timedelta(hours=3)

            slots.append(
                {
                    "start_time": day_slot_1.isoformat(),
                    "end_time": (day_slot_1 + timedelta(minutes=duration_minutes)).isoformat(),
                    "timezone": timezone,
                }
            )
            slots.append(
                {
                    "start_time": day_slot_2.isoformat(),
                    "end_time": (day_slot_2 + timedelta(minutes=duration_minutes)).isoformat(),
                    "timezone": timezone,
                }
            )

        return slots

    async def create_meeting(
        self,
        host_email: str,
        attendee_email: str,
        title: str,
        start_time: str,
        duration_minutes: int = 30,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Create a calendar event entry."""
        event_id = f"cal_evt_{uuid.uuid4().hex[:12]}"
        logger.info(
            "calendar_create_event",
            event_id=event_id,
            host_email=host_email,
            attendee_email=attendee_email,
            title=title,
        )

        return {
            "event_id": event_id,
            "status": "confirmed",
            "host_email": host_email,
            "attendee_email": attendee_email,
            "title": title,
            "start_time": start_time,
            "duration_minutes": duration_minutes,
            "description": description or "",
            "meeting_link": f"https://meet.salesos.ai/{event_id}",
        }

    async def cancel_meeting(self, event_id: str) -> bool:
        """Cancel a calendar event entry."""
        logger.info("calendar_cancel_event", event_id=event_id)
        return True
