/* Cão-Guia Digital — componente independente para o portal.
 * API padrão: Spring Boot /api/chatbot. Adapte data-chatbot-api no script de inclusão.
 */
(() => {
  'use strict';
  const script = document.currentScript;
  const api = (script?.dataset.chatbotApi || '/api/chatbot').replace(/\/$/, '');
  const mount = () => {
    if (document.getElementById('cgchat-launcher')) return;
    const root = document.createElement('div');
    root.className = 'cgchat';
    root.innerHTML = `
      <button type="button" class="cgchat-launch" id="cgchat-launcher"
              aria-controls="cgchat-panel" aria-expanded="false" aria-label="Abrir assistente Cão-Guia Digital">
        <span aria-hidden="true">✦</span> Assistente
      </button>
      <section class="cgchat-panel" id="cgchat-panel" role="dialog"
               aria-modal="false" aria-labelledby="cgchat-title" hidden>
        <header class="cgchat-header">
          <div><strong id="cgchat-title">Assistente Cão-Guia Digital</strong>
          <small>Dúvidas sobre o programa e o portal</small></div>
          <button class="cgchat-close" type="button" aria-label="Fechar assistente">×</button>
        </header>
        <div class="cgchat-messages" role="log" aria-label="Mensagens da conversa" aria-live="off"></div>
        <form class="cgchat-form">
          <label for="cgchat-question">Sua pergunta</label>
          <textarea id="cgchat-question" rows="2" maxlength="2200" placeholder="Digite sua pergunta" required></textarea>
          <div class="cgchat-actions">
            <button type="button" class="cgchat-mic" aria-label="Iniciar gravação de voz" aria-pressed="false">🎙 Microfone</button>
            <button type="submit" class="cgchat-send">Enviar</button>
          </div>
          <p class="cgchat-state" role="status" aria-live="polite"></p>
        </form>
      </section>
      <p class="cgchat-sr" aria-live="polite" aria-atomic="true"></p>
    `;
    document.body.appendChild(root);
    const launch = root.querySelector('.cgchat-launch');
    const panel = root.querySelector('.cgchat-panel');
    const close = root.querySelector('.cgchat-close');
    const form = root.querySelector('.cgchat-form');
    const question = root.querySelector('#cgchat-question');
    const messages = root.querySelector('.cgchat-messages');
    const mic = root.querySelector('.cgchat-mic');
    const send = root.querySelector('.cgchat-send');
    const state = root.querySelector('.cgchat-state');
    const announcement = root.querySelector('.cgchat-sr');
    let recorder = null;
    let stream = null;
    let chunks = [];
    let processing = false;
    let busy = false;
    let voice = null;

    function status(text) { state.textContent = text; }
    function openPanel() {
      panel.hidden = false; launch.setAttribute('aria-expanded', 'true');
      question.focus();
    }
    function closePanel() {
      panel.hidden = true; launch.setAttribute('aria-expanded', 'false');
      launch.focus();
    }
    launch.addEventListener('click', () => panel.hidden ? openPanel() : closePanel());
    close.addEventListener('click', closePanel);
    panel.addEventListener('keydown', e => { if (e.key === 'Escape') closePanel(); });
    function message(author, text = '') {
      const item = document.createElement('article');
      item.className = 'cgchat-bubble ' + (author === 'Você' ? 'cgchat-user' : 'cgchat-assistant');
      const label = document.createElement('span'); label.className = 'cgchat-author'; label.textContent = author;
      const body = document.createElement('div'); body.className = 'cgchat-text'; body.textContent = text;
      item.append(label, body);
      if (author === 'Assistente') {
        const speak = document.createElement('button');
        speak.type = 'button'; speak.className = 'cgchat-speak'; speak.textContent = 'Ouvir resposta';
        speak.addEventListener('click', () => {
          if (!('speechSynthesis' in window)) { status('Leitura em voz alta indisponível neste navegador.'); return; }
          window.speechSynthesis.cancel();
          voice = new SpeechSynthesisUtterance(body.textContent);
          voice.lang = 'pt-BR'; window.speechSynthesis.speak(voice);
        });
        item.append(speak);
      }
      messages.append(item); messages.scrollTop = messages.scrollHeight;
      return body;
    }
    message('Assistente', 'Olá! Como posso ajudar com o Programa Cão-Guia do IF Goiano?');

    function setBusy(value) {
      busy = value;
      send.disabled = value;
      question.disabled = value;
    }
    form.addEventListener('submit', async event => {
      event.preventDefault();
      if (busy || processing || recorder?.state === 'recording') return;
      const text = question.value.trim();
      if (text.length < 2) { status('Digite uma pergunta com pelo menos duas letras.'); return; }
      message('Você', text);
      question.value = '';
      setBusy(true);
      const answer = message('Assistente');
      answer.classList.add('cgchat-waiting');
      answer.textContent = '•••';
      answer.setAttribute('aria-label', 'O assistente esta preparando a resposta');
      status('');
      announcement.textContent = 'Assistente preparando a resposta.';
      let fullAnswer = '';
      try {
        const response = await fetch(api + '/stream', {
          method: 'POST', headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({message: text})
        });
        if (!response.ok || !response.body) throw new Error('Serviço indisponível (HTTP ' + response.status + ').');
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let remainder = '';
        let finished = false;
        while (true) {
          const {done, value} = await reader.read();
          if (done) break;
          remainder += decoder.decode(value, {stream: true});
          const lines = remainder.split('\n'); remainder = lines.pop();
          for (const line of lines) {
            if (!line.trim()) continue;
            let evt; try { evt = JSON.parse(line); } catch { continue; }
            if (evt.type === 'delta') {
              fullAnswer += evt.text || evt.delta || '';
              answer.classList.remove('cgchat-waiting');
              answer.removeAttribute('aria-label');
              answer.textContent = fullAnswer.replace(/\*\*/g, '');
              messages.scrollTop = messages.scrollHeight;
            } else if (evt.type === 'error') {
              throw new Error(evt.message || 'Não foi possível concluir a resposta.');
            } else if (evt.type === 'done') {
              finished = true;
              if (evt.answer && !fullAnswer) fullAnswer = evt.answer;
            }
          }
        }
        if (!fullAnswer && !finished) throw new Error('Não foi possível obter uma resposta.');
        answer.classList.remove('cgchat-waiting');
        answer.removeAttribute('aria-label');
        answer.textContent = (fullAnswer || 'Não encontrei essa informação nos documentos disponíveis.').replace(/\*\*/g, '');
        status('Resposta concluída.');
        announcement.textContent = 'Resposta do assistente: ' + answer.textContent;
      } catch (error) {
        answer.classList.remove('cgchat-waiting');
        answer.removeAttribute('aria-label');
        answer.textContent = 'Não foi possível responder agora. Tente novamente.';
        status('Falha de conexão: ' + error.message);
      } finally { setBusy(false); question.focus(); }
    });
    question.addEventListener('keydown', e => {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); }
    });
    function stopAudio() {
      if (recorder?.state === 'recording') recorder.stop();
    }
    mic.addEventListener('click', async () => {
      if (processing) return;
      if (recorder?.state === 'recording') { stopAudio(); return; }
      if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
        status('O navegador não oferece gravação por microfone nesta página.'); return;
      }
      if (!window.isSecureContext) {
        status('O microfone requer acesso por HTTPS ou localhost.'); return;
      }
      try {
        stream = await navigator.mediaDevices.getUserMedia({audio: true});
        const formats = ['audio/webm;codecs=opus','audio/webm','audio/mp4','audio/ogg'];
        const mimeType = formats.find(t => MediaRecorder.isTypeSupported(t));
        recorder = mimeType ? new MediaRecorder(stream, {mimeType}) : new MediaRecorder(stream);
        chunks = [];
        recorder.ondataavailable = e => { if (e.data.size) chunks.push(e.data); };
        recorder.onstop = async () => {
          mic.setAttribute('aria-pressed','false'); mic.textContent = '🎙 Microfone';
          stream?.getTracks().forEach(t => t.stop());
          if (!chunks.length) { status('Gravação vazia. Tente novamente.'); return; }
          processing = true; mic.disabled = true; setBusy(true);
          status('Transcrevendo pergunta.');
          const blob = new Blob(chunks, {type: recorder.mimeType || 'audio/webm'});
          const ext = blob.type.includes('mp4') ? 'm4a' : blob.type.includes('ogg') ? 'ogg' : 'webm';
          const data = new FormData(); data.append('audio', blob, 'gravacao.' + ext);
          try {
            const response = await fetch(api + '/transcrever', {method: 'POST', body: data});
            const payload = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(payload.detail || 'Não foi possível transcrever a gravação.');
            question.value = payload.text || '';
            status(question.value ? 'Pergunta transcrita. Confira o texto antes de enviar.' : 'Não foi possível reconhecer a fala.');
            question.focus();
          } catch(error) { status('Erro de transcrição: ' + error.message); }
          finally { processing = false; mic.disabled = false; setBusy(false); }
        };
        recorder.start(); mic.setAttribute('aria-pressed', 'true'); mic.textContent = '■ Parar gravação';
        status('Gravando. Clique novamente para transcrever.');
      } catch(error) {
        status(error.name === 'NotAllowedError'
          ? 'Permita o acesso ao microfone nas configurações do navegador.'
          : 'Não foi possível acessar o microfone: ' + error.message);
      }
    });
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount);
  else mount();
})();
