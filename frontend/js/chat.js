// chat.js v0.5 with Persona support
console.log("chat.js v0.5 with Persona support");

const chatContainer = document.querySelector('.chat-window');
const textarea = document.querySelector('.message-input');
const sendButton = document.querySelector('.main-footer .menu-button:last-child');
let currentController = null;
let isGenerating = false;

// Global user name (loaded from Persona)
let currentUserName = 'User';

/**
 * Escape HTML special characters.
 * @param {string} str - Input string.
 * @returns {string} Escaped string.
 */
function escapeHtml(str) {
    return str.replace(/[&<>]/g, function(m) {
        if (m === '&') return '&amp;';
        if (m === '<') return '&lt;';
        if (m === '>') return '&gt;';
        return m;
    });
}

/**
 * Add a message to the chat window.
 * @param {string} text - Message content.
 * @param {string} role - Role (user, assistant, system).
 * @param {boolean} isUser - Whether this message is from the user.
 */
function addMessage(text, role, isUser = false) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message');
    if (role === 'System') {
        messageDiv.innerHTML = `<em>${escapeHtml(text)}</em>`;
    } else {
        let displayName = role;
        if (isUser) {
            displayName = currentUserName;
        }
        messageDiv.innerHTML = `<strong>${escapeHtml(displayName)}:</strong> ${escapeHtml(text)}`;
    }
    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

/**
 * Load conversation history from the server.
 */
async function loadHistory() {
    try {
        const response = await fetch('/api/history');
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        chatContainer.innerHTML = '';
        for (const msg of data.messages) {
            if (msg.role === 'system') continue; // completely ignore system
            let role = msg.role;
            const isUser = (role === 'user');
            if (isUser) role = 'user';
            addMessage(msg.content, role, isUser);
        }
    } catch (err) {
        console.error("loadHistory error:", err);
        addMessage("Failed to load history", "System", false);
    }
}

/**
 * Load user persona from the server.
 */
async function loadPersona() {
    try {
        const resp = await fetch('/api/persona');
        const persona = await resp.json();
        if (persona.name && persona.name.trim()) {
            currentUserName = persona.name.trim();
        } else {
            currentUserName = 'User';
        }
        console.log(`[Chat] User name set to: ${currentUserName}`);
    } catch (err) {
        console.warn('Could not load persona:', err);
        currentUserName = 'User';
    }
}

/**
 * Update user name from modal (called by persona_modal).
 * @param {string} newName - New user name.
 */
window.updateUserName = function(newName) {
    if (newName && newName.trim()) {
        currentUserName = newName.trim();
        console.log(`[Chat] User name updated to: ${currentUserName}`);
        // Reload history to update all user messages
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

/**
 * Send a message to the LLM and handle streaming response.
 */
async function sendMessage() {
    if (isGenerating) {
        if (currentController) {
            currentController.abort();
        }
        try {
            await fetch('/api/abort', { method: 'POST' });
        } catch(e) { console.warn("abort request failed", e); }
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

    addMessage(text, 'user', true);
    textarea.value = '';
    textarea.style.height = 'auto';

    isGenerating = true;
    setSendButtonToStop();

    currentController = new AbortController();
    let accumulatedReply = '';

    try {
        const response = await fetch('/api/send/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: text,
                world_state: worldState
            }),
            signal: currentController.signal
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = line.slice(6);
                    if (data === '[DONE]') {
                        await loadHistory();
                        break;
                    } else {
                        accumulatedReply += data;
                    }
                }
            }
        }
    } catch (err) {
        if (err.name === 'AbortError') {
            await loadHistory();
            if (!accumulatedReply) {
                addMessage('[Generation stopped]', 'System', false);
            }
        } else {
            console.error("sendMessage error:", err);
            addMessage("Error: " + err.message, "System", false);
        }
    } finally {
        isGenerating = false;
        setSendButtonToSend();
        currentController = null;
    }
}

sendButton.addEventListener('click', sendMessage);
textarea.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// Load persona and history on startup
(async function init() {
    await loadPersona();
    await loadHistory();
})();