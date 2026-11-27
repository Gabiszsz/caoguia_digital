(() => {
  'use strict';
  if (document.getElementById('cg-rag-toggle')) return;

  const toggle = document.createElement('button');
  toggle.type = 'button';
  toggle.id = 'cg-rag-toggle';
  toggle.textContent = 'Conversar com o assistente';
  toggle.setAttribute('aria-controls', 'cg-rag-dialog');
  toggle.setAttribute('aria-expanded', 'false');

  const dialog = document.createElement('section');
  dialog.id = 'cg-rag-dialog';
  dialog.className = 'cg-rag-dialog';
  dialog.hidden = true;
  dialog.setAttribute('role', 'dialog');
  dialog.setAttribute('aria-modal', 'true');
  dialog.setAttribute('aria-label', 'Chatbot acessível Cão-Guia Digital');
  dialog.innerHTML = `
    <div class="cg-rag-content">
      <div class="cg-rag-toolbar">
        <strong>Assistente Cão-Guia Digital</strong>
        <div class="cg-rag-toolbar-actions">
          <a href="/" target="_blank" rel="noopener noreferrer">Abrir em nova aba</a>
          <button type="button" id="cg-rag-close" aria-label="Fechar o chatbot">Fechar ×</button>
        </div>
      </div>
      <div id="cg-rag-loading" class="cg-rag-loading" role="status" aria-live="polite">Carregando o assistente…</div>
      <iframe id="cg-rag-frame" title="Conversa com o chatbot Cão-Guia Digital" referrerpolicy="same-origin" allow="microphone"></iframe>
    </div>`;
  document.body.append(toggle, dialog);
  const closeButton = dialog.querySelector('#cg-rag-close');
  const frame = dialog.querySelector('#cg-rag-frame');
  const loading = dialog.querySelector('#cg-rag-loading');
  let previousFocus = null;
  let hasLoaded = false;

  function open() {
    previousFocus = document.activeElement;
    dialog.hidden = false;
    toggle.setAttribute('aria-expanded', 'true');
    document.body.classList.add('cg-rag-open');
    closeButton.focus();
    // The original accessible UI remains untouched; it is served at /.
    if (!hasLoaded) { hasLoaded = true; frame.src = '/'; }
  }
  function close() {
    dialog.hidden = true;
    toggle.setAttribute('aria-expanded', 'false');
    document.body.classList.remove('cg-rag-open');
    if (previousFocus && typeof previousFocus.focus === 'function') previousFocus.focus();
    else toggle.focus();
  }
  toggle.addEventListener('click', open);
  closeButton.addEventListener('click', close);
  frame.addEventListener('load', () => { loading.hidden = true; });
  dialog.addEventListener('click', e => { if (e.target === dialog) close(); });
  document.addEventListener('keydown', event => {
    if (dialog.hidden) return;
    if (event.key === 'Escape') { event.preventDefault(); close(); }
    if (event.key === 'Tab' && document.activeElement !== frame) {
      const focusable = Array.from(dialog.querySelectorAll('a[href],button:not([disabled]),iframe'));
      if (!focusable.length) return;
      const first = focusable[0], last = focusable[focusable.length-1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
  });
})();
