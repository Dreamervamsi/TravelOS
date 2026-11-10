# TravelOS voice assistant

An Expo React Native travel home screen with a right-hand reachable **Ask AI** action and an animated voice orb, plus a FastAPI endpoint that sends recorded audio to ElevenLabs STT and prints only the transcript in the server terminal.

## Frontend

Dependencies are listed in `package.json`; nothing has been installed. Once you install them manually, run `npx expo start`.

Set `API_BASE_URL` in `App.tsx` to the backend URL reachable from the device. Android emulator typically uses `http://10.0.2.2:8000`; a physical phone needs your computer's LAN IP. iOS simulator can use `http://127.0.0.1:8000`.

The voice session starts when Ask AI opens. It records until it detects speech followed by 1.6 seconds of quiet, uploads that recording, then closes automatically. The UI deliberately does not show the transcription.

## Backend

From `backend/`, install the entries in `requirements.txt` manually. Set your key in `backend/.env`, then start the service with `uvicorn main:app --reload --host 0.0.0.0 --port 8000`.

- `GET /api/health` health check
- `GET /api/transcribe` endpoint usage information
- `POST /api/transcribe` accepts multipart form audio in field `file`; prints `User said: ...` in the terminal

The backend calls the ElevenLabs Speech to Text API using the configured model ID. Keep the key on the backend; never put it in the mobile app.
