import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Date, DateTime
from .database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Patient(Base):
    __tablename__ = "patients"

    patient_id = Column(String, primary_key=True, default=generate_uuid)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    sex = Column(String(20), nullable=False)
    phone_number = Column(String(10), nullable=False)
    email=Column(String(100), nullable=True)

    address_line_1=Column(String(100), nullable=False)
    address_line_2=Column(String(100), nullable=True)

    city=Column(String(100), nullable=False)
    state=Column(String(2), nullable=False)
    zip_code=Column(String(5), nullable=False)

    insurance_provider=Column(String, nullable=True)
    insurance_member_id=Column(String, nullable=True)
    preferred_language=Column(String(50), nullable=True,default="English")

    emergency_contact_name=Column(String, nullable=True)
    emergency_contact_phone=Column(String(10), nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime, 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc)
    )
    deleted_at = Column(DateTime, nullable=True)