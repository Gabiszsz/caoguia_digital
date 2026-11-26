from fastapi.testclient import TestClient
from app import main
from app.rag import RAGAssistant, FALLBACK
from ingest import chunks

client = TestClient(main.app)

def test_home_has_accessibility_controls():
    result = client.get("/")
    assert result.status_code == 200
    assert 'lang="pt-BR"' in result.text
    for token in ["screenReaderMessage", "aria-live", "question", "contrastButton", "autoReadButton", "messages"]:
        assert token in result.text

def test_static_assets():
    assert client.get("/static/styles.css").status_code == 200
    assert client.get("/static/app.js").status_code == 200

def test_health_returns_status_even_without_index():
    result = client.get("/api/v1/health")
    assert result.status_code == 200
    assert "knowledge_base_available" in result.json()

def test_request_validation():
    assert client.post("/api/v1/chat", json={"message": ""}).status_code == 422
    assert client.post("/api/v1/chat", json={"message": "x"}).status_code == 422

def test_chat_response(monkeypatch):
    class FakeAssistant:
        def answer(self, prompt):
            assert prompt == "Qual é o objetivo do portal?"
            return "O portal foi projetado para divulgar o programa.", True, [
                {"document": "Fonte.pdf", "page": 4, "score": 0.67}
            ]
    monkeypatch.setattr(main, "get_assistant", lambda: FakeAssistant())
    result = client.post("/api/v1/chat", json={"message": "Qual é o objetivo do portal?"})
    assert result.status_code == 200
    assert result.json()["sources_found"] is True
    assert result.json()["sources"][0]["page"] == 4

def test_no_documents_causes_fallback():
    class FakeKB:
        def search(self, question):
            return []
    result = RAGAssistant(FakeKB()).answer("Qual o prazo?")
    assert result[0] == FALLBACK
    assert result[1:] == (False, [])

def test_chunker_finishes_and_preserves_content():
    pieces = list(chunks("palavra " * 600, size=200, overlap=30))
    assert len(pieces) > 1
    assert all(1 <= len(part) <= 200 for part in pieces)
