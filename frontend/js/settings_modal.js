// frontend/js/settings_modal.js
/**
 * SettingsModal – main settings modal with links to other modals.
 */
class SettingsModal {
    constructor() {
        this.modal = null;
        this.createModal();
        this.attachButton();
    }

    createModal() {
        const modalDiv = document.createElement('div');
        modalDiv.id = 'settings-modal';
        modalDiv.className = 'lorebook-modal hidden'; // reuse lorebook styles
        modalDiv.innerHTML = `
            <div class="lorebook-overlay"></div>
            <div class="lorebook-container" style="max-width:400px; height:auto; margin:auto; top:20%;">
                <div class="lorebook-header">
                    <span style="flex:1; text-align:center;">Settings</span>
                    <button class="lorebook-close" id="settings-close">✖</button>
                </div>
                <div class="lorebook-content" style="display:flex; flex-direction:column; gap:12px;">
                    <button id="settings-prompts-btn" class="lorebook-add-btn" style="background:#3c3f58; color:white;">Edit Prompts</button>
                    <button id="settings-llm-btn" class="lorebook-add-btn" style="background:#3c3f58; color:white;">LLM Parameters (coming soon)</button>
                    <button id="settings-ui-btn" class="lorebook-add-btn" style="background:#3c3f58; color:white;">UI Settings (coming soon)</button>
                </div>
            </div>
        `;
        document.body.appendChild(modalDiv);
        this.modal = modalDiv;

        modalDiv.querySelector('.lorebook-overlay').addEventListener('click', () => this.close());
        modalDiv.querySelector('#settings-close').addEventListener('click', () => this.close());
        modalDiv.querySelector('#settings-prompts-btn').addEventListener('click', () => {
            this.close();
            if (window.promptsModal) window.promptsModal.open();
        });
    }

    attachButton() {
        const btn = document.getElementById('settings-btn');
        if (btn) {
            btn.addEventListener('click', () => this.open());
        } else {
            console.warn('Settings button (#settings-btn) not found');
        }
    }

    open() {
        this.modal.classList.remove('hidden');
    }

    close() {
        this.modal.classList.add('hidden');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.settingsModal = new SettingsModal();
});