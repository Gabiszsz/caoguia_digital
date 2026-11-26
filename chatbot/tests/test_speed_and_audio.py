import io
import json
import subprocess
import numpy as np
from fastapi.testclient import TestClient
from app import main
from app import transcription
from app.rag import RAGAssistant, FALLBACK

client = TestClient(main.app)


def test_stream_response_and_factual_sources_kept_only_in_api(monkeypatch):
    class FakeAssistant:
        def stream_answer(self, question):
            assert 'cães' in question
            yield {'type': 'delta', 'text': 'As famílias socializadoras '}
            yield {'type': 'delta', 'text': 'apoiam o aprendizado.'}
            yield {'type': 'done', 'sources_found': True, 'sources': [
                {'document':'IF_Goiano.md', 'page':None,'score':.7,'source_url':None}]}
    monkeypatch.setattr(main, 'get_assistant', lambda: FakeAssistant())
    response=client.post('/api/v1/chat/stream',json={'message':'Como são treinados os cães-guia?'})
    assert response.status_code==200
    events=[json.loads(x) for x in response.text.splitlines()]
    assert [e['type'] for e in events]==['start','delta','delta','done']
    assert ''.join(e['text'] for e in events if e['type']=='delta')=='As famílias socializadoras apoiam o aprendizado.'
    assert events[-1]['sources_found']


def test_stream_no_hits_is_immediate_fallback():
    class FakeKB:
        def search(self, question): return []
    events=list(RAGAssistant(FakeKB()).stream_answer('Informação inexistente'))
    assert events[0] == {'type':'delta','text':FALLBACK}
    assert events[-1]['type']=='done'


def test_transcribe_api_uses_audio_endpoint(monkeypatch):
    monkeypatch.setattr(main, 'transcribe_audio', lambda data, suffix: 'Como funciona o treinamento?')
    r=client.post('/api/v1/transcribe',files={'audio':('pergunta.webm',b'123'*200,'audio/webm')})
    assert r.status_code==200
    assert r.json()['text']=='Como funciona o treinamento?'


def test_ffmpeg_decodes_actual_wav_to_pcm():
    # Gera um tom artificial para testar o decodificador, sem reconhecer palavras.
    wav = subprocess.run([
        'ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=440:duration=1',
        '-f','wav','pipe:1'],capture_output=True,check=True).stdout
    samples=transcription.decode_audio(wav)
    assert isinstance(samples,np.ndarray)
    assert samples.ndim==1
    assert 15000 < samples.size < 17000


def test_whisper_receives_float32_audio_without_pyav(monkeypatch):
    class FakeWhisper:
        def transcribe(self, audio, **opts):
            assert audio.dtype==np.float32
            assert opts['language']=='pt'
            assert opts['beam_size']==3
            assert 'Cão-Guia' in opts['initial_prompt']
            return [type('Part', (), {'text':'Olá, chatbot.'})()], None
    monkeypatch.setattr(transcription,'get_whisper_model',lambda: FakeWhisper())
    wav = subprocess.run([
        'ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=440:duration=1',
        '-f','wav','pipe:1'],capture_output=True,check=True).stdout
    assert transcription.transcribe_audio(wav,'.wav')=='Olá, chatbot.'


def test_frontend_does_not_render_sources():
    js = client.get('/static/app.js').text
    assert 'sourceWrap' not in js
    assert 'Fonte:' not in js
    assert 'chat/stream' in js
    html=client.get('/').text
    assert 'Confira as fontes indicadas' not in html


def test_ffmpeg_accepts_webm_opus_recording_format():
    webm = subprocess.run([
        'ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=440:duration=1',
        '-c:a','libopus','-f','webm','pipe:1'],capture_output=True,check=True).stdout
    samples=transcription.decode_audio(webm)
    assert samples.dtype == np.float32
    assert 15000 < samples.size < 17000
