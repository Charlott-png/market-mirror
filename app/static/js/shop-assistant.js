// MM-027 progressively enhances a server-rendered, read-only shopping helper.
(() => {
  const launcher = document.querySelector('#shop-assistant-launcher');
  const panel = document.querySelector('#shop-assistant-panel');
  const close = document.querySelector('#shop-assistant-close');
  const form = document.querySelector('#shop-assistant-form');
  const query = document.querySelector('#shop-assistant-query');
  const send = document.querySelector('#shop-assistant-send');
  const clear = document.querySelector('#shop-assistant-clear');
  const transcript = document.querySelector('#shop-assistant-transcript');
  const status = document.querySelector('#shop-assistant-status');
  const csrf = document.querySelector('#shop-assistant-csrf');
  if (!launcher) {
    console.error('Shop Assistant markup is incomplete: launcher is missing.');
    return;
  }

  // Keep older cached templates working: reveal the launcher before checking
  // the remaining enhancement-only elements.
  launcher.hidden = false;
  if (!panel || !close || !transcript || !status) {
    console.error('Shop Assistant markup is incomplete.', {
      panel: Boolean(panel), close: Boolean(close),
      transcript: Boolean(transcript), status: Boolean(status),
    });
    return;
  }

  const greeting = transcript.firstElementChild?.cloneNode(true) || null;
  let history = [];
  let activeController = null;
  let requestSequence = 0;

  const openPanel = () => {
    panel.hidden = false;
    launcher.setAttribute('aria-expanded', 'true');
    if (query) query.focus({preventScroll: true});
    else close.focus({preventScroll: true});
  };
  const closePanel = () => {
    panel.hidden = true;
    launcher.setAttribute('aria-expanded', 'false');
    launcher.focus({preventScroll: true});
  };
  launcher.addEventListener('click', openPanel);
  close.addEventListener('click', closePanel);
  panel.addEventListener('keydown', event => {
    if (event.key === 'Escape') {
      event.preventDefault();
      closePanel();
    }
  });

  const appendMessage = (role, content) => {
    const item = document.createElement('li');
    item.className = `shop-assistant-message shop-assistant-message-${role}`;
    item.textContent = content;
    transcript.append(item);
    transcript.scrollTop = transcript.scrollHeight;
    return item;
  };
  const appendRecommendation = item => {
    const card = document.createElement('article');
    card.className = 'shop-assistant-product';
    if (item.image_url && item.image_url.startsWith('/media/products/')) {
      const image = document.createElement('img');
      image.src = item.image_url;
      image.alt = '';
      image.loading = 'lazy';
      card.append(image);
    }
    const title = document.createElement('h3');
    const link = document.createElement('a');
    if (typeof item.url === 'string' && item.url.startsWith('/products/')) link.href = item.url;
    link.textContent = item.title;
    title.append(link);
    const facts = document.createElement('p');
    facts.textContent = `$${item.price} ${item.currency} · ${item.condition}`;
    const reason = document.createElement('p');
    reason.textContent = item.reason;
    card.append(title, facts, reason);
    transcript.append(card);
  };

  const setBusy = busy => {
    if (!form || !send) return;
    form.setAttribute('aria-busy', String(busy));
    send.disabled = busy;
  };
  const cancelPending = () => {
    requestSequence += 1;
    if (activeController) activeController.abort();
    activeController = null;
    setBusy(false);
  };

  clear?.addEventListener('click', () => {
    cancelPending();
    history = [];
    transcript.replaceChildren();
    if (greeting) transcript.append(greeting.cloneNode(true));
    status.textContent = 'Chat cleared.';
    query.value = '';
    query.focus({preventScroll: true});
  });

  form?.addEventListener('submit', async event => {
    event.preventDefault();
    if (activeController) return;
    const question = query.value.trim();
    if (!question || question.length > 300 || /[\u0000-\u001f\u007f-\u009f]/u.test(question)) {
      status.textContent = 'Enter a question of up to 300 characters.';
      query.focus();
      return;
    }

    appendMessage('user', question);
    query.value = '';
    status.textContent = 'Looking through active products…';
    setBusy(true);
    const controller = new AbortController();
    activeController = controller;
    const sequence = ++requestSequence;
    try {
      const response = await fetch('/ai/shop-assistant', {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          'X-CSRFToken': csrf?.value || '',
        },
        body: JSON.stringify({query: question, history}),
        signal: controller.signal,
      });
      const result = await response.json().catch(() => ({}));
      if (sequence !== requestSequence) return;
      if (!response.ok) throw new Error(result.message || 'Assistant unavailable');
      appendMessage('assistant', result.summary);
      (result.recommendations || []).forEach(appendRecommendation);
      if (result.follow_up) appendMessage('assistant', result.follow_up);
      if (result.truncated) {
        appendMessage('assistant', 'I searched a limited candidate set. Explore shows the full catalogue.');
      }
      history.push({role: 'user', content: question},
                   {role: 'assistant', content: result.summary});
      history = history.slice(-6);
      status.textContent = 'Assistant response ready.';
    } catch (error) {
      if (error.name === 'AbortError' || sequence !== requestSequence) return;
      status.textContent = error.message === 'Assistant unavailable'
        ? 'The assistant is unavailable. Use Explore to search products.'
        : 'The assistant is unavailable. Use Explore to search products.';
    } finally {
      if (sequence === requestSequence) {
        activeController = null;
        setBusy(false);
      }
    }
  });

  window.addEventListener('pagehide', cancelPending, {once: true});
})();
