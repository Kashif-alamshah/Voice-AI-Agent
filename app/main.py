from fastapi import FastAPI
from .database import engine, Base
from .routes.patient import router as patient_router
from .routes.vapi import router as vapi_router

app = FastAPI()

Base.metadata.create_all(bind=engine)

app.include_router(patient_router)
app.include_router(vapi_router)

@app.get("/")
async def read_root():
    return {"data": "API is Running",
            "error": False,}