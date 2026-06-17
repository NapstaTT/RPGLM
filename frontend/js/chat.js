console.log("chat.js v0.5 — final with timeout");

const chatContainer = document.querySelector('.chat-window');
const textarea = document.querySelector('.message-input');
const sendButton = document.querySelector('.main-footer .menu-button:last-child');
let isGenerating = false;
let currentAbortController = null;
let timeoutId = null;

let currentUserName = 'Player';

function escapeHtml(str) {
    return str.replace(/[&<>]/g, function(m) {
        if (m === '&') return '&amp;';
        if (m === '<') return '&lt;';
        if (m === '>') return '&gt;';
        return m;
    });
}

function addMessage(text, role) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message');
    let displayName = role;
    if (role === 'user') {
        displayName = currentUserName;
    }
    messageDiv.innerHTML = `<strong>${escapeHtml(displayName)}:</strong> ${escapeHtml(text)}`;
    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

async function loadHistory() {
    try {
        const response = await fetch('/api/history');
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        chatContainer.innerHTML = '';
        for (const msg of data.messages) {
            if (msg.role === 'system') continue;
            addMessage(msg.content, msg.role);
        }
    } catch (err) {
        console.error("loadHistory error:", err);
        addMessage("Failed to load history", "System");
    }
}

async function loadPersona() {
    try {
        const resp = await fetch('/api/persona');
        const persona = await resp.json();
        if (persona.name && persona.name.trim()) {
            currentUserName = persona.name.trim();
        } else {
            currentUserName = 'Player';
        }
        console.log(`[Chat] User name set to: ${currentUserName}`);
    } catch (err) {
        console.warn('Could not load persona:', err);
        currentUserName = 'Player';
    }
}

window.updateUserName = function(newName) {
    if (newName && newName.trim()) {
        currentUserName = newName.trim();
        console.log(`[Chat] User name updated to: ${currentUserName}`);
        loadHistory();
    }
};

function setSendButtonToStop() {
    sendButton.innerHTML = `<svg class="icon" width="45" height="45"><use href="/assets/icons/icons.svg#icon-stop"></use></svg>`;
    sendButton.classList.add('stop-button');
}

function setSendButtonToSend() {
    sendButton.innerHTML = `<svg class="icon" width="45" height="45"><use href="/assets/icons/icons.svg#icon-paper-plane"></use></svg>`;
    sendButton.classList.remove('stop-button');
}

async function sendMessage() {
    if (isGenerating) {
        if (currentAbortController) {
            currentAbortController.abort();
        }
        try {
            await fetch('/api/abort', { method: 'POST' });
        } catch(e) {
            console.warn("abort request failed", e);
        }
        isGenerating = false;
        setSendButtonToSend();
        return;
    }

    const text = textarea.value.trim();
    if (!text) return;

    let worldState = null;
    if (window.worldStatePanel && typeof window.worldStatePanel.getCurrentState === 'function') {
        worldState = window.worldStatePanel.getCurrentState();
    }

    addMessage(text, 'user');
    textarea.value = '';
    textarea.style.height = 'auto';

    isGenerating = true;
    setSendButtonToStop();

    currentAbortController = new AbortController();
    timeoutId = setTimeout(() => {
        if (currentAbortController) {
            currentAbortController.abort();
        }
    }, 300000);

    try {
        const response = await fetch('/api/send', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: text,
                world_state: worldState
            }),
            signal: currentAbortController.signal
        });

        clearTimeout(timeoutId);
        timeoutId = null;

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }

        const data = await response.json();
        if (data.messages && data.messages.length) {
            for (const msg of data.messages) {
                addMessage(msg.content, msg.role);
            }
        } else {
            await loadHistory();
        }
    } catch (err) {
        clearTimeout(timeoutId);
        timeoutId = null;
        if (err.name === 'AbortError') {
            await loadHistory();
        } else {
            console.error("sendMessage error:", err);
            addMessage("Error: " + err.message, "System");
        }
    } finally {
        clearTimeout(timeoutId);
        timeoutId = null;
        isGenerating = false;
        setSendButtonToSend();
        currentAbortController = null;
    }
}

sendButton.addEventListener('click', sendMessage);
textarea.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

(async function init() {
    await loadPersona();
    await loadHistory();
})();

window.loadHistory = loadHistory;