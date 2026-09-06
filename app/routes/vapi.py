from fastapi import APIRouter, Request
from sqlalchemy.orm import Session
from datetime import datetime

from ..database import SessionLocal
from ..models import Patient
from ..schemas import PatientCreate, PatientUpdate
from ..validator import clean_and_validate_US_Phone_number

router = APIRouter(prefix="/vapi", tags=["vapi"])

def _convert_date_format(date_str: str) -> str:
    """Converts MM/DD/YYYY (what Vapi sends) to YYYY-MM-DD (what Pydantic's date type expects)."""
    try:
        parsed = datetime.strptime(date_str, "%m/%d/%Y")
        return parsed.strftime("%Y-%m-%d")
    except ValueError:
        return date_str

def _extract_tool_call(body: dict):
    """Pulls out the tool call id + arguments from Vapi's webhook payload shape."""
    tool_calls = body.get("message", {}).get("toolCalls", [])
    if not tool_calls:
        return None, {}   # <-- return an empty dict, not None
    call = tool_calls[0]
    call_id = call.get("id")
    args = call.get("function", {}).get("arguments") or {}   # <-- guard against explicit null
    return call_id, args

@router.post("/find_patient_by_phone")
async def vapi_find_patient_by_phone(request: Request):
    body = await request.json()
    call_id, args = _extract_tool_call(body)

    db: Session = SessionLocal()
    try:
        phone_raw = args.get("phone_number", "")
        try:
            phone = clean_and_validate_US_Phone_number(phone_raw)
        except ValueError as e:
            return {"results": [{"toolCallId": call_id, "result": f"Invalid phone number: {e}"}]}

        patient = (
            db.query(Patient)
            .filter(Patient.phone_number == phone, Patient.deleted_at.is_(None))
            .first()
        )

        if patient:
            result = (
                f"Found existing patient: {patient.first_name} {patient.last_name}, "
                f"patient_id={patient.patient_id}"
            )
        else:
            result = "No existing patient found with this phone number."

        return {"results": [{"toolCallId": call_id, "result": result}]}
    finally:
        db.close()

@router.post("/create_patient")
async def vapi_create_patient(request: Request):
    body = await request.json()
    call_id, args = _extract_tool_call(body)

    db: Session = SessionLocal()
    try:
        # Convert date format before validation
        if "date_of_birth" in args:
            args["date_of_birth"] = _convert_date_format(args["date_of_birth"])

        try:
            validated = PatientCreate(**args)
        except Exception as e:
            return {"results": [{"toolCallId": call_id, "result": f"Validation error: {e}"}]}

        new_patient = Patient(**validated.model_dump())
        db.add(new_patient)
        db.commit()
        db.refresh(new_patient)

        result = (
            f"Patient saved successfully. Patient ID: {new_patient.patient_id}, "
            f"Name: {new_patient.first_name} {new_patient.last_name}"
        )
        return {"results": [{"toolCallId": call_id, "result": result}]}
    except Exception as e:
        db.rollback()
        return {"results": [{"toolCallId": call_id, "result": f"Error saving patient: {str(e)}"}]}
    finally:
        db.close()


@router.post("/update_patient")
async def vapi_update_patient(request: Request):
    body = await request.json()
    call_id, args = _extract_tool_call(body)

    db: Session = SessionLocal()
    try:
        phone_raw = args.pop("phone_number", None)
        if not phone_raw:
            return {"results": [{"toolCallId": call_id, "result": "Missing phone_number to identify the patient to update."}]}

        try:
            phone = clean_and_validate_US_Phone_number(phone_raw)
        except ValueError as e:
            return {"results": [{"toolCallId": call_id, "result": f"Invalid phone number: {e}"}]}

        patient = (
            db.query(Patient)
            .filter(Patient.phone_number == phone, Patient.deleted_at.is_(None))
            .first()
        )
        if not patient:
            return {"results": [{"toolCallId": call_id, "result": "No patient found with that phone number."}]}

        if "date_of_birth" in args:
            args["date_of_birth"] = _convert_date_format(args["date_of_birth"])

        try:
            validated = PatientUpdate(**args)
        except Exception as e:
            return {"results": [{"toolCallId": call_id, "result": f"Validation error: {e}"}]}

        update_data = validated.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(patient, field, value)

        db.commit()
        db.refresh(patient)

        return {"results": [{"toolCallId": call_id, "result": f"Patient updated successfully. Patient ID: {patient.patient_id}"}]}
    except Exception as e:
        db.rollback()
        return {"results": [{"toolCallId": call_id, "result": f"Error updating patient: {str(e)}"}]}
    finally:
        db.close()