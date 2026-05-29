from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

from models.database import init_db
from routers import upload, analyze, reports, chat

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    os.makedirs(os.getenv("UPLOAD_DIR", "./uploads"), exist_ok=True)
    os.makedirs(os.getenv("REPORTS_DIR", "./reports"), exist_ok=True)
    yield


app = FastAPI(
    title="Bank Statement Analyser API",
    description="AI-powered bank statement analysis platform",
    version="1.0.0",
    lifespan=lifespan,
)

allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/api", tags=["Upload"])
app.include_router(analyze.router, prefix="/api", tags=["Analysis"])
app.include_router(reports.router, prefix="/api", tags=["Reports"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
