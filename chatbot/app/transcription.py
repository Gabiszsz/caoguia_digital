"""Transcrição local de voz em português, com decodificação FFmpeg e recuperação de falhas.

Os dados de áudio não são enviados a serviços externos de transcrição.
O navegador envia a gravação à API FastAPI do próprio chatbot.
"""
import logging
import os
import subprocess
from functools import lru_cache

import numpy as np

MAX_AUDIO_BYTES = 15 * 1024 * 1024
MAX_AUDIO_SECONDS = 75
log = logging.getLogger(__name__)


class TranscriptionError(Exception):
    """Erro seguro para exibição ao visitante; diagnóstico detalhado fica no log."""


@lru_cache(maxsize=1)
def get_cpu_model():
    """Modelo estável na CPU para evitar dependências CUDA do Colab."""
    from faster_whisper import WhisperModel
    name = os.getenv("WHISPER_CPU_MODEL", "base")
    log.info("Carregando Whisper %s em CPU/int8", name)
    return WhisperModel(name, device="cpu", compute_type="int8",
                        cpu_threads=min(4, os.cpu_count() or 2))


@lru_cache(maxsize=1)
def get_whisper_model():
    """CPU por padrão. GPU é opt-in e pode cair para CPU ao falhar na inferência."""
    preferred = os.getenv("WHISPER_DEVICE", "cpu").strip().lower()
    if preferred in ("cuda", "auto"):
        try:
            from faster_whisper import WhisperModel
            name = os.getenv("WHISPER_MODEL", "small")
            log.info("Tentando Whisper %s em CUDA", name)
            return WhisperModel(name, device="cuda", compute_type="float16")
        except Exception:
            log.exception("Não foi possível carregar Whisper na GPU; usando CPU")
    return get_cpu_model()


def decode_audio(data: bytes) -> np.ndarray:
    """Converte WebM/Opus, M4A, OGG ou WAV em float32 mono 16 kHz."""
    command = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
               "-i", "pipe:0", "-t", str(MAX_AUDIO_SECONDS),
               "-ar", "16000", "-ac", "1", "-f", "f32le", "pipe:1"]
    try:
        result = subprocess.run(command, input=data, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=35, check=False)
    except FileNotFoundError as exc:
        log.exception("FFmpeg não encontrado")
        raise TranscriptionError("O componente de áudio não foi instalado corretamente. Execute a etapa 3 do Colab.") from exc
    except subprocess.TimeoutExpired as exc:
        log.exception("FFmpeg excedeu o tempo limite")
        raise TranscriptionError("A conversão da gravação demorou demais. Tente uma pergunta mais curta.") from exc
    if result.returncode != 0 or len(result.stdout) < 6400:
        stderr = result.stderr.decode("utf-8", errors="replace")[-2000:]
        log.error("FFmpeg não conseguiu decodificar áudio: rc=%s, bytes=%s, erro=%s",
                  result.returncode, len(data), stderr)
        raise TranscriptionError("A gravação não pôde ser lida. Atualize a página e tente novamente.")
    return np.frombuffer(result.stdout, dtype="<f4")


def _recognize(model, samples: np.ndarray, beam_size: int = 3) -> str:
    """Itera os segmentos dentro do try: falhas CUDA podem surgir só nesse momento."""
    segments, _ = model.transcribe(
        samples,
        language="pt",
        task="transcribe",
        beam_size=beam_size,
        best_of=2,
        temperature=0.0,
        # O filtro VAD usa ONNX Runtime; para perguntas curtas pode introduzir falhas
        # em algumas instalações Colab. Mantemos desativado aqui.
        vad_filter=False,
        condition_on_previous_text=False,
        initial_prompt=("Pergunta em português brasileiro sobre o Programa Cão-Guia "
                        "do IF Goiano, Campus Urutaí, famílias socializadoras, "
                        "treinamento, inscrições e acessibilidade."),
    )
    return " ".join(segment.text.strip() for segment in segments).strip()[:2200]


def transcribe_audio(data: bytes, suffix: str) -> str:
    """Transcreve uma gravação e tenta CPU quando a GPU falha durante a inferência."""
    del suffix  # FFmpeg detecta o formato real pelo cabeçalho do arquivo.
    samples = decode_audio(data)
    if not np.all(np.isfinite(samples)):
        log.warning("Gravação com dados PCM inválidos")
        raise TranscriptionError("O áudio recebido estava corrompido. Tente gravar novamente.")
    if float(np.max(np.abs(samples))) < 0.0001:
        return ""  # Nenhuma fala foi detectada no microfone.

    try:
        model = get_whisper_model()
        return _recognize(model, samples)
    except Exception as exc:
        # GPU pode passar na criação do modelo e falhar apenas no primeiro
        # transcribe() ou durante a iteração do generator; recuperar automaticamente.
        log.exception("Primeira tentativa de transcrição falhou; tentando CPU")
        try:
            cpu_model = get_cpu_model()
            return _recognize(cpu_model, samples, beam_size=2)
        except Exception as cpu_exc:
            log.exception("Transcrição CPU também falhou; consultar traceback")
            raise TranscriptionError(
                "O reconhecimento de voz não conseguiu processar a gravação. "
                "Verifique o diagnóstico da etapa 7 no Colab."
            ) from cpu_exc


def transcription_status() -> dict:
    """Resumo do ambiente sem expor o conteúdo de áudios ou detalhes privados."""
    from shutil import which
    return {
        "ffmpeg_available": bool(which("ffmpeg")),
        "whisper_device": os.getenv("WHISPER_DEVICE", "cpu"),
        "cpu_model": os.getenv("WHISPER_CPU_MODEL", "base"),
        "model_loaded": (get_whisper_model.cache_info().currsize > 0 or
                         get_cpu_model.cache_info().currsize > 0),
    }
