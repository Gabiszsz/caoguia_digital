from fastapi.testclient import TestClient
from app import main

client = TestClient(main.app)

def test_audio_transcribed(monkeypatch):
    def fake_transcribe(content, suffix):
        assert content == b'x' * 500
        assert suffix == '.webm'
        return 'Como funciona o programa Cão-Guia?'
    monkeypatch.setattr(main, 'transcribe_audio', fake_transcribe)
    response = client.post('/api/v1/transcribe', files={'audio': ('pergunta.webm', b'x'*500, 'audio/webm')})
    assert response.status_code == 200
    assert response.json()['text'] == 'Como funciona o programa Cão-Guia?'

def test_audio_rejects_invalid_type():
    response = client.post('/api/v1/transcribe', files={'audio': ('texto.txt', b'x'*500, 'text/plain')})
    assert response.status_code == 415

def test_audio_rejects_empty_recording():
    response = client.post('/api/v1/transcribe', files={'audio': ('x.webm', b'ab', 'audio/webm')})
    assert response.status_code == 422

def test_audio_rejects_too_large():
    response = client.post('/api/v1/transcribe', files={'audio': ('x.webm', b'x' * (15*1024*1024+1), 'audio/webm')})
    assert response.status_code == 413

def test_page_has_audio_controls():
    page = client.get('/').text
    assert 'dictateButton' in page
    assert 'uploadAudioButton' not in page
    assert 'audioFileInput' not in page
