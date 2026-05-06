from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

from api.routes import router
from config.settings import settings
from db.database import init_db

load_dotenv()

app = FastAPI(
    title="AI Audit Tool MVP",
    description="End-to-end audit automation: upload to output",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
async def startup() -> None:
    init_db()


@app.get("/health")
def health():
    return {"status": "ok", "llm_provider": settings.llm_provider}
