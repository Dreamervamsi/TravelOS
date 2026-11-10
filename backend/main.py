import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

load_dotenv(Path(__file__).with_name(".env"))

app = FastAPI(title="TravelOS Voice API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to your app origins before production.
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_MODEL_ID = os.getenv("ELEVENLABS_MODEL_ID", "scribe_v2")


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "TravelOS Voice API"}


@app.get("/api/transcribe")
def transcribe_info():
    return {"method": "POST", "path": "/api/transcribe", "field": "file"}


@app.post("/api/transcribe")
async def transcribe(file: UploadFile = File(...)):
    if not ELEVENLABS_API_KEY or ELEVENLABS_API_KEY == "paste_your_elevenlabs_api_key_here":
        raise HTTPException(status_code=503, detail="Set ELEVENLABS_API_KEY in backend/.env first.")

    audio = await file.read()
    if not audio:
        raise HTTPException(status_code=400, detail="The uploaded audio file is empty.")

    try:
        response = requests.post(
            "https://api.elevenlabs.io/v1/speech-to-text",
            headers={"xi-api-key": ELEVENLABS_API_KEY},
            data={"model_id": ELEVENLABS_MODEL_ID},
            files={"file": (file.filename or "voice-question.m4a", audio, file.content_type or "audio/m4a")},
            timeout=90,
        )
        response.raise_for_status()
        transcript = response.json().get("text", "")
    except requests.RequestException as exc:
        detail = exc.response.text if exc.response is not None else str(exc)
        raise HTTPException(status_code=502, detail=f"ElevenLabs transcription failed: {detail}") from exc

    print(f"User said: {transcript}", flush=True)
    return {"ok": True}
