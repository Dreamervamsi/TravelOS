import requests

from pathlib import Path
from fastapi import FastAPI, File, HTTPException, UploadFile, Depends
from fastapi.middleware.cors import CORSMiddleware
from config import get_settings

settings = get_settings()

GROQ_API_KEY = settings.groq_api_key
GROQ_MODEL = settings.groq_model
ELEVENLABS_API_KEY = settings.elevenlabs_api_key
ELEVENLABS_MODEL_ID = settings.elevenlabs_model_id

app = FastAPI(title="TravelOS Voice API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "TravelOS Voice API"}

@app.get("/api/transcribe")
def transcribe_info():
    return {"method": "POST", "path": "/api/transcribe", "field": "file"}

@app.post("/api/transcribe")
async def transcribe(file: UploadFile = File(...)):
    if not ELEVENLABS_API_KEY:
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
    groq_client = AsyncGroq(api_key=GROQ_API_KEY)

    try:
        await groq_client.chat.completions(
            model = GROQ_MODEL,
             messages=[
                {"role": "system", "content": "You are a helpful and concise AI assistant."},
                {"role": "user", "content": transcript}
            ],
            temperature=payload.temperature,
            max_tokens=1024,
        )

    return {"ok": True}
