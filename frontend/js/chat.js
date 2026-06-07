/**
 * RPGLM Frontend Controller (v0.3.0 Release)
 * Handles macro execution pipelines, lexical parsing, and storage synchronization.
 */

console.log("chat.js loaded");

const chatContainer = document.querySelector('.chat-window');
const textarea = document.querySelector('.message-input');
const sendButton = document.querySelector('.main-footer .menu-button:last-child');

/**
 * Encodes special character symbols to prevent HTML structural breaking.
 * @param {string} str - Raw string text.
 * @returns {string} - Escaped plain-text string.
 */
function escapeHtml(str) {
    return str.replace(/[&<>]/g, function(m) {
        switch (m) {
            case '&': return '&amp;';
            case '<': return '&lt;';
            case '>': return '&gt;';
            default: return m;
        }
    });
}

/**
 * RPGLM Multi-pass Lexical Analyzer
 * Processes raw server text stream outputs and wraps segments into custom-styled structures.
 * Implements a secure token-hiding placeholder workflow to prevent nested collision.
 * @param {string} text - Raw content received from the narrative pipeline.
 * @returns {string} - Styled document HTML fragment.
 */
function parseDialogue(text) {
    if (!text) return "";

    let html = escapeHtml(text);
    const codeBlocks = [];
    const thoughts = [];

    // Stage 1: Protect triple backtick system data structures (Code blocks)
    html = html.replace(/```([\s\S]*?)```/g, function(match, code) {
        codeBlocks.push(code);
        return `___CODE_BLOCK_PLACEHOLDER_${codeBlocks.length - 1}___`;
    });

    // Stage 2: Protect single backtick internal monologue constructs (Thoughts)
    html = html.replace(/`([\s\S]*?)`/g, function(match, thought) {
        thoughts.push(thought);
        return `___THOUGHTS_PLACEHOLDER_${thoughts.length - 1}___`;
    });

    // Stage 3: Parse character name blocks (**Name:**)
    html = html.replace(/\*\*([A-Za-zА-Яа-я0-9_\-\s]+):\*\*/g, function(match, name) {
        return `<span class="char-name">${name}:</span>`;
    });

    // Stage 4: Parse actions and environmental descriptions (*Narrative*)
    html = html.replace(/\*([\s\S]*?)\*/g, function(match, content) {
        return `<span class="narrative">*${content}*</span>`;
    });

    // Stage 5: Parse spoken character conversations ("Speech")
    html = html.replace(/"([\s\S]*?)"/g, function(match, content) {
        return `<span class="speech">"${content}"</span>`;
    });

    // Stage 6: Restore single backtick thoughts
    html = html.replace(/___THOUGHTS_PLACEHOLDER_(\d+)___/g, function(match, index) {
        return `<span class="thoughts">${thoughts[parseInt(index, 10)]}</span>`;
    });

    // Stage 7: Restore triple backtick code blocks
    html = html.replace(/___CODE_BLOCK_PLACEHOLDER_(\d+)___/g, function(match, index) {
        return `<pre class="code-block">${codeBlocks[parseInt(index, 10)]}</pre>`;
    });

    // Convert newlines to breaks for dynamic paragraph preservation
    html = html.replace(/\n/g, '<br>');

    return html;
}

/**
 * Creates and appends a safe message card viewport component to the chat log.
 * @param {string} sender - Role representation ('You', 'World', 'System').
 * @returns {HTMLElement} - Created message node.
 */
function createMessageElement(sender) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message');
    messageDiv.setAttribute('data-sender', sender);
    chatContainer.appendChild(messageDiv);
    return messageDiv;
}

/**
 * Downloads and synchronizes chat logs from persistent backend storage APIs.
 */
async function loadHistory() {
    try {
        const response = await fetch('/api/history');
        if (!response.ok) throw new Error(`HTTP Error Status: ${response.status}`);
        const data = await response.json();
        chatContainer.innerHTML = '';
        
        for (const msg of data.messages) {
            const sender = msg.role === 'user' ? 'You' : 'World';
            const div = createMessageElement(sender);
            div.innerHTML = parseDialogue(msg.content);
        }
        chatContainer.scrollTop = chatContainer.scrollHeight;
    } catch (err) {
        console.error("loadHistory error:", err);
        const div = createMessageElement('System');
        div.innerHTML = "<strong>System:</strong> Failed to fetch persistent history.";
    }
}

/**
 * Translates input fields, handles predictive execution, and updates UI layouts.
 */
async function sendMessage() {
    const text = textarea.value.trim();
    if (!text) return;
    
    // Optimistic rendering on the client-side using predefined mock replacements
    const userDiv = createMessageElement('You');
    const clientCompiled = text.replace(/{{user}}/g, "Artem").replace(/{{char}}/g, "Mia");
    userDiv.innerHTML = parseDialogue(clientCompiled);
    
    textarea.value = '';
    chatContainer.scrollTop = chatContainer.scrollHeight;

    try {
        const response = await fetch('/api/send', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: text })
        });
        if (!response.ok) throw new Error(`HTTP Error Status: ${response.status}`);
        
        // Pull latest states
        await loadHistory();
    } catch (err) {
        console.error("sendMessage error:", err);
        const errDiv = createMessageElement('System');
        errDiv.innerHTML = `<strong>Error:</strong> ${escapeHtml(err.message)}`;
    }
}

// Global Event Listeners
sendButton.addEventListener('click', sendMessage);
textarea.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// App Initiation
loadHistory();