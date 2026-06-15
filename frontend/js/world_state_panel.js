/**
 * WorldStatePanel – UI panel for selecting location, character, and time.
 */
class WorldStatePanel {
    constructor() {
        this.container = null;
        this.locationSelect = null;
        this.characterSelect = null;
        this.timeInput = null;
        this.locations = [];
        this.characters = [];
        this.createPanel();
        this.loadData();
        this.loadCurrentState();
    }

    createPanel() {
        this.container = document.createElement('div');
        this.container.id = 'world-state-panel';
        this.container.style.cssText = `
            position: fixed;
            top: 60px;
            right: 20px;
            width: 260px;
            background: #3c3f58;
            border: 1px solid #707793;
            border-radius: 12px;
            padding: 12px;
            z-index: 1000;
            color: white;
            font-size: 14px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        `;
        this.container.innerHTML = `
            <div style="margin-bottom: 8px; font-weight: bold;">World State</div>
            <div style="margin-bottom: 8px;">
                <label>Location:</label>
                <select id="ws-location" style="width:100%; background:#2E3047; color:white;"></select>
            </div>
            <div style="margin-bottom: 8px;">
                <label>Active Character:</label>
                <select id="ws-character" style="width:100%; background:#2E3047; color:white;"></select>
            </div>
            <div style="margin-bottom: 8px;">
                <label>Time:</label>
                <input type="text" id="ws-time" placeholder="e.g., Morning" style="width:100%; background:#2E3047; color:white; border:1px solid #707793; border-radius:4px; padding:4px;">
            </div>
        `;
        document.body.appendChild(this.container);

        this.locationSelect = document.getElementById('ws-location');
        this.characterSelect = document.getElementById('ws-character');
        this.timeInput = document.getElementById('ws-time');
    }

    async loadData() {
        try {
            const [locationsRes, charactersRes] = await Promise.all([
                fetch('/lorebook/locations'),
                fetch('/lorebook/characters')
            ]);
            this.locations = await locationsRes.json();
            this.characters = await charactersRes.json();
            this.populateSelects();
        } catch (err) {
            console.error('Failed to load lorebook data for world state panel:', err);
        }
    }

    populateSelects() {
        // Location options
        this.locationSelect.innerHTML = '<option value="">(none)</option>';
        this.locations.forEach(loc => {
            const option = document.createElement('option');
            option.value = loc.id;
            option.textContent = loc.title || 'Unnamed';
            this.locationSelect.appendChild(option);
        });

        // Character options
        this.characterSelect.innerHTML = '<option value="">(none)</option>';
        this.characters.forEach(char => {
            const option = document.createElement('option');
            option.value = char.id;
            option.textContent = char.name || 'Unnamed';
            this.characterSelect.appendChild(option);
        });
    }

    async loadCurrentState() {
        try {
            const resp = await fetch('/api/world_state/current');
            const state = await resp.json();
            this.locationSelect.value = state.location_id || '';
            this.characterSelect.value = state.active_character_id || '';
            this.timeInput.value = state.time_string || '';
        } catch (err) {
            console.error('Failed to load current world state:', err);
        }
    }

    /**
     * Get the current world state from the UI.
     * @returns {object} World state object.
     */
    getCurrentState() {
        return {
            location_id: this.locationSelect.value || null,
            active_character_id: this.characterSelect.value || null,
            time_string: this.timeInput.value.trim() || null
        };
    }
}

// Initialize after DOM ready
document.addEventListener('DOMContentLoaded', () => {
    window.worldStatePanel = new WorldStatePanel();
});