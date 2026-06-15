// frontend/js/prompts_modal.js
/**
 * PromptsModal – modal for editing LLM prompts and templates.
 */
class PromptsModal {
    constructor() {
        this.modal = null;
        this.currentTab = 'narrator';
        this.templates = {};
        this.prompts = {};
        this.createModal();
    }

    createModal() {
        const modalDiv = document.createElement('div');
        modalDiv.id = 'prompts-modal';
        modalDiv.className = 'lorebook-modal hidden';
        modalDiv.innerHTML = `
            <div class="lorebook-overlay"></div>
            <div class="lorebook-container" style="width:80%; max-width:900px; height:80%; margin:auto; top:10%;">
                <div class="lorebook-header">
                    <button class="lorebook-tab" data-tab="narrator">Narrator</button>
                    <button class="lorebook-tab" data-tab="character">Character</button>
                    <button class="lorebook-tab" data-tab="permutation">Permutation</button>
                    <button class="lorebook-close" id="prompts-close">✖</button>
                </div>
                <div class="lorebook-content">
                    <div id="prompts-editor"></div>
                    <div class="form-actions" style="margin-top:20px;">
                        <button id="prompts-save" class="lorebook-add-btn" style="background:#3BBA9C;">Save</button>
                        <button id="prompts-cancel" style="background:#707793; color:white; border:none; border-radius:20px; padding:6px 12px;">Cancel</button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modalDiv);
        this.modal = modalDiv;

        modalDiv.querySelector('.lorebook-overlay').addEventListener('click', () => this.close());
        modalDiv.querySelector('#prompts-close').addEventListener('click', () => this.close());
        modalDiv.querySelector('#prompts-cancel').addEventListener('click', () => this.close());
        modalDiv.querySelector('#prompts-save').addEventListener('click', () => this.save());

        // Tab switching
        modalDiv.querySelectorAll('.lorebook-tab').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });
    }

    async open() {
        await this.loadData();
        this.switchTab(this.currentTab);
        this.modal.classList.remove('hidden');
    }

    close() {
        this.modal.classList.add('hidden');
    }

    async loadData() {
        try {
            const resp = await fetch('/api/prompts');
            const data = await resp.json();
            this.templates = data.templates || {};
            this.prompts = data.prompts || {};
        } catch (err) {
            console.error('Failed to load prompts:', err);
            alert('Error loading prompts');
        }
    }

    /**
     * Switch active tab.
     * @param {string} tabId - Tab identifier.
     */
    switchTab(tabId) {
        this.currentTab = tabId;
        this.modal.querySelectorAll('.lorebook-tab').forEach(btn => {
            if (btn.dataset.tab === tabId) btn.classList.add('active');
            else btn.classList.remove('active');
        });
        this.renderEditor();
    }

    renderEditor() {
        const container = this.modal.querySelector('#prompts-editor');
        const template = this.templates[this.currentTab] || '';
        const prompt = this.prompts[this.currentTab] || '';
        container.innerHTML = `
            <div class="form-group">
                <label>Template (supports {{#if var}}...{{/if}} and {{var}}):</label>
                <textarea id="prompt-template" rows="12" style="width:100%; font-family:monospace;">${this.escapeHtml(template)}</textarea>
                <small>Use macros: {{system_prompt}}, {{user_persona}}, {{character_description}}, {{location_description}}, {{world_map}}, {{history}}, {{scenario}}</small>
            </div>
            <div class="form-group">
                <label>Main Prompt:</label>
                <textarea id="prompt-text" rows="6" style="width:100%;">${this.escapeHtml(prompt)}</textarea>
                <small>This will be appended after the template.</small>
            </div>
        `;
    }

    async save() {
        const template = this.modal.querySelector('#prompt-template').value;
        const prompt = this.modal.querySelector('#prompt-text').value;
        // Update local data
        this.templates[this.currentTab] = template;
        this.prompts[this.currentTab] = prompt;
        try {
            const resp = await fetch('/api/prompts', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    templates: this.templates,
                    prompts: this.prompts
                })
            });
            if (!resp.ok) throw new Error(await resp.text());
            alert('Prompts saved successfully');
            this.close();
        } catch (err) {
            alert('Error saving: ' + err.message);
        }
    }

    /**
     * Escape HTML special characters.
     * @param {string} str - Input string.
     * @returns {string} Escaped string.
     */
    escapeHtml(str) {
        if (!str) return '';
        return str.replace(/[&<>]/g, function(m) {
            if (m === '&') return '&amp;';
            if (m === '<') return '&lt;';
            if (m === '>') return '&gt;';
            return m;
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.promptsModal = new PromptsModal();
});