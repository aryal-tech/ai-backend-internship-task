from pydantic import BaseModel, EmailStr
from datetime import datetime

class BookingRequest(BaseModel):
    """Schema for the LLM to call the booking tool."""
    name: str
    email: EmailStr
    date: str  
    time: str 

class BookingResponse(BaseModel):
    """Schema for the API response after a successful booking."""
    booking_id: str
    name: str
    email: EmailStr
    start_time_utc: datetime
    end_time_utc: datetime