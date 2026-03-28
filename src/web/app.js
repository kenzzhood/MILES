/**
 * MILES Playground — Frontend Logic
 * 
 * API contract:
 *  POST /api/v1/interact        → { plan, task_ids, direct_response }
 *  GET  /api/v1/stream/{taskId} → SSE stream with status/result payloads
 * 
 * HTML elements required:
 *  #chat-form, #prompt-input, #send-btn
 *  #messages, #welcome-state
 *  #plan-list, #plan-count
 *  #tasks-list, #tasks-count
 *  #btn-clear
 *  Templates: #message-template, #task-template
 */

'use strict';

// ── Element refs ──────────────────────────────────────────────────────────────
const chatForm       = document.getElementById('chat-form');
const promptInput    = document.getElementById('prompt-input');
const sendBtn        = document.getElementById('send-btn');
const messagesEl     = document.getElementById('messages');
const welcomeState   = document.getElementById('welcome-state');
const planListEl     = document.getElementById('plan-list');
const planCountEl    = document.getElementById('plan-count');
const tasksListEl    = document.getElementById('tasks-list');
const tasksCountEl   = document.getElementById('tasks-count');
const btnClear       = document.getElementById('btn-clear');

const msgTemplate    = document.getElementById('message-template');
const taskTemplate   = document.getElementById('task-template');

// ── State ─────────────────────────────────────────────────────────────────────
const activeStreams = new Map();  // taskId → EventSource
let   taskCount    = 0;
let   typingNode   = null;

// ── Textarea auto-resize ──────────────────────────────────────────────────────
promptInput.addEventListener('input', () => {
  promptInput.style.height = 'auto';
  promptInput.style.height = Math.min(promptInput.scrollHeight, 180) + 'px';
});

// ── Enter = submit, Shift+Enter = newline ─────────────────────────────────────
promptInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    chatForm.dispatchEvent(new SubmitEvent('submit', { bubbles: true, cancelable: true }));
  }
});

// ── Suggestion chips ──────────────────────────────────────────────────────────
document.querySelectorAll('.suggestion-chip').forEach((chip) => {
  chip.addEventListener('click', () => {
    const prompt = chip.dataset.prompt;
    if (!prompt) return;
    promptInput.value = prompt;
    promptInput.dispatchEvent(new Event('input'));  // trigger resize
    chatForm.dispatchEvent(new SubmitEvent('submit', { bubbles: true, cancelable: true }));
  });
});

// ── Clear button ──────────────────────────────────────────────────────────────
btnClear.addEventListener('click', () => {
  // Close any open SSE streams first
  activeStreams.forEach((s) => s.close());
  activeStreams.clear();

  // Clear messages area and restore welcome state
  messagesEl.innerHTML = '';
  if (welcomeState) {
    welcomeState.style.display = '';
    messagesEl.appendChild(welcomeState);
  }

  // Reset dashboard panels
  planListEl.innerHTML = '<li class="plan-empty">No plan yet</li>';
  planCountEl.textContent = '—';

  tasksListEl.innerHTML = '<div class="tasks-empty">No tasks running</div>';
  tasksCountEl.textContent = '—';
  taskCount = 0;
});

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Hide the welcome state on first message */
function hideWelcome() {
  if (welcomeState && welcomeState.parentNode === messagesEl) {
    welcomeState.style.display = 'none';
  }
}

/** Scroll messages to the bottom */
function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

/** Show/remove the typing indicator */
function showTyping() {
  if (typingNode) return;
  typingNode = document.createElement('div');
  typingNode.className = 'message message--ai';
  typingNode.innerHTML = `<div class="typing-indicator"><span></span><span></span><span></span></div>`;
  messagesEl.appendChild(typingNode);
  scrollToBottom();
}
function hideTyping() {
  if (typingNode) { typingNode.remove(); typingNode = null; }
}

/**
 * Add a chat message bubble.
 * @param {string} sender
 * @param {string} text  — supports markdown
 * @param {'user'|'ai'|'system'} role
 */
