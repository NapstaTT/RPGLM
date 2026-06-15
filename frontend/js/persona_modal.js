/**
 * PersonaModal – modal for editing user persona.
 */
class PersonaModal {
    constructor() {
        this.modal = null;
        this.createModal();
        this.attachButton();
    }

    createModal() {
        const modalDiv = document.createElement('div');
        modalDiv.id = 'persona-modal';
        modalDiv.className = 'lorebook-modal hidden';
        modalDiv.innerHTML = `
            <div class="lorebook-overlay"></div>
            <div class="lorebook-container" style="max-width:500px; height:auto; margin:auto; top:20%;">
                <div class="lorebook-header">
                    <span style="flex:1; text-align:center;">User Persona</span>
                    <button class="lorebook-close" id="persona-close">✖</button>
                </div>
                <div class="lorebook-content">
                    <form id="persona-form">
                        <div class="form-group">
                            <label>Name:</label>
                            <input type="text" name="name" required>
                        </div>
                        <div class="form-group">
                            <label>Description:</label>
                            <textarea name="description" rows="6"></textarea>
                            <small>Describes your character, appearance, backstory.</small>
                        </div>
                        <div class="form-actions">
                            <button type="submit">Save</button>
                            <button type="button" id="persona-cancel">Cancel</button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        document.body.appendChild(modalDiv);
        this.modal = modalDiv;
        modalDiv.querySelector('.lorebook-overlay').addEventListener('click', () => this.close());
        modalDiv.querySelector('#persona-close').addEventListener('click', () => this.close());
        modalDiv.querySelector('#persona-cancel').addEventListener('click', () => this.close());

        const form = modalDiv.querySelector('#persona-form');
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(form);
            const data = {
                name: formData.get('name'),
                description: formData.get('description'),
            };
            try {
                const resp = await fetch('/api/persona', {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                if (!resp.ok) throw new Error(await resp.text());
                // Update global name in chat.js
                if (window.updateUserName) window.updateUserName(data.name);
                this.close();
            } catch (err) {
                alert('Error saving persona: ' + err.message);
            }
        });
    }

    attachButton() {
        const btn = document.getElementById('persona-btn');
        if (btn) {
            btn.addEventListener('click', () => this.open());
        } else {
            console.warn('Persona button not found');
        }
    }

    async open() {
        try {
            const resp = await fetch('/api/persona');
            const persona = await resp.json();
            const form = this.modal.querySelector('#persona-form');
            form.querySelector('input[name="name"]').value = persona.name || '';
            form.querySelector('textarea[name="description"]').value = persona.description || '';
            this.modal.classList.remove('hidden');
        } catch (err) {
            alert('Failed to load persona: ' + err.message);
        }
    }

    close() {
        this.modal.classList.add('hidden');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.personaModal = new PersonaModal();
});