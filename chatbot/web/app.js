"use strict";

const $ = id => document.getElementById(id);
const form = $("chatForm");
const question = $("question");
const messages = $("messages");
const sendButton = $("sendButton");
const srMessage = $("screenReaderMessage");
const serviceIndicator = $("serviceIndicator");
const contrastButton = $("contrastButton");
const autoReadButton = $("autoReadButton");
const micButton = $("dictateButton");
let busy = false;
let speaking = false;
let autoRead = false;
let lastAnswer = "";
let mediaRecorder = null;
let audioStream = null;
let audioParts = [];
let voiceBusy = false;
let stopRecordingTimeout = null;
const voiceStatus = $("transcriptionStatus");

function getPref(key, fallback) {
  try { return localStorage.getItem(`cg-access-${key}`) ?? fallback; }
  catch (_) { return fallback; }
}
function setPref(key, value) {
  try { localStorage.setItem(`cg-access-${key}`, String(value)); }
  catch (_) { /* Se o armazenamento estiver bloqueado no iframe, use apenas a sessão. */ }
}
function announce(text) {
  srMessage.textContent = "";
  // Duas atualizações permitem que leitores de tela anunciem mensagens consecutivas.
  requestAnimationFrame(() => { srMessage.textContent = text; });
}
function speak(text) {
  if (!("speechSynthesis" in window)) {
    announce("A leitura por voz não é suportada neste navegador. Utilize seu leitor de tela.");
    return;
  }
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "pt-BR";
  utterance.rate = 0.95;
  utterance.pitch = 1;
  utterance.onstart = () => { speaking = true; };
  utterance.onend = () => { speaking = false; };
  utterance.onerror = () => { speaking = false; };
  window.speechSynthesis.speak(utterance);
}
function stopSpeaking() {
  if ("speechSynthesis" in window) window.speechSynthesis.cancel();
  speaking = false;
}
function make(tag, cls, text) {
  const el = document.createElement(tag);
  if (cls) el.className = cls;
  if (text !== undefined) el.textContent = text;
  return el;
}
function addReplyActions(container, bubble) {
  if (container.querySelector(".reply-actions")) return;
  const actions = make("div", "reply-actions");
  const readBtn = make("button", "reply-button", "Ouvir resposta");
  readBtn.type = "button";
  readBtn.setAttribute("aria-label", "Ouvir esta resposta por voz");
  readBtn.addEventListener("click", () => speak(bubble.textContent));
  const stopBtn = make("button", "reply-button", "Parar leitura");
  stopBtn.type = "button";
  stopBtn.addEventListener("click", stopSpeaking);
  actions.append(readBtn, stopBtn);
  container.append(actions);
}
function showTyping(bubble) {
  bubble.replaceChildren();
  bubble.classList.add("is-loading");
  bubble.setAttribute("role", "status");
  bubble.setAttribute("aria-label", "O assistente está preparando a resposta");
  const dots = make("span", "typing-dots");
  dots.setAttribute("aria-hidden", "true");
  for (let i = 0; i < 3; i++) dots.append(make("span", "typing-dot"));
  bubble.append(dots);
}
function endTyping(bubble) {
  bubble.classList.remove("is-loading");
  bubble.removeAttribute("role");
  bubble.removeAttribute("aria-label");
}
// O texto vem em fragmentos. Remover os marcadores também no frontend impede
// que ** apareça durante a geração se os caracteres chegarem separados.
function displayPlainText(value) {
  return value.replace(/\*/g, "").replace(/^\s{0,3}#{1,6}\s*/gm, "");
}
function addMessage(author, text, options = {}) {
  const isUser = author === "Você";
  const article = make("article", "message" + (isUser ? " is-user" : ""));
  article.setAttribute("aria-label", isUser ? "Mensagem enviada por você" : "Resposta do assistente");
  const avatar = make("div", "avatar", isUser ? "EU" : "CG");
  avatar.setAttribute("aria-hidden", "true");
  const container = make("div", "message-body");
  const who = make("p", "message-author", author);
  const bubble = make("div", "bubble", text);
  if (options.pending) showTyping(bubble);
  container.append(who, bubble);
  // Nenhuma etiqueta de fonte ou botão extra durante o carregamento.
  if (!isUser && !options.welcome && !options.pending) addReplyActions(container, bubble);
  article.append(avatar, container);
  messages.append(article);
  messages.scrollTop = messages.scrollHeight;
  return article;
}
function startConversation() {
  messages.replaceChildren();
  addMessage("Assistente", "Olá! Sou o assistente virtual do projeto Cão-Guia Digital. Posso consultar documentos oficiais sobre o Programa Cão-Guia do IF Goiano e a especificação do portal. Qual é sua dúvida?", {welcome: true});
}
async function serviceStatus() {
  try {
    const [health, model] = await Promise.all([
      fetch("/api/v1/health", { cache: "no-store" }),
      fetch("/api/v1/model/status", { cache: "no-store" })
    ]);
    if (!health.ok || !model.ok) throw new Error("Serviço indisponível");
    const h = await health.json();
    const m = await model.json();
    const ready = Boolean(h.knowledge_base_available && m.online && m.installed);
    serviceIndicator.textContent = ready ? "Assistente disponível" : "Configuração pendente";
    serviceIndicator.className = "service-state " + (ready ? "ready" : "error");
    serviceIndicator.title = ready ? "Documentos indexados e modelo Ollama disponível" : "Verifique as células de instalação, download do modelo e indexação no Colab";
  } catch (_) {
    serviceIndicator.textContent = "Serviço indisponível";
    serviceIndicator.className = "service-state error";
  }
}
function setBusy(value) {
  busy = value;
  sendButton.disabled = value;
  question.readOnly = value;
  question.setAttribute("aria-busy", String(value));
  micButton.disabled = value || voiceBusy;
}
// Recebe eventos NDJSON, inclusive quando a rede divide um evento entre dois pacotes.
// Recebe eventos NDJSON e mostra a resposta a partir do primeiro fragmento.
async function readStream(response, bubble) {
  if (!response.body?.getReader) {
    throw new Error("Este navegador não suporta a exibição progressiva.");
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let pending = "";
  let rawAnswer = "";
  let finished = false;
  function consume(line) {
    if (!line.trim()) return;
    const event = JSON.parse(line);
    if (event.type === "error") throw new Error(event.message || "Falha ao gerar resposta.");
    if (event.type === "delta") {
      rawAnswer += event.text || "";
      endTyping(bubble);
      bubble.textContent = displayPlainText(rawAnswer);
      messages.scrollTop = messages.scrollHeight;
    }
    // Eventos internos 'start' ou 'phase' não são mostrados ao visitante.
    if (event.type === "done") finished = true;
  }
  try {
    while (true) {
      const {value, done} = await reader.read();
      if (done) break;
      pending += decoder.decode(value, {stream: true});
      let position;
      while ((position = pending.indexOf("\n")) >= 0) {
        const line = pending.slice(0, position);
        pending = pending.slice(position + 1);
        consume(line);
      }
    }
    pending += decoder.decode();
    if (pending.trim()) consume(pending);
  } finally {
    reader.releaseLock();
  }
  if (!finished) throw new Error("A conexão terminou antes de concluir a resposta.");
  return displayPlainText(rawAnswer);
}
async function submitQuestion() {
  if (busy) return;
  const content = question.value.trim();
  if (content.length < 2) {
    announce("Escreva uma pergunta com pelo menos dois caracteres.");
    question.focus();
    return;
  }
  if (content.length > 2200) {
    announce("A pergunta deve ter no máximo dois mil e duzentos caracteres.");
    question.focus();
    return;
  }
  stopSpeaking();
  addMessage("Você", content);
  question.value = "";
  setBusy(true);
  announce("Pergunta enviada. Aguarde o início da resposta.");
  const reply = addMessage("Assistente", "", {pending: true});
  const bubble = reply.querySelector(".bubble");
  try {
    const response = await fetch("/api/v1/chat/stream", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({message: content})
    });
    if (!response.ok) {
      let details = "Falha ao conectar ao assistente.";
      try { details = (await response.json()).detail || details; } catch (_) { /* Sem JSON */ }
      throw new Error(details);
    }
    const answer = (await readStream(response, bubble)).trim();
    if (!answer) throw new Error("A resposta veio vazia. Tente novamente.");
    lastAnswer = answer;
    endTyping(bubble);
    bubble.textContent = answer;
    addReplyActions(reply.querySelector(".message-body"), bubble);
    announce("Resposta do assistente: " + answer);
    if (autoRead) speak(answer);
  } catch (error) {
    const explanation = error instanceof Error ? error.message : "Falha inesperada.";
    // Se recebeu parte da resposta, preserva o texto e avisa sobre a interrupção.
    const parcial = bubble.classList.contains("is-loading") ? "" : bubble.textContent;
    endTyping(bubble);
    bubble.textContent = (parcial ? parcial + "\n\n" : "") + "Não foi possível concluir a resposta: " + explanation;
    addReplyActions(reply.querySelector(".message-body"), bubble);
    announce("Resposta interrompida: " + explanation);
  } finally {
    setBusy(false);
  }
}
form.addEventListener("submit", event => {
  event.preventDefault();
  submitQuestion();
});
question.addEventListener("keydown", event => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    submitQuestion();
  }
});
document.addEventListener("keydown", event => {
  if (event.altKey && !event.ctrlKey && !event.metaKey && event.key.toLowerCase() === "q") {
    event.preventDefault();
    question.focus();
  }
  if (event.key === "Escape") stopSpeaking();
});
document.querySelectorAll("[data-question]").forEach(button => {
  button.addEventListener("click", () => {
    question.value = button.dataset.question;
    question.focus();
    announce("Pergunta sugerida inserida. Pressione Enter para enviar.");
  });
});
$("clearButton").addEventListener("click", () => {
  if (busy) return;
  stopSpeaking();
  lastAnswer = "";
  startConversation();
  announce("Conversa limpa.");
  question.focus();
});
function updateContrast(enabled, quiet = false) {
  document.documentElement.dataset.contrast = enabled ? "high" : "normal";
  contrastButton.setAttribute("aria-pressed", String(enabled));
  contrastButton.setAttribute("aria-label", enabled ? "Desativar alto contraste" : "Ativar alto contraste");
  setPref("contrast", enabled ? "high" : "normal");
  if (!quiet) announce(enabled ? "Alto contraste ativado." : "Alto contraste desativado.");
}
contrastButton.addEventListener("click", () => updateContrast(document.documentElement.dataset.contrast !== "high"));
autoReadButton.addEventListener("click", () => {
  autoRead = !autoRead;
  autoReadButton.setAttribute("aria-pressed", String(autoRead));
  autoReadButton.setAttribute("aria-label", autoRead ? "Desativar leitura automática das respostas" : "Ativar leitura automática das respostas");
  if (!autoRead) stopSpeaking();
  announce(autoRead ? "Leitura automática ativada." : "Leitura automática desativada.");
});

