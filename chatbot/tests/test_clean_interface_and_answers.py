import json
from pathlib import Path
from app.rag import RAGAssistant
from fastapi.testclient import TestClient
from app.main import app

ROOT = Path(__file__).resolve().parents[1]


def test_loading_has_three_accessible_dots_not_extra_status():
    html = (ROOT / 'web' / 'index.html').read_text('utf-8')
    js = (ROOT / 'web' / 'app.js').read_text('utf-8')
    css = (ROOT / 'web' / 'styles.css').read_text('utf-8')
    assert 'id="thinking"' not in html
    assert 'Consultando documentos' not in html
    assert 'addMessage("Assistente", "", {pending: true})' in js
    assert 'bubble.classList.add("is-loading")' in js
    assert 'for (let i = 0; i < 3; i++)' in js
    assert '.typing-dot:nth-child(3)' in css
    assert 'prefers-reduced-motion' in css
    assert 'event.type === "phase"' not in js


def test_stream_removes_markdown_even_if_asterisks_arrive_in_separate_chunks(monkeypatch):
    class KB:
        def search(self, question):
            return [{'document': 'fonte.md', 'text': 'Famílias socializadoras auxiliam na formação dos cães-guia.',
                     'page': None, 'score': .87, 'source_url': None}]

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def raise_for_status(self): pass
        def iter_lines(self, chunk_size=1):
            for content in ['A ', '*', '*', 'socialização', '*', '*', ' é ', 'importante.']:
                yield json.dumps({'message': {'content': content}}).encode()
            yield json.dumps({'done': True}).encode()

    monkeypatch.setattr('app.rag.requests.post', lambda *a, **k: Response())
    model = RAGAssistant(KB())
    events = list(model.stream_answer('Como ocorre a socialização?'))
    result = ''.join(e['text'] for e in events if e['type'] == 'delta')
    assert result == 'A socialização é importante.'
    assert '**' not in result
    assert events[-1]['type'] == 'done'
    assert model._cached('Como ocorre a socialização?')[0] == result


def test_non_stream_answer_also_removes_bold_markers(monkeypatch):
    class KB:
        def search(self, question):
            return [{'document': 'fonte.md', 'text': 'Informação sobre o programa.',
                     'page': None, 'score': .85, 'source_url': None}]

    class Response:
        def raise_for_status(self): pass
        def json(self): return {'message': {'content': 'O **programa** ajuda.'}}

    monkeypatch.setattr('app.rag.requests.post', lambda *a, **k: Response())
    answer, found, sources = RAGAssistant(KB()).answer('Qual é a finalidade?')
    assert found and sources
    assert answer == 'O programa ajuda.'


def test_api_version_and_ui():
    client = TestClient(app)
    assert client.get('/openapi.json').json()['info']['version'] == '2.6'
    assert '/static/app.js?v=2.6' in client.get('/').text
