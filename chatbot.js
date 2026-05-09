// js/chatbot.js
// Oracle chat — Strangeness IS
// Backend: https://api.strangenessis.com

const BACKEND_URL   = 'https://api.strangenessis.com';
const FREE_MESSAGES = 3;
const PHONE_NUMBER  = '1-800-STRANGE'; // Update when vanity number is confirmed

let messageCount        = 0;
let portalShown         = false;
let portalDismissed     = false;
let chatHistory         = [];
let conversationSummary = '';
let sessionId           = 'sess_' + Math.random().toString(36).slice(2);


const messagesEl    = document.getElementById('messages');
const inputEl       = document.getElementById('user-input');
const sendBtn       = document.getElementById('send-btn');
const counterText   = document.getElementById('counter-text');
const portalOverlay = document.getElementById('portal-overlay');
const summaryTextEl = document.getElementById('summary-text');
const statusDot     = document.getElementById('status-dot');
const statusTextEl  = document.getElementById('status-text');
const portalFab     = document.getElementById('portal-fab');

document.addEventListener('DOMContentLoaded', () => {
  updateCounter();

  inputEl.addEventListener('input', () => {
    inputEl.style.height = 'auto';
    inputEl.style.height = Math.min(inputEl.scrollHeight, 140) + 'px';
  });

  inputEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  sendBtn.addEventListener('click', sendMessage);
});

function updateCounter() {
  const remaining = Math.max(0, FREE_MESSAGES - messageCount);
  const el = document.getElementById('message-counter');
  if (!el) return;
  el.classList.remove('warning', 'unlocked', 'unlimited');

  if (portalDismissed) {
    if (counterText) counterText.textContent = 'Unlimited Oracle access';
    el.classList.add('unlimited');
  } else if (remaining === 0) {
    if (counterText) counterText.textContent = 'Portal unlocked 🌀';
    el.classList.add('unlocked');
  } else if (remaining === 1) {
    if (counterText) counterText.textContent = `${remaining} free question remaining`;
    el.classList.add('warning');
  } else {
    if (counterText) counterText.textContent = `${remaining} free questions remaining`;
  }
}

async function sendMessage() {
  const text = inputEl.value.trim();
  if (!text || sendBtn.disabled) return;
  if (portalShown && !portalDismissed) return;

  messageCount++;

  updateCounter();

  appendMessage('user', text);
  chatHistory.push({ role: 'user', content: text });

  inputEl.value = '';
  inputEl.style.height = 'auto';
  sendBtn.disabled = true;

  const loadingEl = appendMessage('loading', '🔮 The Oracle contemplates...');

  try {
    const response = await fetch(`${BACKEND_URL}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message:    text,
        history:    chatHistory.slice(-10),
        session_id: sessionId,
      }),
    });

    // Server-side free limit reached — show portal immediately
    if (response.status === 402) {
      loadingEl.remove();
      if (!portalShown) setTimeout(showPortal, 200);
      sendBtn.disabled = false;
      inputEl.focus();
      return;
    }

    if (!response.ok) throw new Error(`Server error: ${response.status}`);

    const data = await response.json();
    loadingEl.remove();
    appendMessage('bot', data.reply);
    chatHistory.push({ role: 'assistant', content: data.reply });
    // Update session ID if server returns one
    if (data.session_id) sessionId = data.session_id;

  } catch (err) {
    loadingEl.remove();
    appendMessage('error', `⚠️ The Oracle cannot be reached.\n\nError: ${err.message}`);
  } finally {
    sendBtn.disabled = false;
    inputEl.focus();
  }

  if (messageCount >= FREE_MESSAGES && !portalShown) {
    setTimeout(showPortal, 800);
  }
}

async function showPortal() {
  portalShown = true;
  if (portalOverlay) {
    portalOverlay.classList.add('visible');
    document.body.style.overflow = 'hidden';
  }
  generateSummary();
  checkAgentStatus();
}

function hidePortal() {
  if (portalOverlay) portalOverlay.classList.remove('visible');
  document.body.style.overflow = '';
}

function continueWithAI() {
  portalDismissed = true;
  hidePortal();
  updateCounter();
  if (portalFab) portalFab.style.display = 'flex';
  inputEl.focus();
}

async function generateSummary() {
  if (!chatHistory.length) {
    if (summaryTextEl) summaryTextEl.textContent = 'No conversation yet.';
    return;
  }
  const preview = chatHistory.slice(-6).map(m =>
    `${m.role === 'user' ? 'Visitor' : 'Oracle'}: ${m.content.slice(0, 120)}${m.content.length > 120 ? '...' : ''}`
  ).join('\n');
  if (summaryTextEl) summaryTextEl.textContent = preview;
  conversationSummary = preview;

  try {
    const res = await fetch(`${BACKEND_URL}/summarize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ history: chatHistory }),
    });
    if (res.ok) {
      const data = await res.json();
      if (data.summary) {
        if (summaryTextEl) summaryTextEl.textContent = data.summary;
        conversationSummary = data.summary;
      }
    }
  } catch {
    // preview fallback is fine
  }
}