// Captura de voz com MediaRecorder e transcrição Whisper no Python.
// Funciona sem depender da implementação SpeechRecognition do navegador.
function voiceMessage(text, isError = false) {
  voiceStatus.hidden = false;
  voiceStatus.textContent = text;
  voiceStatus.dataset.error = isError ? "true" : "false";
  announce(text);
}
function voiceControls(isBusy) {
  voiceBusy = isBusy;
  micButton.disabled = isBusy || busy;
}
function recordingState(active) {
  micButton.setAttribute("aria-pressed", String(active));
  micButton.setAttribute("aria-label", active ? "Parar gravação e converter fala em texto" : "Começar gravação de voz");
  micButton.title = active ? "Clique para parar a gravação" : "Clique para gravar a pergunta";
}
function releaseAudio() {
  if (stopRecordingTimeout) clearTimeout(stopRecordingTimeout);
  stopRecordingTimeout = null;
  audioStream?.getTracks().forEach(track => track.stop());
  audioStream = null;
}
function audioFileName(type) {
  if (type.includes("mp4")) return "pergunta.m4a";
  if (type.includes("ogg")) return "pergunta.ogg";
  if (type.includes("wav")) return "pergunta.wav";
  return "pergunta.webm";
}
async function uploadRecording(blob, fileName) {
  if (blob.size < 100) {
    voiceMessage("Não foi possível gravar o áudio. Tente novamente.", true);
    return;
  }
  if (blob.size > 15 * 1024 * 1024) {
    voiceMessage("Áudio muito grande. Grave uma pergunta de até 75 segundos.", true);
    return;
  }
  voiceMessage("Convertendo sua fala em texto. A primeira transcrição pode demorar um pouco.");
  voiceControls(true);
  try {
    const formData = new FormData();
    formData.append("audio", blob, fileName);
    const response = await fetch("/api/v1/transcribe", { method: "POST", body: formData });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Não foi possível transcrever o áudio. Confira a verificação do microfone na etapa 7 do Colab.");
    if (!result.text?.trim()) throw new Error("Não identifiquei palavras na gravação.");
    question.value = [question.value.trim(), result.text.trim()].filter(Boolean).join(" ").slice(0, 1200);
    voiceMessage("Pergunta transcrita. Confira o texto e clique em Enviar.");
    question.focus();
  } catch (error) {
    voiceMessage(error instanceof Error ? error.message : "Erro no ditado. Tente novamente.", true);
  } finally {
    voiceControls(false);
  }
}
function microphoneError(error) {
  const name = error?.name || "";
  if (name === "NotAllowedError" || name === "PermissionDeniedError" || name === "SecurityError") {
    return "O acesso ao microfone foi bloqueado. No Colab, abra o chatbot em outra aba pelo link da etapa 8. No navegador, permita o microfone para essa página e recarregue.";
  }
  if (name === "NotFoundError" || name === "DevicesNotFoundError") {
    return "Não foi encontrado um microfone. Conecte um microfone ao dispositivo e tente novamente.";
  }
  if (name === "NotReadableError") {
    return "O microfone está sendo utilizado por outro programa. Feche o programa e tente novamente.";
  }
  return "Não consegui iniciar o microfone. Confira as permissões do navegador e se abriu a página em uma aba HTTPS separada.";
}
function supportedAudioType() {
  const types = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus", "audio/ogg"];
  return types.find(type => MediaRecorder.isTypeSupported(type)) || "";
}
async function startRecording() {
  if (busy || voiceBusy) return;
  const permissions = document.permissionsPolicy || document.featurePolicy;
  if (permissions && typeof permissions.allowsFeature === 'function' && !permissions.allowsFeature('microphone')) {
    voiceMessage('A janela incorporada bloqueou o microfone. Na etapa 8 do Colab, clique em Abrir chatbot em outra aba.', true);
    return;
  }
  if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
    voiceMessage("O navegador não permite gravação nesta janela. Abra o chatbot em outra aba HTTPS, autorize o microfone e tente novamente.", true);
    return;
  }
  try {
    voiceMessage("Solicitando permissão para usar o microfone…");
    stopSpeaking();
    voiceControls(true);
    audioStream = await navigator.mediaDevices.getUserMedia({audio: {
      echoCancellation: true, noiseSuppression: true, autoGainControl: true
    }});
    const type = supportedAudioType();
    mediaRecorder = new MediaRecorder(audioStream, type ? {mimeType: type} : {});
    audioParts = [];
    mediaRecorder.ondataavailable = event => { if (event.data.size) audioParts.push(event.data); };
    mediaRecorder.onerror = () => {
      releaseAudio();
      recordingState(false);
      voiceControls(false);
      voiceMessage("Ocorreu um erro ao gravar. Tente novamente.", true);
    };
    mediaRecorder.onstop = async () => {
      const mime = mediaRecorder.mimeType || type || "audio/webm";
      const blob = new Blob(audioParts, {type: mime});
      recordingState(false);
      releaseAudio();
      await uploadRecording(blob, audioFileName(mime));
    };
    mediaRecorder.start(500);
    voiceControls(false);
    recordingState(true);
    voiceMessage("Gravando. Fale sua pergunta e clique no microfone novamente para terminar.");
    stopRecordingTimeout = setTimeout(() => {
      if (mediaRecorder?.state === "recording") mediaRecorder.stop();
    }, 75000);
  } catch (error) {
    releaseAudio();
    recordingState(false);
    voiceControls(false);
    voiceMessage(microphoneError(error), true);
  }
}
micButton.addEventListener("click", () => {
  if (mediaRecorder?.state === "recording") {
    voiceMessage("Gravação encerrada. Preparando transcrição…");
    mediaRecorder.stop();
    return;
  }
  startRecording();
});
const savedContrast = getPref("contrast", "normal") === "high";
updateContrast(savedContrast, true);
startConversation();
serviceStatus();
