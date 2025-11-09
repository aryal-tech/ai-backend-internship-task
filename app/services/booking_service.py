from uuid import uuid4
from datetime import datetime, timedelta, timezone
from dateutil.parser import parse as parse_datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text as sql_text
from pydantic import EmailStr
import email_validator

class BookingService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _validate_and_parse(self, name: str, email: EmailStr, date_str: str, time_str: str) -> datetime:
        if not name or not email:
            raise ValueError("Name and email are required.")
        
        email_validator.validate_email(email)

        try:
            parsed_dt = parse_datetime(f"{date_str} {time_str}")
            if parsed_dt.tzinfo is None:
                parsed_dt = parsed_dt.astimezone()
            return parsed_dt.astimezone(timezone.utc)
        except Exception as e:
            raise ValueError(f"Invalid date or time format: '{date_str} {time_str}'. Error: {e}")

    async def _check_conflict(self, start_time_utc: datetime, end_time_utc: datetime) -> bool:
        query = sql_text("""
            SELECT 1 FROM bookings
            WHERE (:start < end_time_utc) AND (:end > start_time_utc)
            LIMIT 1
        """)
        result = await self.session.execute(query, {"start": start_time_utc, "end": end_time_utc})
        return result.scalar() is not None

    async def create_booking(
        self, name: str, email: EmailStr, date_str: str, time_str: str, conversation_id: str
    ) -> dict:
        start_time_utc = self._validate_and_parse(name, email, date_str, time_str)
        end_time_utc = start_time_utc + timedelta(hours=1)

        if await self._check_conflict(start_time_utc, end_time_utc):
            raise ValueError(f"Booking conflict: The slot at {start_time_utc.isoformat()} is already taken.")

        booking_id = str(uuid4())
        insert_query = sql_text("""
            INSERT INTO bookings (id, name, email, start_time_utc, end_time_utc, source_conversation_id)
            VALUES (:id, :name, :email, :start, :end, :conv_id)
        """)
        try:
            await self.session.execute(insert_query, {
                "id": booking_id, "name": name, "email": str(email),
                "start": start_time_utc, "end": end_time_utc, "conv_id": conversation_id,
            })
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise RuntimeError(f"Database error while saving booking: {e}")
            
        return {
            "booking_id": booking_id, "name": name, "email": email,
            "start_time_utc": start_time_utc, "end_time_utc": end_time_utc
        }