(() => {
  'use strict';

  const shell = document.getElementById('chat-shell');
  const transcript = document.getElementById('chat-transcript');
  if (!shell || !transcript) return;

  const liveStatus = document.getElementById('chat-live-status');
  const readMessageInput = document.getElementById('chat-read-message-id');
  const updatesUrl = shell.dataset.updatesUrl || '';
  const liveUpdates = shell.dataset.liveUpdates === 'true';
  const startingCursor = Number(shell.dataset.latestMessageId || '0');
  let latestMessageId = Number.isSafeInteger(startingCursor) && startingCursor >= 0
    ? startingCursor : 0;
  const knownMessageIds = new Set(
    Array.from(transcript.querySelectorAll('[data-message-id]'))
      .map(item => Number(item.dataset.messageId))
      .filter(Number.isSafeInteger)
  );
  let timerId = null;
  let activeController = null;
  let requestInFlight = false;
  let pollingStopped = false;

  const shortTime = new Intl.DateTimeFormat(undefined, {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
  const fullTime = new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  });

  const setStatus = message => {
    if (liveStatus) liveStatus.textContent = message;
  };

  const localizeTime = timeElement => {
    if (!timeElement || timeElement.dataset.localized === 'true') return;
    const value = timeElement.dataset.utcTime || timeElement.getAttribute('datetime');
    const date = new Date(value);
    if (!value || Number.isNaN(date.getTime())) return;
    timeElement.textContent = shortTime.format(date);
    const complete = fullTime.format(date);
    timeElement.title = complete;
    timeElement.setAttribute('aria-label', complete);
    timeElement.dataset.localized = 'true';
  };

  transcript.querySelectorAll('time[data-utc-time]').forEach(localizeTime);

  const messageIsValid = (message, previousId) => {
    if (!message || typeof message !== 'object' || Array.isArray(message)) return false;
    const keys = Object.keys(message).sort();
    const expected = ['body', 'created_at', 'fallback_time', 'id', 'is_own', 'sender_username'];
    if (keys.length !== expected.length || keys.some((key, index) => key !== expected[index])) {
      return false;
    }
    if (!Number.isSafeInteger(message.id) || message.id <= previousId) return false;
    if (typeof message.body !== 'string' || message.body.length < 1 || message.body.length > 2000) return false;
    if (typeof message.sender_username !== 'string' || message.sender_username.length < 1 || message.sender_username.length > 80) return false;
    if (typeof message.is_own !== 'boolean') return false;
    if (typeof message.created_at !== 'string' || message.created_at.length > 40 || Number.isNaN(new Date(message.created_at).getTime())) return false;
    if (typeof message.fallback_time !== 'string' || message.fallback_time.length < 1 || message.fallback_time.length > 30) return false;
    return true;
  };

  const payloadIsValid = payload => {
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return false;
    const keys = Object.keys(payload).sort();
    if (keys.join(',') !== 'has_more,latest_id,messages') return false;
    if (!Array.isArray(payload.messages) || payload.messages.length > 50) return false;
    if (!Number.isSafeInteger(payload.latest_id) || payload.latest_id < latestMessageId) return false;
    if (typeof payload.has_more !== 'boolean') return false;
    let previousId = latestMessageId;
    for (const message of payload.messages) {
      if (!messageIsValid(message, previousId)) return false;
      previousId = message.id;
    }
    if (payload.messages.length && payload.latest_id !== previousId) return false;
    if (!payload.messages.length && payload.latest_id !== latestMessageId) return false;
    return true;
  };

  const createMessage = message => {
    const row = document.createElement('li');
    row.className = `chat-message ${message.is_own ? 'chat-message--outgoing' : 'chat-message--incoming'}`;
    row.dataset.messageId = String(message.id);

    const bubble = document.createElement('article');
    bubble.className = 'chat-bubble';
    bubble.setAttribute('aria-label', `Message from ${message.is_own ? 'you' : message.sender_username}`);

    const sender = document.createElement('span');
    sender.className = 'chat-message-sender';
    sender.textContent = message.is_own ? 'You' : message.sender_username;

    const body = document.createElement('p');
    body.className = 'chat-message-body preserve-lines';
    body.textContent = message.body;

    const time = document.createElement('time');
    time.className = 'chat-message-time';
    time.dateTime = message.created_at;
    time.dataset.utcTime = message.created_at;
    time.textContent = message.fallback_time;

    bubble.append(sender, body, time);
    row.append(bubble);
    localizeTime(time);
    return row;
  };

  const closeToBottom = () => (
    transcript.scrollHeight - transcript.scrollTop - transcript.clientHeight <= 80
  );

  const appendBatch = payload => {
    const shouldFollow = closeToBottom();
    let appended = 0;
    for (const message of payload.messages) {
      if (knownMessageIds.has(message.id)) continue;
      const empty = document.getElementById('chat-empty-state');
      if (empty) empty.remove();
      transcript.append(createMessage(message));
      knownMessageIds.add(message.id);
      appended += 1;
    }
    latestMessageId = payload.latest_id;
    shell.dataset.latestMessageId = String(latestMessageId);
    if (readMessageInput && latestMessageId > Number(readMessageInput.value || '0')) {
      readMessageInput.value = String(latestMessageId);
    }
    if (appended && shouldFollow) {
      transcript.scrollTop = transcript.scrollHeight;
      setStatus('');
    } else if (appended) {
      setStatus('New messages arrived.');
    } else if (liveStatus && liveStatus.textContent === 'Waiting to reconnect…') {
      setStatus('');
    }
  };

  const schedule = delay => {
    if (pollingStopped || document.hidden) return;
    if (timerId !== null) window.clearTimeout(timerId);
    timerId = window.setTimeout(poll, delay);
  };

  const stopForSession = () => {
    pollingStopped = true;
    setStatus('Your session ended. Reload this page to sign in again.');
  };

  async function poll() {
    timerId = null;
    if (pollingStopped || document.hidden) return;
    if (requestInFlight) {
      schedule(100);
      return;
    }
    requestInFlight = true;
    activeController = new AbortController();
    try {
      const url = new URL(updatesUrl, window.location.origin);
      url.searchParams.set('after_id', String(latestMessageId));
      const response = await fetch(url, {
        credentials: 'same-origin',
        cache: 'no-store',
        headers: {'Accept': 'application/json'},
        signal: activeController.signal,
      });
      const contentType = response.headers.get('content-type') || '';
      if (response.redirected || [401, 403, 404].includes(response.status) || !contentType.includes('application/json')) {
        stopForSession();
        return;
      }
      if (!response.ok) throw new Error('temporary');
      const payload = await response.json();
      if (!payloadIsValid(payload)) throw new Error('invalid');
      appendBatch(payload);
      schedule(payload.has_more ? 0 : 3000);
    } catch (error) {
      if (error && error.name === 'AbortError') return;
      setStatus('Waiting to reconnect…');
      schedule(3000);
    } finally {
      requestInFlight = false;
      activeController = null;
    }
  }

  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      if (timerId !== null) window.clearTimeout(timerId);
      timerId = null;
      if (activeController) activeController.abort();
      return;
    }
    if (liveUpdates && !pollingStopped) schedule(0);
  });

  window.addEventListener('pagehide', () => {
    pollingStopped = true;
    if (timerId !== null) window.clearTimeout(timerId);
    if (activeController) activeController.abort();
  });

  if (liveUpdates && updatesUrl) {
    transcript.scrollTop = transcript.scrollHeight;
    schedule(3000);
  }
})();
