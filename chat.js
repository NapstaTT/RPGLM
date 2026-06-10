console.log("chat.js v0.3 loaded");

const chatContainer = document.querySelector('.chat-window');
const textarea = document.querySelector('.message-input');
const sendButton = document.querySelector('.main-footer .menu-button:last-child');
let currentController = null;
let isGenerating = false;

function escapeHtml(str) {
    return str.replace(/[&<>]/g, function(m) {
        if (m === '&') return '&amp;';
        if (m === '<') return '&lt;';
        if (m === '>') return '&gt;';
        return m;
    });
}

function addMessage(text, sender) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message');
    if (sender === 'System') {
        messageDiv.innerHTML = `<em>${escapeHtml(text)}</em>`;
    } else {
        messageDiv.innerHTML = `<strong>${escapeHtml(sender)}:</strong> ${escapeHtml(text)}`;
    }
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
            let sender = msg.role;
            if (sender === 'user') sender = 'User';
            addMessage(msg.content, sender);
        }
    } catch (err) {
        console.error("loadHistory error:", err);
        addMessage("Failed to load history", "System");
    }
}

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

    addMessage(text, 'user');
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
            body: JSON.stringify({ text: text }),
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
            // Пользователь нажал Stop – сервер уже сохранил частичный ответ
            // Просто перезагружаем историю, чтобы отобразить сохранённое
            await loadHistory();
            if (!accumulatedReply) {
                addMessage('[Generation stopped]', 'System');
            }
        } else {
            console.error("sendMessage error:", err);
            addMessage("Error: " + err.message, "System");
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

loadHistory();