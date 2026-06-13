/**
 * Lorebook UI Module
 * Provides modal window with three tabs: Locations, Characters, Entries.
 * Uses REST API endpoints from backend/lorebook/router.py
 */

class LorebookUI {
    constructor() {
        this.baseUrl = '/lorebook';
        this.currentTab = 'locations';
        this.data = {
            locations: [],
            characters: [],
            entries: []
        };
        this.modal = null;
        this.init();
    }

    init() {
        this.createModal();
        this.attachGlobalButton();
    }

    createModal() {
        const modalDiv = document.createElement('div');
        modalDiv.id = 'lorebook-modal';
        modalDiv.className = 'lorebook-modal hidden';
        modalDiv.innerHTML = `
            <div class="lorebook-overlay"></div>
            <div class="lorebook-container">
                <div class="lorebook-header">
                    <button class="lorebook-tab" data-tab="locations">📌 Locations</button>
                    <button class="lorebook-tab" data-tab="characters">👥 Characters</button>
                    <button class="lorebook-tab" data-tab="entries">📄 Entries</button>
                    <button class="lorebook-close">✖</button>
                </div>
                <div class="lorebook-content">
                    <div class="lorebook-toolbar">
                        <button class="lorebook-add-btn">➕ Add</button>
                    </div>
                    <div class="lorebook-list" id="lorebook-list"></div>
                </div>
            </div>
        `;
        document.body.appendChild(modalDiv);
        this.modal = modalDiv;

        modalDiv.querySelectorAll('.lorebook-tab').forEach(btn => {
            btn.addEventListener('click', (e) => this.switchTab(e.target.dataset.tab));
        });
        modalDiv.querySelector('.lorebook-close').addEventListener('click', () => this.close());
        modalDiv.querySelector('.lorebook-add-btn').addEventListener('click', () => this.showEditForm());
        modalDiv.querySelector('.lorebook-overlay').addEventListener('click', () => this.close());

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen()) this.close();
        });
    }

    attachGlobalButton() {
        let btn = document.getElementById('open-lorebook-btn');
        if (!btn) {
            btn = document.createElement('button');
            btn.id = 'open-lorebook-btn';
            btn.textContent = '📖 Lorebook';
            btn.style.position = 'fixed';
            btn.style.bottom = '20px';
            btn.style.right = '20px';
            btn.style.zIndex = '1000';
            document.body.appendChild(btn);
        }
        btn.addEventListener('click', () => this.open());
    }

    async open() {
        await this.loadData();
        this.switchTab(this.currentTab);
        this.modal.classList.remove('hidden');
    }

    close() {
        this.modal.classList.add('hidden');
    }

    isOpen() {
        return !this.modal.classList.contains('hidden');
    }

    async loadData() {
        try {
            const [locations, characters, entries] = await Promise.all([
                fetch(`${this.baseUrl}/locations`).then(r => r.json()),
                fetch(`${this.baseUrl}/characters`).then(r => r.json()),
                fetch(`${this.baseUrl}/entries`).then(r => r.json())
            ]);
            this.data.locations = locations;
            this.data.characters = characters;
            this.data.entries = entries;
        } catch (err) {
            console.error('Failed to load lorebook data:', err);
            alert('Error loading lorebook');
        }
    }

    switchTab(tabId) {
        this.currentTab = tabId;
        this.modal.querySelectorAll('.lorebook-tab').forEach(btn => {
            if (btn.dataset.tab === tabId) btn.classList.add('active');
            else btn.classList.remove('active');
        });
        this.renderList();
    }

    renderList() {
        const container = this.modal.querySelector('#lorebook-list');
        const items = this.data[this.currentTab];
        if (!items || items.length === 0) {
            container.innerHTML = '<div class="lorebook-empty">No entries. Click "Add"</div>';
            return;
        }

        const sorted = [...items].sort((a,b) => (a.position||0) - (b.position||0));
        const html = sorted.map(item => this.renderItemCard(item)).join('');
        container.innerHTML = html;

        // Delete button (sync confirm for Firefox compatibility)
        container.querySelectorAll('.lorebook-delete-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const id = btn.dataset.id;
                if (!id) {
                    alert('Error: missing id');
                    return;
                }
                this.createCustomConfirm(
                    'Delete this entry?',
                    () => this.deleteItem(id).catch(err => alert('Delete error: ' + err.message)),
                    () => console.log('Delete cancelled')
                );
            });
        });

        // Edit button
        container.querySelectorAll('.lorebook-edit-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const id = btn.dataset.id;
                const original = items.find(i => i.id === id);
                if (original) this.showEditForm(original);
            });
        });
    }

    renderItemCard(item) {
        const title = item.name || item.title || 'Untitled';
        const stateIcon = {
            'always_active': '🟢',
            'activate_on_keyword': '🔑',
            'deactivated': '⚫'
        }[item.state] || '❓';
        return `
            <div class="lorebook-card" data-id="${item.id}">
                <div class="lorebook-card-header">
                    <span class="lorebook-card-title">${this.escapeHtml(title)}</span>
                    <span class="lorebook-card-state">${stateIcon}</span>
                </div>
                <div class="lorebook-card-preview">${this.escapeHtml(item.description?.substring(0, 80) || '')}...</div>
                <div class="lorebook-card-actions">
                    <button class="lorebook-edit-btn" data-id="${item.id}">✏️ Edit</button>
                    <button class="lorebook-delete-btn" data-id="${item.id}">🗑️ Delete</button>
                </div>
            </div>
        `;
    }

    async showEditForm(original = null) {
        const isEdit = !!original;
        const entityType = this.currentTab;
        const fields = this.getFieldsForType(entityType, original);

        const formHtml = `
            <div class="lorebook-form-overlay" id="lorebook-form-overlay">
                <div class="lorebook-form-container">
                    <h3>${isEdit ? 'Edit' : 'Create'} ${this.getTypeLabel(entityType)}</h3>
                    <form id="lorebook-form">
                        ${fields.map(f => this.renderFormField(f)).join('')}
                        <div class="form-actions">
                            <button type="submit">${isEdit ? 'Save' : 'Create'}</button>
                            <button type="button" id="lorebook-form-cancel">Cancel</button>
                        </div>
                    </form>
                </div>
            </div>
        `;

        const oldForm = document.getElementById('lorebook-form-overlay');
        if (oldForm) oldForm.remove();

        document.body.insertAdjacentHTML('beforeend', formHtml);
        const formOverlay = document.getElementById('lorebook-form-overlay');
        const form = document.getElementById('lorebook-form');

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const data = await this.collectFormData(form, entityType, isEdit, original);
            if (!data) return;
            try {
                if (isEdit) {
                    await this.updateItem(entityType, original.id, data);
                } else {
                    await this.createItem(entityType, data);
                }
                await this.loadData();
                this.renderList();
                formOverlay.remove();
            } catch (err) {
                alert('Error: ' + err.message);
            }
        });

        document.getElementById('lorebook-form-cancel').addEventListener('click', () => formOverlay.remove());
        formOverlay.addEventListener('click', (e) => { if (e.target === formOverlay) formOverlay.remove(); });
    }

    renderFormField(f) {
        const value = f.value ?? '';
        if (f.type === 'textarea') {
            return `<div class="form-group"><label>${f.label}</label><textarea name="${f.name}" rows="4">${this.escapeHtml(String(value))}</textarea></div>`;
        } else if (f.type === 'select') {
            const optionsHtml = f.options.map(opt => `<option value="${opt.value}" ${opt.value == value ? 'selected' : ''}>${this.escapeHtml(opt.label)}</option>`).join('');
            return `<div class="form-group"><label>${f.label}</label><select name="${f.name}">${optionsHtml}</select></div>`;
        } else if (f.type === 'checkbox-group') {
            const checkboxesHtml = f.options.map(opt => `
                <label>
                    <input type="checkbox" name="${f.name}" value="${opt.value}" ${(value || []).includes(opt.value) ? 'checked' : ''}>
                    ${this.escapeHtml(opt.label)}
                </label>
            `).join('');
            return `<div class="form-group"><label>${f.label}</label><div class="checkbox-group">${checkboxesHtml}</div></div>`;
        } else if (f.type === 'checkbox') {
            return `<div class="form-group"><label><input type="checkbox" name="${f.name}" ${value ? 'checked' : ''}> ${f.label}</label></div>`;
        } else {
            return `<div class="form-group"><label>${f.label}</label><input type="${f.type}" name="${f.name}" value="${this.escapeHtml(String(value))}" ${f.required ? 'required' : ''}></div>`;
        }
    }

    createCustomConfirm(message, onConfirm, onCancel) {
        const overlay = document.createElement('div');
        overlay.className = 'custom-confirm-overlay';

        overlay.innerHTML = `
            <div class="custom-confirm-dialog">
                <p>${this.escapeHtml(message)}</p>
                <div class="custom-confirm-actions">
                    <button class="confirm-yes">Yes</button>
                    <button class="confirm-no">Cancel</button>
                </div>
            </div>
        `;

        overlay.querySelector('.confirm-yes').onclick = () => {
            document.body.removeChild(overlay);
            if (onConfirm) onConfirm();
        };
        overlay.querySelector('.confirm-no').onclick = () => {
            document.body.removeChild(overlay);
            if (onCancel) onCancel();
        };

        document.body.appendChild(overlay);
    }

    async collectFormData(form, entityType, isEdit, original) {
        const formData = new FormData(form);
        const data = {};

        for (let [key, val] of formData.entries()) {
            if (key === 'keywords') {
                data[key] = val ? val.split(',').map(s => s.trim()).filter(s => s) : [];
            } else if (key === 'chance' || key === 'depth' || key === 'position') {
                data[key] = parseInt(val, 10) || 0;
            } else if (key === 'is_leaf') {
                continue;
            } else {
                data[key] = val;
            }
        }

        const isLeafCheckbox = form.querySelector('input[name="is_leaf"]');
        if (isLeafCheckbox) {
            data.is_leaf = isLeafCheckbox.checked;
        }

        const selectedChars = Array.from(form.querySelectorAll('input[name="characters_on_location"]:checked')).map(cb => cb.value);
        if (entityType === 'locations') {
            data.characters_on_location = selectedChars;
        }

        if (data.parent_id === '') data.parent_id = null;

        if (!isEdit) {
            if (entityType === 'characters' && !data.name) data.name = data.title || 'New character';
            if (!data.state) data.state = 'activate_on_keyword';
            if (!data.logic) data.logic = 'ANY';
            if (data.chance === undefined) data.chance = 100;
            if (data.depth === undefined) data.depth = 0;
        }
        return data;
    }

    getFieldsForType(type, original) {
        const baseFields = [
            { name: 'title', label: 'Title', type: 'text', required: true, value: original?.title || '' },
            { name: 'description', label: 'Description', type: 'textarea', value: original?.description || '' },
            { name: 'state', label: 'State', type: 'select', options: [
                { value: 'always_active', label: '🟢 Always active' },
                { value: 'activate_on_keyword', label: '🔑 Activate on keyword' },
                { value: 'deactivated', label: '⚫ Deactivated' }
            ], value: original?.state || 'activate_on_keyword' },
            { name: 'keywords', label: 'Keywords (comma separated)', type: 'text', value: (original?.keywords || []).join(', ') },
            { name: 'logic', label: 'Logic', type: 'select', options: [
                { value: 'ANY', label: 'ANY' },
                { value: 'ALL', label: 'ALL' }
            ], value: original?.logic || 'ANY' },
            { name: 'chance', label: 'Chance (0-100)', type: 'number', value: original?.chance ?? 100 },
            { name: 'depth', label: 'Depth (0-100)', type: 'number', value: original?.depth ?? 0 },
            { name: 'position', label: 'Position', type: 'number', value: original?.position ?? 0 }
        ];

        if (type === 'characters') {
            const nameField = { name: 'name', label: 'Character name', type: 'text', required: true, value: original?.name || '' };
            return [nameField, ...baseFields.filter(f => f.name !== 'title')];
        }

        if (type === 'locations') {
            const parentOptions = this.data.locations
                .filter(loc => loc.id !== original?.id)
                .map(loc => ({ value: loc.id, label: loc.title }));
            const characterOptions = this.data.characters.map(c => ({ value: c.id, label: c.name }));
            return [
                ...baseFields,
                { name: 'parent_id', label: 'Parent location', type: 'select', options: [{ value: '', label: '(none)' }, ...parentOptions], value: original?.parent_id || '' },
                { name: 'is_leaf', label: 'Leaf (cannot have children)', type: 'checkbox', value: original?.is_leaf || false },
                { name: 'characters_on_location', label: 'Characters on this location', type: 'checkbox-group', options: characterOptions, value: original?.characters_on_location || [] }
            ];
        }

        const locationOptions = this.data.locations.map(loc => ({ value: loc.id, label: loc.title }));
        return [
            ...baseFields,
            { name: 'parent_id', label: 'Linked location', type: 'select', options: [{ value: '', label: '(none)' }, ...locationOptions], value: original?.parent_id || '' }
        ];
    }

    getTypeLabel(type) {
        return { locations: 'location', characters: 'character', entries: 'entry' }[type];
    }

    async createItem(type, data) {
        const resp = await fetch(`${this.baseUrl}/${type}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!resp.ok) throw new Error(await resp.text());
        return resp.json();
    }

    async updateItem(type, id, data) {
        const resp = await fetch(`${this.baseUrl}/${type}/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!resp.ok) throw new Error(await resp.text());
        return resp.json();
    }

    async deleteItem(id) {
        try {
            const resp = await fetch(`${this.baseUrl}/${this.currentTab}/${id}`, { method: 'DELETE' });
            if (!resp.ok) {
                const text = await resp.text();
                throw new Error(text);
            }
            await this.loadData();
            this.renderList();
        } catch (err) {
            alert('Delete error: ' + err.message);
        }
    }

    escapeHtml(str) {
        if (str === undefined || str === null) return '';
        const s = String(str);
        return s.replace(/[&<>]/g, function(m) {
            if (m === '&') return '&amp;';
            if (m === '<') return '&lt;';
            if (m === '>') return '&gt;';
            return m;
        });
    }
}

// Initialize when DOM is ready
window.lorebookUI = new LorebookUI();