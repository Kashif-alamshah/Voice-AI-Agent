from datetime import date, datetime
from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional
from .validator import clean_and_validate_US_Phone_number
import re

VALID_STATES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA",
    "KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
    "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT",
    "VA","WA","WV","WI","WY","DC"
}

VALID_SEX_OPTIONS = {"Male", "Female", "Other", "Decline to Answer"}

class PatientBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    date_of_birth: date
    sex: str = Field(description="Patient's sex")
    phone_number: str = Field(description="Patient's phone number")
    email:Optional[EmailStr] = Field(default=None, description="Patient's email address")

    address_line_1: str = Field(min_length=1, max_length=100, description="Patients address")
    address_line_2: Optional[str] = Field(default=None, max_length=100, description="Street address")
    city: str = Field(min_length=1, max_length=50, description="City")
    state: str = Field(min_length=2, max_length=2, description="State abbreviation")
    zip_code: str = Field(description="ZIP code")

    insurance_provider: Optional[str] = Field(default=None, description="Insurance provider")
    insurance_member_id: Optional[str] = Field(default=None, description="Member ID")
    preferred_language: Optional[str] = Field(default="English")

    emergency_contact_name: Optional[str] = Field(default=None, description="Name of Emergency contact")
    emergency_contact_phone: Optional[str] = Field(default=None, description="Emergency contact")

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, value):
        if value is None:
            return value
        return clean_and_validate_US_Phone_number(value)


    @field_validator("emergency_contact_phone")
    @classmethod
    def validate_emergency_contact_phone(cls,value):
        if value is not None:
            return clean_and_validate_US_Phone_number(value)
        return value

    @field_validator("state")
    @classmethod
    def validate_state(cls, value):
        if value is None:
            return value
        value = value.upper()
        if value not in VALID_STATES:
            raise ValueError(f"Invalid state abbreviation: {value}. Must be a valid US state abbreviation.")
        return value

    @field_validator("sex")
    @classmethod
    def validate_sex(cls, value):
        if value is None:
            return value
        if value not in VALID_SEX_OPTIONS:
            raise ValueError(f"Invalid sex option: {value}. Must be one of {VALID_SEX_OPTIONS}.")
        return value

    @field_validator("zip_code")
    @classmethod
    def validate_zip_code(cls, value):
        if value is None:
            return value
        if not re.match(r"^\d{5}(-\d{4})?$", value):
            raise ValueError("ZIP code must be 5 digits or ZIP+4 format")
        return value    

    @field_validator("date_of_birth")
    @classmethod   
    def validate_date_of_birth(cls, value):
        if value is None:
            return value
        if value > date.today():
            raise ValueError("Date of birth cannot be in the future.")
        return value

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, value):
        if value is None:
            return value
        if not re.match(r"^[A-Za-z'\-\s]{1,50}$", value):
            raise ValueError("Names must be 1-50 alphabetic characters, hyphens, or apostrophes")
        return value
  

class PatientCreate(PatientBase):
    pass

class PatientUpdate(PatientBase):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    sex: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_member_id: Optional[str] = None
    preferred_language: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None

    

class PatientOut(PatientBase):
    patient_id: str
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    model_config = {"from_attributes": True}