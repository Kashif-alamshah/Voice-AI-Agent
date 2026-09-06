from fastapi import APIRouter, Depends,HTTPException,Query
from requests import get
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
from ..database import get_db
from ..models import Patient
from ..schemas import PatientCreate, PatientUpdate, PatientOut

router = APIRouter(prefix="/patients", tags=["Patients"])

@router.post("/", status_code=201)
def create_patient(patient: PatientCreate, db: Session = Depends(get_db)):
    db_patient = Patient(**patient.model_dump())
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    return {
        "data": PatientOut.model_validate(db_patient),
        "error": None,
    }

@router.get("")
def list_patients(
    last_name: Optional[str] = Query(None, description="Filter by last name"),
    date_of_birth: Optional[str] = Query(None, description="Filter by date of birth"),
    phone_number: Optional[str] = Query(None, description="Filter by phone number"),
    db: Session = Depends(get_db),
):
    query=db.query(Patient).filter(Patient.deleted_at.is_(None))
    if last_name:
        query = query.filter(Patient.last_name.ilike(last_name))
    if date_of_birth:
        query = query.filter(Patient.date_of_birth == date_of_birth)
    if phone_number:
        query = query.filter(Patient.phone_number == phone_number)

    patients = query.all()
    return {
        "data": [PatientOut.model_validate(patient) for patient in patients],
        "error": None,
    }

@router.get("/{patient_id}")
def get_patient(patient_id:str, db:Session = Depends(get_db)):
    patient=db.query(Patient).filter(Patient.patient_id==patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return {
        "data": PatientOut.model_validate(patient),
        "error": None,
    }

@router.put("/{patient_id}")
def update_patient(patient_id:str, update:PatientUpdate, db:Session=Depends(get_db)):
    patient=db.query(Patient).filter(Patient.patient_id==patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    update_data=update.model_dump(exclude_unset=True)
    for field,value in update_data.items():
        setattr(patient,field,value)

    db.commit()
    db.refresh(patient)
    return {"data": PatientOut.model_validate(patient), "error": None}

@router.delete("/{patient_id}")
def delete_patient(patient_id:str, db:Session = Depends(get_db)):
    patient=db.query(Patient).filter(Patient.patient_id==patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    patient.deleted_at=datetime.now(timezone.utc)
    db.commit()
    return {"data": {"patient_id": patient_id, "deleted": True}, "error": None}