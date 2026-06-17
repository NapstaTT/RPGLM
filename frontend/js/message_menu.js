// frontend/js/message_menu.js
class MessageMenu {
    constructor() {
        this.modal = null;
        this.createModal();
        this.attachButton();
    }

    createModal() {
        const modalDiv = document.createElement('div');
        modalDiv.id = 'message-menu-modal';
        modalDiv.className = 'lorebook-modal hidden';
        modalDiv.innerHTML = `
            <div class="lorebook-overlay"></div>
            <div class="lorebook-container" style="max-width:300px; height:auto; margin:auto; top:30%;">
                <div class="lorebook-header">
                    <span style="flex:1; text-align:center;">Message Actions</span>
                    <button class="lorebook-close" id="msg-menu-close">✖</button>
                </div>
                <div class="lorebook-content" style="display:flex; flex-direction:column; gap:10px;">
                    <button id="rollback-btn" class="lorebook-add-btn" style="background:#3c3f58; color:white;">Delete Last Message</button>
                    <!-- WIP: edit, regenerate, etc. -->
                </div>
            </div>
        `;
        document.body.appendChild(modalDiv);
        this.modal = modalDiv;

        modalDiv.querySelector('.lorebook-overlay').addEventListener('click', () => this.close());
        modalDiv.querySelector('#msg-menu-close').addEventListener('click', () => this.close());

        const rollbackBtn = modalDiv.querySelector('#rollback-btn');
        rollbackBtn.addEventListener('click', async () => {
            await this.rollback();
            this.close();
        });
    }

    attachButton() {
        const btn = document.getElementById('message-menu-btn');
        if (btn) {
            btn.addEventListener('click', () => this.open());
        } else {
            console.warn('Message menu button not found');
        }
    }

    open() {
        this.modal.classList.remove('hidden');
    }

    close() {
        this.modal.classList.add('hidden');
    }

    async rollback() {
        try {
            const response = await fetch('/api/rollback', { method: 'POST' });
            if (!response.ok) throw new Error(await response.text());
            const newWorldState = await response.json();
            // world_state update to fallback to previous world state
            if (window.worldStatePanel) {
                window.worldStatePanel.locationSelect.value = newWorldState.location_id || '';
                window.worldStatePanel.characterSelect.value = newWorldState.active_character_id || '';
                window.worldStatePanel.timeInput.value = newWorldState.time_string || '';
            }
            // Reload chat history
            if (window.loadHistory) {
                await window.loadHistory();
            } else {
                // backup plan
                window.location.reload();
            }
        } catch (err) {
            alert('Rollback failed: ' + err.message);
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.messageMenu = new MessageMenu();
});