"""Aplicação standalone servindo UI acessível e API na mesma origem."""
import json
import logging
import os
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path
from time import perf_counter
import requests
from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from starlette.concurrency import run_in_threadpool
from fastapi.staticfiles import StaticFiles
from config import INDEX_DIR, OLLAMA_BASE_URL, OLLAMA_MODEL, ROOT
from app.knowledge_base import KnowledgeBase, KnowledgeBaseError
from app.rag import RAGAssistant
from app.schemas import ChatRequest, ChatResponse, HealthResponse
from app.transcription import MAX_AUDIO_BYTES, transcribe_audio, TranscriptionError, transcription_status, get_cpu_model

def preload_knowledge_base():
    """Carrega o índice e o encoder antes da primeira pergunta."""
    from app.knowledge_base import get_encoder
    assistant = get_assistant()
    assistant.kb.load()
    get_encoder().encode(["Programa Cão-Guia do IF Goiano"], normalize_embeddings=True)


@asynccontextmanager
async def lifespan(_app):
    if os.getenv("PRELOAD_KB", "0") == "1":
        try:
            await run_in_threadpool(preload_knowledge_base)
            logging.getLogger(__name__).info("Base RAG e modelo de embeddings preparados.")
        except Exception:
            logging.getLogger(__name__).exception("Não foi possível preparar a base RAG.")
    if os.getenv("PRELOAD_WHISPER", "0") == "1":
        try:
            await run_in_threadpool(get_cpu_model)
            logging.getLogger(__name__).info("Whisper CPU carregado antes do primeiro ditado.")
        except Exception:
            logging.getLogger(__name__).exception("Falha ao pré-carregar Whisper. Confira o diagnóstico na etapa 7.")
    yield


app = FastAPI(title="Cão-Guia Digital — Assistente Acessível", version="2.6", lifespan=lifespan)

# Integração com a página local do portal; sem acesso aberto de qualquer origem.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500", "http://localhost:5500",
        "http://127.0.0.1:5501", "http://localhost:5501",
        "http://127.0.0.1:8080", "http://localhost:8080",
    ],
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)

app.mount("/static", StaticFiles(directory=str(ROOT / "web")), name="static")
from app.portal_integration import attach_portal
attach_portal(app)

@lru_cache(maxsize=1)
def get_assistant():
    return RAGAssistant(KnowledgeBase())

@app.get("/", include_in_schema=False)
def home():
    return FileResponse(ROOT / "web" / "index.html", media_type="text/html")

@app.get("/api/v1/health", response_model=HealthResponse)
def health():
    ready = all((INDEX_DIR / f).exists() for f in ["faiss.index", "chunks.json", "metadata.json"])
    return HealthResponse(status="ok" if ready else "degraded", knowledge_base_available=ready, llm_name=OLLAMA_MODEL)

@app.get("/api/v1/model/status")
def model_status():
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        r.raise_for_status()
        models = [item.get("name", "") for item in r.json().get("models", [])]
        return {"online": True, "model": OLLAMA_MODEL, "installed": OLLAMA_MODEL in models, "available": models}
    except requests.RequestException:
        return {"online": False, "model": OLLAMA_MODEL, "installed": False, "available": []}

@app.post("/api/v1/chat", response_model=ChatResponse)
def chat(data: ChatRequest):
    question = data.message.strip()
    if len(question) < 2:
        raise HTTPException(status_code=422, detail="Digite uma pergunta com pelo menos 2 caracteres.")
    start = perf_counter()
    try:
        answer, found, sources = get_assistant().answer(question)
        return ChatResponse(
            answer=answer,
            sources_found=found,
            sources=sources,
            response_time_ms=round((perf_counter() - start) * 1000),
        )
    except KnowledgeBaseError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except requests.Timeout as exc:
        raise HTTPException(status_code=504, detail="O modelo demorou para responder. Tente novamente.") from exc
    except requests.RequestException as exc:
        raise HTTPException(status_code=503, detail="O Ollama não respondeu. Confira a célula que inicia o modelo no Colab.") from exc
    except Exception as exc:
        # A stacktrace é gravada apenas no log da aplicação; não expor detalhes ao visitante.
        import logging
        logging.getLogger(__name__).exception("Falha ao responder pergunta")
        raise HTTPException(status_code=500, detail="Não foi possível processar a pergunta agora.") from exc

@app.post("/api/v1/chat/stream")
def chat_stream(data: ChatRequest):
    """Resposta progressiva em NDJSON. Fontes ficam na API, não na interface."""
    question = data.message.strip()
    if len(question) < 2:
        raise HTTPException(status_code=422, detail="Digite uma pergunta com pelo menos 2 caracteres.")

    def events():
        started = perf_counter()
        yield json.dumps({"type": "start"}, ensure_ascii=False) + "\n"
        try:
            for event in get_assistant().stream_answer(question):
                if event.get("type") == "done":
                    event["response_time_ms"] = round((perf_counter() - started) * 1000)
                yield json.dumps(event, ensure_ascii=False) + "\n"
        except (requests.Timeout, requests.RequestException) as exc:
            logging.getLogger(__name__).warning("Ollama indisponível no stream: %s", exc)
            yield json.dumps({"type": "error", "message":
                "A resposta demorou mais que o esperado. Confira se o Ollama está usando a GPU e tente novamente."}, ensure_ascii=False) + "\n"
        except KnowledgeBaseError as exc:
            yield json.dumps({"type": "error", "message": str(exc)}, ensure_ascii=False) + "\n"
        except Exception:
            logging.getLogger(__name__).exception("Falha ao gerar resposta progressiva")
            yield json.dumps({"type": "error", "message":
                "Não foi possível concluir a resposta agora. Tente novamente."}, ensure_ascii=False) + "\n"

    return StreamingResponse(events(), media_type="application/x-ndjson",
                             headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"})


@app.get("/api/v1/transcribe/status")
def get_transcription_status():
    return transcription_status()


@app.post("/api/v1/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    """Recebe um áudio curto, converte fala para texto e apaga o arquivo temporário."""
    mime = (audio.content_type or "").split(";")[0].lower().strip()
    supported = {"audio/webm", "video/webm", "audio/mp4", "audio/x-m4a", "audio/m4a", "audio/ogg", "audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp3", "application/octet-stream"}
    if mime not in supported:
        raise HTTPException(status_code=415, detail="Formato de áudio não suportado. Utilize WebM, M4A, MP3, OGG ou WAV.")
    try:
        content = await audio.read(MAX_AUDIO_BYTES + 1)
        if len(content) > MAX_AUDIO_BYTES:
            raise HTTPException(status_code=413, detail="Áudio muito grande. Grave uma pergunta de até 75 segundos.")
        if len(content) < 100:
            raise HTTPException(status_code=422, detail="A gravação está vazia. Tente novamente.")
        mime_ext = {"audio/webm":".webm", "video/webm":".webm", "audio/mp4":".m4a", "audio/x-m4a":".m4a", "audio/m4a":".m4a", "audio/ogg":".ogg", "audio/wav":".wav", "audio/x-wav":".wav", "audio/mpeg":".mp3", "audio/mp3":".mp3"}
        extension = mime_ext.get(mime, ".webm")
        text = await run_in_threadpool(transcribe_audio, content, extension)
        if not text:
            raise HTTPException(status_code=422, detail="Não consegui reconhecer a fala. Tente outra gravação, de preferência em um ambiente silencioso.")
        return {"text": text, "language": "pt-BR"}
    except TranscriptionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    finally:
        await audio.close()
