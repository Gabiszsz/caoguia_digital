import subprocess
import numpy as np
from fastapi.testclient import TestClient
from app import main, transcription


def test_gpu_runtime_fails_then_falls_back_to_cpu(monkeypatch):
    class BrokenGPU:
        def transcribe(self, audio, **kwargs):
            def delayed():
                raise RuntimeError("CUDA encode falhou depois que transcribe retornou")
                yield None
            return delayed(), None
    class WorkingCPU:
        def transcribe(self, audio, **kwargs):
            return iter([type("Segment", (), {"text": "Programa Cão-Guia"})()]), None
    monkeypatch.setattr(transcription, "get_whisper_model", lambda: BrokenGPU())
    monkeypatch.setattr(transcription, "get_cpu_model", lambda: WorkingCPU())
    monkeypatch.setattr(transcription, "decode_audio", lambda audio: np.ones(20000, dtype=np.float32)*0.01)
    assert transcription.transcribe_audio(b"audio", ".webm") == "Programa Cão-Guia"


def test_cpu_retry_without_cuda(monkeypatch):
    class RetryCPU:
        def __init__(self): self.calls = 0
        def transcribe(self, audio, **kwargs):
            self.calls += 1
            if self.calls == 1: raise RuntimeError("falha temporária")
            return iter([type("Segment", (), {"text": "Olá"})()]), None
    obj=RetryCPU()
    monkeypatch.setattr(transcription, "get_whisper_model", lambda: obj)
    monkeypatch.setattr(transcription, "get_cpu_model", lambda: obj)
    monkeypatch.setattr(transcription, "decode_audio", lambda audio: np.ones(20000, dtype=np.float32)*0.01)
    assert transcription.transcribe_audio(b"audio", ".webm") == "Olá"
    assert obj.calls == 2


def test_transcription_status_endpoint_no_audio_saved():
    result=TestClient(main.app).get("/api/v1/transcribe/status")
    assert result.status_code == 200
    body=result.json()
    assert isinstance(body["ffmpeg_available"], bool)
    assert "whisper_device" in body
    assert "cpu_model" in body
    assert "transcript" not in body
