/**
 * Main chat interaction module.
 * Handles sending messages to the backend and displaying LLM replies.
 */

// DOM elements
const chatContainer = document.querySelector('.chat-window');
const textarea = document.querySelector('.message-input');
const sendButton = document.querySelector('.main-footer .menu-button:last-child');
const menuButtons = document.querySelectorAll('.main-header .menu-button');

/**
 * Appends a message to the chat window.
 * @param {string} text - Message content.
 * @param {string} sender - Name of the sender (e.g., 'You', 'World').
 */
function addMessage(text, sender) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message');
    messageDiv.innerHTML = `<strong>${escapeHtml(sender)}:</strong> ${escapeHtml(text)}`;
    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

/**
 * Simple HTML escape to prevent XSS.
 * @param {string} str - Raw string.
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
 * Sends user message to backend and displays the reply.
 */
async function sendMessage() {
    const text = textarea.value.trim();
    if (text === '') return;

    addMessage(text, 'You');
    textarea.value = '';

    try {
        const response = await fetch('/api/send', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: text })
        });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();
        addMessage(data.reply, 'World');
    } catch (error) {
        console.error('Send error:', error);
        addMessage('Failed to reach the server. Is it running?', 'System');
    }
}

// Event listeners
sendButton.addEventListener('click', sendMessage);
textarea.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

menuButtons.forEach((btn, idx) => {
    btn.addEventListener('click', () => console.log(`Menu button ${idx} clicked`));
});