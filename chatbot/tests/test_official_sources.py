from pathlib import Path
from config import DOCUMENTS_DIR
from app.schemas import Source


def test_official_documents_exist_and_have_verifiable_links():
    official = list(DOCUMENTS_DIR.glob("IF_Goiano_*.md"))
    assert len(official) >= 4
    for doc in official:
        text = doc.read_text(encoding="utf-8")
        assert "Fonte oficial: https://" in text
        assert "ifgoiano.edu.br" in text


def test_source_can_hold_institutional_url():
    source = Source(document="IF_Goiano_01_Programa.md", score=.6, source_url="https://ifgoiano.edu.br/home/index.php/programa-cao-guia.html")
    assert source.source_url.startswith("https://ifgoiano.edu.br/")
