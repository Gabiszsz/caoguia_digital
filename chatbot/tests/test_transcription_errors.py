import numpy as np
from app import transcription
import pytest

class FakeSegment:
    text = "Como funciona o programa?"

class FakeWhisper:
    def __init__(self, fail=False):
        self.fail = fail
    def transcribe(self, samples, **kw):
        assert isinstance(samples, np.ndarray)
        assert samples.dtype == np.float32
        assert kw["language"] == "pt"
        if self.fail:
            raise RuntimeError("falha do modelo")
        return iter([FakeSegment()]), None

def test_transcription_uses_pcm_array(monkeypatch):
    monkeypatch.setattr(transcription, "get_whisper_model", lambda: FakeWhisper())
    monkeypatch.setattr(transcription, "decode_audio", lambda _: np.ones(16000,dtype=np.float32)*0.02)
    assert transcription.transcribe_audio(b"data", ".webm") == "Como funciona o programa?"

def test_transcription_failure_has_actionable_message(monkeypatch):
    monkeypatch.setattr(transcription, "get_whisper_model", lambda: FakeWhisper(fail=True))
    monkeypatch.setattr(transcription, "decode_audio", lambda _: np.ones(16000,dtype=np.float32)*0.02)
    monkeypatch.setattr(transcription, "get_cpu_model", lambda: FakeWhisper(fail=True))
    with pytest.raises(transcription.TranscriptionError, match="etapa 7"):
        transcription.transcribe_audio(b"data", ".webm")
