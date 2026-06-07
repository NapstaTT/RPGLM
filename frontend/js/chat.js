console.log("chat.js loaded");

const chatContainer = document.querySelector('.chat-window');
const textarea = document.querySelector('.message-input');
const sendButton = document.querySelector('.main-footer .menu-button:last-child');

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
    messageDiv.innerHTML = `<strong>${escapeHtml(sender)}:</strong> ${escapeHtml(text)}`;
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
            if (sender === 'user') sender = 'You';
            else if (sender === 'assistant') sender = 'World';
            addMessage(msg.content, sender);
        }
    } catch (err) {
        console.error("loadHistory error:", err);
        addMessage("Не удалось загрузить историю", "System");
    }
}

async function sendMessage() {
    const text = textarea.value.trim();
    if (!text) return;
    addMessage(text, 'You');
    textarea.value = '';

    try {
        const response = await fetch('/api/send', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: text })
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        await response.json();
        await loadHistory();
    } catch (err) {
        console.error("sendMessage error:", err);
        addMessage("Ошибка при отправке", "System");
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