function addMessage(sender, text, role = 'ai') {
  hideWelcome();
  hideTyping();

  const node = msgTemplate.content.firstElementChild.cloneNode(true);
  node.classList.add(`message--${role}`);

  node.querySelector('.message__sender').textContent = sender;
  node.querySelector('.message__time').textContent   = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  const body = node.querySelector('.message__body');

  // Render markdown if available
  const rendered = (window.marked && text) ? marked.parse(String(text)) : (String(text || '')).replace(/\n/g, '<br>');
  body.innerHTML = rendered;

  // If result contains a GLB model link, embed a model-viewer
  const glbMatch = (text || '').match(/\/models\/[\w\-.%]+\.glb(\?[^\s)"\]]*)?/);
  if (glbMatch) {
    const viewer = _makeModelViewer(glbMatch[0]);
    body.appendChild(viewer);
  }

  messagesEl.appendChild(node);
  scrollToBottom();
}

/** Build a model-viewer element */
function _makeModelViewer(srcUrl) {
  const viewer = document.createElement('model-viewer');
  viewer.src = srcUrl;
  viewer.setAttribute('camera-controls', '');
  viewer.setAttribute('auto-rotate', '');
  viewer.setAttribute('shadow-intensity', '1');
  viewer.setAttribute('environment-image', 'neutral');
  viewer.setAttribute('exposure', '1');
  viewer.style.cssText = 'width:100%;height:280px;border-radius:8px;background:#0a0e1a;margin-top:10px;display:block;';
  return viewer;
}

// ── Orchestrator Plan ─────────────────────────────────────────────────────────

function renderPlan(tasks) {
  planListEl.innerHTML = '';

  if (!tasks || tasks.length === 0) {
    planListEl.innerHTML = '<li class="plan-empty">Direct response — no workers dispatched</li>';
    planCountEl.textContent = '0';
    return;
  }

  planCountEl.textContent = tasks.length;

  tasks.forEach((task, i) => {
    const li = document.createElement('li');
    li.innerHTML = `
      <div class="plan-step-num">${i + 1}</div>
      <div class="plan-step-details">
        <strong>${_escHtml(task.worker_name)}</strong>
        <span>${_escHtml(task.prompt)}</span>
      </div>`;
    planListEl.appendChild(li);
  });
}

// ── Worker Tasks ──────────────────────────────────────────────────────────────

function _getOrCreateTaskCard(taskId, workerName, prompt) {
  let card = tasksListEl.querySelector(`[data-task-id="${CSS.escape(taskId)}"]`);
  if (card) return card;

  // Remove "no tasks" placeholder
  const empty = tasksListEl.querySelector('.tasks-empty');
  if (empty) empty.remove();

  card = taskTemplate.content.firstElementChild.cloneNode(true);
  card.dataset.taskId = taskId;
  card.querySelector('.task-worker').textContent = workerName;
  card.querySelector('.task-prompt').textContent = prompt;
  tasksListEl.appendChild(card);

  taskCount++;
  tasksCountEl.textContent = taskCount;

  return card;
}

function updateTaskStatus(taskId, status, resultText) {
  const card = tasksListEl.querySelector(`[data-task-id="${CSS.escape(taskId)}"]`);
  if (!card) return;

  const statusEl = card.querySelector('.task-status');
  statusEl.dataset.status = status;
  statusEl.textContent    = status;

  if ((status === 'SUCCESS' || status === 'FAILURE') && resultText) {
    const resultEl = card.querySelector('.task-card__result');
    resultEl.innerHTML = '';

    if (status === 'SUCCESS') {
      // Render markdown
      const textDiv = document.createElement('div');
      textDiv.innerHTML = window.marked ? marked.parse(String(resultText)) : _escHtml(String(resultText));
      resultEl.appendChild(textDiv);

      // Embed model viewer if GLB link present
      const glbMatch = resultText.match(/\/models\/[\w\-.%]+\.glb(\?[^\s)"\]]*)?/);
      if (glbMatch) {
        resultEl.appendChild(_makeModelViewer(glbMatch[0]));
      }
    } else {
      resultEl.innerHTML = `<span style="color:var(--c-danger);font-size:0.8rem">${_escHtml(String(resultText))}</span>`;
    }
  }
}

function subscribeToTask(taskId, workerName, prompt) {
  _getOrCreateTaskCard(taskId, workerName, prompt);
  updateTaskStatus(taskId, 'PENDING');

  const stream = new EventSource(`/api/v1/stream/${encodeURIComponent(taskId)}`);
  activeStreams.set(taskId, stream);

  stream.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data);
      updateTaskStatus(taskId, payload.status, payload.result);

      if (payload.status === 'SUCCESS' || payload.status === 'FAILURE') {
        stream.close();
        activeStreams.delete(taskId);

        // Echo result to chat
        addMessage(
          workerName,
          payload.result || `Task finished with status ${payload.status}`,
          payload.status === 'FAILURE' ? 'system' : 'ai'
        );
      }
    } catch (err) {
      console.error('[MILES] SSE parse error:', err);
    }
  };

  stream.onerror = () => {
    stream.close();
    activeStreams.delete(taskId);
    updateTaskStatus(taskId, 'FAILURE', 'Connection to task stream lost.');
  };
}

// ── Form submit ───────────────────────────────────────────────────────────────
chatForm.addEventListener('submit', async (e) => {
  e.preventDefault();

  const prompt = promptInput.value.trim();
  if (!prompt) return;

  // Show user message immediately
  addMessage('You', prompt, 'user');
  promptInput.value = '';
  promptInput.style.height = 'auto';
  sendBtn.disabled = true;
  showTyping();

  try {
    const response = await fetch('/api/v1/interact', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ prompt }),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Server error ${response.status}`);
    }

    const data  = await response.json();
    const tasks = data.plan?.tasks ?? [];

    // Render plan sidebar
    renderPlan(tasks);

    // Show direct AI response
    if (data.direct_response) {
      addMessage('MILES', data.direct_response, 'ai');
    }

    // Subscribe to worker tasks
    if (tasks.length > 0) {
      if (!data.direct_response) {
        hideTyping();  // already handled above for direct_response
      }
      tasks.forEach((task, i) => {
        const taskId = data.task_ids?.[i];
        if (taskId) subscribeToTask(taskId, task.worker_name, task.prompt);
      });
    } else if (!data.direct_response) {
      addMessage('MILES', 'No response generated.', 'ai');
    }

  } catch (error) {
    console.error('[MILES] Fetch error:', error);
    hideTyping();
    addMessage('System', error.message, 'system');
  } finally {
    sendBtn.disabled = false;
    promptInput.focus();
  }
});

// ── Cleanup on page unload ────────────────────────────────────────────────────
window.addEventListener('beforeunload', () => {
  activeStreams.forEach((s) => s.close());
  activeStreams.clear();
});

// ── Utility ───────────────────────────────────────────────────────────────────
function _escHtml(str) {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}