function checkAgentStatus() {
  if (typeof Tawk_API !== 'undefined' && Tawk_API.getStatus) {
    setAgentOnline(Tawk_API.getStatus() === 'online');
  } else {
    setAgentOnline(false);
  }
}

function setAgentOnline(online) {
  if (statusDot) statusDot.className = 'status-dot ' + (online ? 'online' : 'offline');
  if (statusTextEl) statusTextEl.textContent = online
    ? 'Investigator online — ready to connect now'
    : 'Investigator offline — use email follow-up below';
  const liveBtn = document.getElementById('btn-live');
  if (liveBtn && !online) {
    liveBtn.disabled = true;
    liveBtn.textContent = 'Investigator offline';
  }
}

function launchLiveChat() {
  if (typeof Tawk_API === 'undefined' || !Tawk_API.maximize) {
    alert('Live chat not configured yet. Please use the email option below.');
    return;
  }
  if (Tawk_API.setAttributes) {
    Tawk_API.setAttributes({
      name:    'Strangeness IS Visitor',
      summary: conversationSummary || 'No summary available',
    }, () => {});
  }
  Tawk_API.showWidget();
  Tawk_API.maximize();
  hidePortal();
  if (portalFab) portalFab.style.display = 'flex';
}

async function submitEmailHandoff() {
  const emailInput = document.getElementById('email-input');
  const email = emailInput ? emailInput.value.trim() : '';

  if (!email || !email.includes('@') || !email.includes('.')) {
    if (emailInput) {
      emailInput.style.borderColor = '#ef4444';
      emailInput.placeholder = 'Please enter a valid email';
    }
    return;
  }
  if (emailInput) emailInput.style.borderColor = '';

  const btn = document.querySelector('.btn-email');
  if (btn) { btn.disabled = true; btn.textContent = 'Sending...'; }

  try {
    const res = await fetch(`${BACKEND_URL}/handoff`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        visitor_email: email,
        summary:       conversationSummary,
        history:       chatHistory,
        session_id:    sessionId,
      }),
    });

    if (!res.ok) throw new Error('Server error');

    const emailForm    = document.getElementById('email-form');
    const emailSuccess = document.getElementById('email-success');
    if (emailForm)    emailForm.style.display    = 'none';
    if (emailSuccess) emailSuccess.style.display = 'block';
    setTimeout(continueWithAI, 3000);

  } catch (err) {
    if (btn) { btn.disabled = false; btn.textContent = 'Send summary'; }
    appendMessage('error', `⚠️ Could not send: ${err.message}`);
    hidePortal();
  }
}

function appendMessage(role, text) {
  const el = document.createElement('div');
  el.className = `message ${role}`;
  el.textContent = text;
  messagesEl.appendChild(el);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return el;
}
