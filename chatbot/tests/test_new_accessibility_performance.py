import json
from pathlib import Path
from unittest.mock import Mock

from app.rag import RAGAssistant
from config import MAX_MESSAGE_CHARS


def test_question_limit_allows_longer_spoken_questions():
    assert MAX_MESSAGE_CHARS == 2200


def test_stream_clean_text_and_cache_avoid_duplicate_ollama_call(monkeypatch):
    class KB:
        def search(self, question):
            return [{'document': 'institucional.md', 'page': None, 'score': .81, 'source_url': None,
                     'text': 'O Programa possui famílias socializadoras.'}]
    class Response:
        def raise_for_status(self): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def iter_lines(self, chunk_size=1):
            yield json.dumps({'message':{'content':'As famílias '}}).encode()
            yield json.dumps({'message':{'content':'socializadoras ajudam.'}}).encode()
            yield json.dumps({'done':True}).encode()
    posted = []
    def fake_post(*args, **kw):
        posted.append(kw['json'])
        return Response()
    monkeypatch.setattr('app.rag.requests.post', fake_post)
    a=RAGAssistant(KB())
    q='Qual é a função das famílias socializadoras?'
    first=list(a.stream_answer(q))
    assert first[0]['type']=='delta'
    assert first[-1]['type']=='done'
    second=list(a.stream_answer(q))
    assert len(posted)==1
    assert second[0]['type']=='delta'
    assert second[0]['text']=='As famílias socializadoras ajudam.'
    assert second[-1]['sources_found'] is True


def test_voice_accessibility_without_hover_narration_or_extra_zoom():
    src=Path(__file__).parents[1]
    js=(src/'web/app.js').read_text(encoding='utf8')
    html=(src/'web/index.html').read_text(encoding='utf8')
    py=(src/'app/transcription.py').read_text(encoding='utf8')
    assert 'id="hoverReadButton"' not in html
    assert 'id="fontUp"' not in html and 'id="fontDown"' not in html
    assert 'scheduleHoverSpeech' not in js
    assert 'id="inputHint"' not in html
    assert 'id="keyboardHint"' in html
    assert 'id="dictateButton"' in html
    assert 'id="contrastButton"' in html
    assert 'id="autoReadButton"' in html
    assert 'autoGainControl: true' in js
    assert 'initial_prompt' in py
    assert 'WHISPER_CPU_MODEL' in py
    assert 'Enviar áudio' not in html
