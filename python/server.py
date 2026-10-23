"""
ElevenX FastAPI + WebSocket server (Python Orchestration Layer)
"""

import io
import wave
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from elevenx_engine import ElevenXEngine

app = FastAPI(title="ElevenX Voice AI API", version="1.0.0")
engine = ElevenXEngine()


class SynthesisRequest(BaseModel):
    text: str
    reference_audio_path: str
    emotion: str = "neutral"
    spatial: bool = False


def numpy_to_wav_bytes(audio: np.ndarray, sample_rate: int) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        channels = 1 if audio.ndim == 1 else audio.shape[1]
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes((audio * 32767).astype(np.int16).tobytes())
    buffer.seek(0)
    return buffer.read()


@app.websocket("/ws/tts")
async def websocket_tts(websocket: WebSocket):
    await websocket.accept()
    try:
        data = await websocket.receive_json()
        text = data.get("text", "")
        ref_audio = data.get("reference_audio", "")
        emotion = data.get("emotion", "neutral")

        for chunk in engine.synthesize_stream(text, ref_audio, emotion):
            pcm_bytes = (chunk * 32767).astype(np.int16).tobytes()
            await websocket.send_bytes(pcm_bytes)

        await websocket.send_text("[DONE]")
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        await websocket.send_text(f"[ERROR] {str(e)}")
    finally:
        await websocket.close()


@app.post("/synthesize")
async def synthesize(request: SynthesisRequest):
    audio = engine.synthesize_full(
        request.text,
        request.reference_audio_path,
        request.emotion,
        request.spatial
    )
    wav_bytes = numpy_to_wav_bytes(audio, engine.sample_rate)
    return StreamingResponse(io.BytesIO(wav_bytes), media_type="audio/wav")


@app.get("/health")
async def health():
    return {"status": "ok", "engine": "ElevenX", "sample_rate": engine.sample_rate}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
