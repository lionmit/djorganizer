/* ============================================================
   DJOrganizer v19 — app.js
   Vanilla JS only. No frameworks.
   All dynamic HTML insertion uses the esc() sanitiser on every
   user-supplied or server-supplied value before embedding in
   innerHTML strings.
   ============================================================ */

'use strict';

// ── CSRF helper ──────────────────────────────────────────────
const csrf = (() => {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.content : '';
})();

function csrfHeaders() {
    return { 'Content-Type': 'application/json' };
}

function csrfBody(payload) {
    return JSON.stringify({ ...payload, csrf_token: csrf });
}

// ── State ────────────────────────────────────────────────────
let _allTracks   = [];   // full set from sessionStorage
let _filtered    = [];   // after filterTracks()
let _sortState   = { col: null, dir: 'none' };
let _configModalTrigger = null;

// ── Genre display names ──────────────────────────────────────
const GENRE_NAMES = {
    house:           'House',
    amapiano:        'Amapiano',
    afrobeats:       'Afrobeats',
    reggae_dancehall:'Reggae & Dancehall',
    hiphop:          'Hip-Hop & R&B',
    latin:           'Latin',
    bass_dnb_garage: 'Bass DnB & Garage',
    pop:             'Pop',
    funk_disco_soul: 'Funk Disco Soul',
    rock:            'Rock & Alternative',
    electronic:      'Electronic',
    classics:        'Classics',
    country:         'Country',
    israeli:         'Israeli & Mizrachi',
    arabic:          'Arabic & Middle Eastern',
    russian:         'Russian',
    kpop:            'K-Pop',
    jpop:            'J-Pop',
    bollywood:       'Bollywood & Desi',
    turkish:         'Turkish',
    tools:           'Tools & FX',
    inbox:           'INBOX',
};

function displayGenre(key) {
    return GENRE_NAMES[key] || key || '—';
}

// ── Energy helpers ───────────────────────────────────────────
const ENERGY_META = {
    Low:  { cls: 'low',  icon: '↓', label: 'Low'  },
    Mid:  { cls: 'mid',  icon: '—', label: 'Mid'  },
    High: { cls: 'high', icon: '↑', label: 'High' },
};

// ── Duration formatter ───────────────────────────────────────
function formatDuration(secs) {
    if (!secs && secs !== 0) return '—';
    const s = Math.round(Number(secs));
    const m = Math.floor(s / 60);
    const r = s % 60;
    return `${m}:${String(r).padStart(2, '0')}`;
}

// ── HTML escape (all user/server strings must pass through this) ──
function esc(str) {
    if (str === null || str === undefined) return '—';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// ── DOM creation helpers — avoid raw innerHTML where possible ──

/**
 * el(tag, attrs, ...children) — lightweight element factory.
 * @param {string} tag
 * @param {Object} attrs  — attributes/properties (class, textContent, etc.)
 * @param {...Node|string} children
 */
function el(tag, attrs, ...children) {
    const node = document.createElement(tag);
    if (attrs) {
        Object.entries(attrs).forEach(([k, v]) => {
            if (k === 'textContent') node.textContent = v;
            else if (k === 'className') node.className = v;
            else if (k === 'style') node.style.cssText = v;
            else if (k.startsWith('data-')) node.dataset[k.slice(5)] = v;
            else node.setAttribute(k, v);
        });
    }
    children.forEach(c => {
        if (c instanceof Node) node.appendChild(c);
        else if (c !== null && c !== undefined) node.appendChild(document.createTextNode(String(c)));
    });
    return node;
}

/** createEnergyBadge — builds the badge DOM node safely */
function createEnergyBadge(val) {
    const m = ENERGY_META[val] || { cls: 'mid', icon: '—', label: val || '—' };
    const span = el('span', {
        className: `energy-badge ${m.cls}`,
        'aria-label': `Energy: ${m.label}`,
    });
    const icon = el('span', { className: 'energy-icon', 'aria-hidden': 'true' }, m.icon);
    span.appendChild(icon);
    span.appendChild(document.createTextNode(m.label));
    return span;
}

/** createCleanBadge — returns a DOM node */
function createCleanBadge(val) {
    const v = String(val).toLowerCase();
    const isClean = (v === 'true' || v === 'yes' || v === '1');
    return el('span', {
        className: `clean-badge ${isClean ? 'clean' : 'explicit'}`,
        'aria-label': isClean ? 'Clean' : 'Explicit',
    }, isClean ? '✓ Clean' : 'E');
}

/* ============================================================
   WELCOME SCREEN
   ============================================================ */

(function initDropZone() {
    const zone    = document.getElementById('drop-zone');
    const input   = document.getElementById('folder-input');
    const pathIn  = document.getElementById('path-input');
    if (!zone) return;

    // Keyboard activation
    zone.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            if (input) input.click();
        }
    });

    // Drag events
    ['dragenter', 'dragover'].forEach(evt => {
        zone.addEventListener(evt, (e) => {
            e.preventDefault();
            e.stopPropagation();
            zone.classList.add('drag-over');
        });
    });
    ['dragleave', 'dragend'].forEach(evt => {
        zone.addEventListener(evt, () => zone.classList.remove('drag-over'));
    });
    zone.addEventListener('drop', (e) => {
        e.preventDefault();
        e.stopPropagation();
        zone.classList.remove('drag-over');

        const items = e.dataTransfer ? e.dataTransfer.items : null;
        if (items) {
            for (let i = 0; i < items.length; i++) {
                const entry = items[i].webkitGetAsEntry
                    ? items[i].webkitGetAsEntry() : null;
                if (entry && entry.isDirectory) {
                    const file = items[i].getAsFile();
                    if (file && file.path) { startScan(file.path); return; }
                }
            }
        }

        const files = e.dataTransfer ? e.dataTransfer.files : null;
        if (files && files.length > 0) {
            const f = files[0];
            if (f.path) {
                const slash = f.path.lastIndexOf('/');
                const dir   = slash > 0 ? f.path.substring(0, slash) : f.path;
                startScan(dir);
                return;
            }
        }
        showDropError('Could not read folder path. Please use Browse or type the path below.');
    });

    if (input) {
        input.addEventListener('change', () => {
            const files = input.files;
            if (!files || files.length === 0) return;
            const f = files[0];
            if (f.path) {
                const slash = f.path.lastIndexOf('/');
                const dir   = slash > 0 ? f.path.substring(0, slash) : f.path;
                startScan(dir);
            } else {
                showDropError(
                    'Browser security prevents reading the full folder path. ' +
                    'Please type or paste the absolute path below.'
                );
            }
        });
    }

    if (pathIn) {
        pathIn.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') startScanFromPath();
        });
    }
})();

function showDropError(msg) {
    let existing = document.getElementById('drop-error-msg');
    if (!existing) {
        existing = el('p', {
            'id': 'drop-error-msg',
            'role': 'alert',
            'style': 'color:var(--error);font-size:0.82rem;margin-top:0.5rem',
        });
        const zone = document.getElementById('drop-zone');
        if (zone) zone.appendChild(existing);
    }
    existing.textContent = msg;
}

function startScanFromPath() {
    const input = document.getElementById('path-input');
    if (!input) return;
    const path = input.value.trim();
    if (!path) { input.focus(); return; }
    startScan(path);
}

/**
 * startScan — POST to /api/scan, consume SSE stream, update progress.
 * On 'complete' stores tracks in sessionStorage and navigates to /preview.
 */
function startScan(path) {
    if (!path) return;
    showState('scanning');

    const progressFill = document.getElementById('scan-progress-fill');
    const progressBar  = document.getElementById('scan-progress-bar');
    const countText    = document.getElementById('scan-count-text');
    const percentEl    = document.getElementById('scan-percent');
    const liveTrack    = document.getElementById('live-track');
    const liveGenre    = document.getElementById('live-genre');

    fetch('/api/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path, csrf_token: csrf }),
    }).then(response => {
        if (!response.ok) {
            return response.json().then(d => {
                throw new Error(d.error || 'Scan failed');
            });
        }
        const reader  = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        function read() {
            reader.read().then(({ done, value }) => {
                if (done) return;
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop();

                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue;
                    try {
                        const evt = JSON.parse(line.slice(6));
                        handleScanEvent(evt);
                    } catch (_) { /* skip malformed */ }
                }
                read();
            }).catch(err => showScanError('Stream error: ' + err.message));
        }
        read();
    }).catch(err => showScanError(err.message));

    function handleScanEvent(evt) {
        if (evt.type === 'progress') {
            const pct = Math.round((evt.current / evt.total) * 100);
            if (progressFill) progressFill.style.width = pct + '%';
            if (progressBar) progressBar.setAttribute('aria-valuenow', pct);
            if (percentEl)   percentEl.textContent = pct + '%';
            if (countText)   countText.textContent = `Scanning ${evt.current} of ${evt.total} tracks\u2026`;
            // Use textContent only — evt.latest is a filename string
            if (liveTrack)   liveTrack.textContent = evt.latest || '';
            if (liveGenre)   liveGenre.textContent = '';
        } else if (evt.type === 'complete') {
            try {
                sessionStorage.setItem('dj_tracks', JSON.stringify(evt.tracks));
                sessionStorage.setItem('dj_source_path', evt.source_path || '');
                sessionStorage.setItem('dj_active_locales', JSON.stringify(evt.active_locales || []));
            } catch (e) {
                console.warn('sessionStorage write failed:', e);
            }
            window.location.href = '/preview';
        }
    }
}

function showScanError(msg) {
    showState('welcome');
    showDropError('Scan error: ' + msg);
}

function showState(state) {
    const welcome  = document.getElementById('welcome-state');
    const scanning = document.getElementById('scanning-state');
    if (!welcome || !scanning) return;
    if (state === 'scanning') {
        welcome.classList.add('hidden');
        scanning.classList.remove('hidden');
        scanning.removeAttribute('hidden');
    } else {
        scanning.classList.add('hidden');
        welcome.classList.remove('hidden');
    }
}

/* ============================================================
   PREVIEW SCREEN
   ============================================================ */

function initPreview() {
    let tracks = [];
    try {
        const raw = sessionStorage.getItem('dj_tracks');
        if (raw) tracks = JSON.parse(raw);
    } catch (_) {}

    // Attach original index before any sorting/filtering
    tracks.forEach((t, i) => { t._origIndex = i; });

    _allTracks = tracks;
    _filtered  = [...tracks];

    updateTrackCountLabel(tracks.length, tracks.length);
    populateFilterOptions(tracks);
    renderTable(tracks);

    const cfgOutPath = window.DJCONFIG && window.DJCONFIG.output_folder;
    const outInput   = document.getElementById('output-path-input');
    if (outInput && cfgOutPath) outInput.value = cfgOutPath;

    const copySelect = document.getElementById('copy-mode-select');
    if (copySelect && window.DJCONFIG && window.DJCONFIG.copy_mode === 'false') {
        copySelect.value = 'false';
    }
}

function updateTrackCountLabel(visible, total) {
    const labelEl = document.getElementById('track-count-label');
    if (!labelEl) return;
    labelEl.textContent = visible === total
        ? `${total} track${total !== 1 ? 's' : ''} found`
        : `Showing ${visible} of ${total} tracks`;
}

/**
 * renderTable — build DOM rows for 12 visible columns.
 * date_added / era are CSV-only.
 */
function renderTable(tracks) {
    const tbody = document.getElementById('tracks-tbody');
    if (!tbody) return;

    tbody.innerHTML = '';

    if (!tracks || tracks.length === 0) {
        const tr = document.createElement('tr');
        const td = el('td', { colspan: '13', style: 'padding:3rem 1rem;text-align:center;color:var(--text-muted)' });
        const icon = el('span', { style: 'font-size:1.5rem;display:block;margin-bottom:0.5rem', 'aria-hidden': 'true' }, '\uD83D\uDD0D');
        const msg  = el('p', { style: 'color:var(--text-muted)' }, 'No tracks match the current filters.');
        td.appendChild(icon);
        td.appendChild(msg);
        tr.appendChild(td);
        tbody.appendChild(tr);
        return;
    }

    const fragment = document.createDocumentFragment();

    tracks.forEach((t) => {
        const origIdx = t._origIndex ?? 0;
        const tr = document.createElement('tr');
        tr.setAttribute('data-index', origIdx);

        // Row number
        tr.appendChild(el('td', { style: 'color:var(--text-muted);font-size:0.78rem' }, String(origIdx + 1)));

        // Title
        const titleTd = el('td', { title: t.title || '', style: 'font-weight:600' });
        titleTd.textContent = t.title || '—';
        tr.appendChild(titleTd);

        // Artist
        const artistTd = el('td', { title: t.artist || '' });
        artistTd.textContent = t.artist || '—';
        tr.appendChild(artistTd);

        // Genre (clickable badge)
        const genreLabel = displayGenre(t.genre);
        const genreSpan  = el('span', {
            className: 'genre-badge',
            tabindex: '0',
            role: 'button',
            'aria-label': `Genre: ${genreLabel}. Press Enter to change.`,
        }, genreLabel);
        genreSpan.addEventListener('click', () => openGenreOverride(genreSpan, origIdx));
        genreSpan.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openGenreOverride(genreSpan, origIdx); }
        });
        const genreTd = document.createElement('td');
        genreTd.appendChild(genreSpan);
        tr.appendChild(genreTd);

        // Energy (clickable badge)
        const energyBadgeNode = createEnergyBadge(t.energy);
        const energyWrapper   = el('span', {
            tabindex: '0',
            role: 'button',
            'aria-label': `Energy: ${t.energy || 'Mid'}. Press Enter to change.`,
        });
        energyWrapper.appendChild(energyBadgeNode);
        energyWrapper.addEventListener('click', () => openEnergyOverride(energyWrapper, origIdx));
        energyWrapper.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openEnergyOverride(energyWrapper, origIdx); }
        });
        const energyTd = document.createElement('td');
        energyTd.appendChild(energyWrapper);
        tr.appendChild(energyTd);

        // Clean
        const cleanTd = document.createElement('td');
        cleanTd.appendChild(createCleanBadge(t.clean));
        tr.appendChild(cleanTd);

        // BPM
        tr.appendChild(el('td', {}, t.bpm ? String(Math.round(t.bpm)) : '—'));

        // Key
        const keyTd = el('td', {}); keyTd.textContent = t.key || '—'; tr.appendChild(keyTd);

        // Mix type
        const mixTd = el('td', {}); mixTd.textContent = t.mix_type || '—'; tr.appendChild(mixTd);

        // Year
        tr.appendChild(el('td', {}, t.year ? String(t.year) : '—'));

        // Language
        const langTd = el('td', {}); langTd.textContent = t.language || '—'; tr.appendChild(langTd);

        // Vocal
        const vocalTd = el('td', {}); vocalTd.textContent = t.vocal_type || '—'; tr.appendChild(vocalTd);

        // Duration
        tr.appendChild(el('td', {}, formatDuration(t.duration)));

        fragment.appendChild(tr);
    });

    tbody.appendChild(fragment);
}

// ── Inline genre override ────────────────────────────────────
function openGenreOverride(spanEl, trackIndex) {
    const existing = spanEl.parentNode.querySelector('.inline-select');
    if (existing) { existing.remove(); spanEl.style.display = ''; return; }

    spanEl.style.display = 'none';
    const sel = el('select', { className: 'inline-select', 'aria-label': 'Override genre' });

    Object.entries(GENRE_NAMES).forEach(([k, v]) => {
        const opt = el('option', { value: k }, v);
        if (k === (_allTracks[trackIndex] || {}).genre) opt.selected = true;
        sel.appendChild(opt);
    });

    sel.addEventListener('change', () => {
        overrideTag(trackIndex, 'genre', sel.value);
        spanEl.textContent = displayGenre(sel.value);
        sel.remove();
        spanEl.style.display = '';
    });
    sel.addEventListener('blur', () => { sel.remove(); spanEl.style.display = ''; });
    spanEl.parentNode.appendChild(sel);
    sel.focus();
}

// ── Inline energy override ───────────────────────────────────
function openEnergyOverride(wrapperEl, trackIndex) {
    const existing = wrapperEl.parentNode.querySelector('.inline-select');
    if (existing) { existing.remove(); wrapperEl.style.display = ''; return; }

    wrapperEl.style.display = 'none';
    const sel = el('select', { className: 'inline-select', 'aria-label': 'Override energy' });

    ['Low', 'Mid', 'High'].forEach(v => {
        const opt = el('option', { value: v }, v);
        if (v === (_allTracks[trackIndex] || {}).energy) opt.selected = true;
        sel.appendChild(opt);
    });

    sel.addEventListener('change', () => {
        overrideTag(trackIndex, 'energy', sel.value);
        wrapperEl.innerHTML = '';
        wrapperEl.appendChild(createEnergyBadge(sel.value));
        sel.remove();
        wrapperEl.style.display = '';
    });
    sel.addEventListener('blur', () => { sel.remove(); wrapperEl.style.display = ''; });
    wrapperEl.parentNode.appendChild(sel);
    sel.focus();
}

/**
 * overrideTag — update a single track's tag in _allTracks memory.
 */
function overrideTag(trackIndex, tag, value) {
    if (_allTracks[trackIndex]) {
        _allTracks[trackIndex][tag] = value;
        try { sessionStorage.setItem('dj_tracks', JSON.stringify(_allTracks)); } catch (_) {}
    }
}

// ── Column sort ──────────────────────────────────────────────
function sortColumn(col) {
    if (_sortState.col === col) {
        if (_sortState.dir === 'none')            _sortState.dir = 'ascending';
        else if (_sortState.dir === 'ascending')  _sortState.dir = 'descending';
        else                                       _sortState.dir = 'none';
    } else {
        _sortState.col = col;
        _sortState.dir = 'ascending';
    }

    document.querySelectorAll('#tracks-table th.sortable').forEach(th => {
        const thCol = (th.getAttribute('onclick') || '').match(/sortColumn\('(\w+)'\)/)?.[1];
        th.setAttribute('aria-sort', thCol === col && _sortState.dir !== 'none' ? _sortState.dir : 'none');
    });

    if (_sortState.dir === 'none') {
        applyFilters();
        return;
    }

    const dir = _sortState.dir === 'ascending' ? 1 : -1;
    _filtered.sort((a, b) => {
        let va = a[col], vb = b[col];
        if (col === 'bpm' || col === 'year' || col === 'duration') {
            return (Number(va) || 0 - (Number(vb) || 0)) * dir;
        }
        if (col === 'energy') {
            const order = { Low: 0, Mid: 1, High: 2 };
            return ((order[va] ?? 1) - (order[vb] ?? 1)) * dir;
        }
        if (col === 'clean') {
            const t2n = v => (String(v).toLowerCase() === 'true' ? 1 : 0);
            return (t2n(va) - t2n(vb)) * dir;
        }
        va = String(va || '').toLowerCase();
        vb = String(vb || '').toLowerCase();
        return va < vb ? -dir : va > vb ? dir : 0;
    });

    renderTable(_filtered);
    updateTrackCountLabel(_filtered.length, _allTracks.length);
}

// ── Filter dropdowns ─────────────────────────────────────────
function populateFilterOptions(tracks) {
    const genres    = [...new Set(tracks.map(t => t.genre).filter(Boolean))].sort();
    const languages = [...new Set(tracks.map(t => t.language).filter(Boolean))].sort();

    const genreSel = document.getElementById('filter-genre');
    const langSel  = document.getElementById('filter-lang');

    if (genreSel) {
        genres.forEach(g => {
            genreSel.appendChild(el('option', { value: g }, displayGenre(g)));
        });
    }
    if (langSel) {
        languages.forEach(l => {
            langSel.appendChild(el('option', { value: l }, l));
        });
    }
}

/**
 * filterTracks — pure filter returning a subset of _allTracks
 */
function filterTracks(filters) {
    return _allTracks.filter(t => {
        if (filters.genre    && t.genre    !== filters.genre)    return false;
        if (filters.energy   && t.energy   !== filters.energy)   return false;
        if (filters.language && t.language !== filters.language) return false;
        if (filters.clean !== '') {
            const c = String(t.clean).toLowerCase();
            const isClean = (c === 'true' || c === 'yes' || c === '1');
            if (filters.clean === 'true'  && !isClean) return false;
            if (filters.clean === 'false' && isClean)  return false;
        }
        const yr = Number(t.year);
        if (filters.yearFrom && yr && yr < Number(filters.yearFrom)) return false;
        if (filters.yearTo   && yr && yr > Number(filters.yearTo))   return false;
        return true;
    });
}

function applyFilters() {
    const filters = {
        genre:    document.getElementById('filter-genre')?.value    || '',
        energy:   document.getElementById('filter-energy')?.value   || '',
        clean:    document.getElementById('filter-clean')?.value    ?? '',
        language: document.getElementById('filter-lang')?.value     || '',
        yearFrom: document.getElementById('filter-year-from')?.value || '',
        yearTo:   document.getElementById('filter-year-to')?.value   || '',
    };

    _filtered = filterTracks(filters);

    if (_sortState.col && _sortState.dir !== 'none') {
        const savedDir = _sortState.dir;
        const savedCol = _sortState.col;
        _sortState.col = null; // force re-sort
        _sortState.dir = 'none';
        sortColumn(savedCol);
        _sortState.dir = savedDir; // restore state
    } else {
        renderTable(_filtered);
    }

    updateTrackCountLabel(_filtered.length, _allTracks.length);
}

function resetFilters() {
    ['filter-genre','filter-energy','filter-clean','filter-lang','filter-year-from','filter-year-to']
        .forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
    _filtered  = [..._allTracks];
    _sortState = { col: null, dir: 'none' };
    document.querySelectorAll('#tracks-table th.sortable').forEach(th => th.setAttribute('aria-sort', 'none'));
    renderTable(_filtered);
    updateTrackCountLabel(_filtered.length, _allTracks.length);
}

// ── View toggle ──────────────────────────────────────────────
function switchView(view) {
    const tablePanel = document.getElementById('view-table');
    const dashPanel  = document.getElementById('view-dashboard');
    const tabTable   = document.getElementById('tab-table');
    const tabDash    = document.getElementById('tab-dashboard');

    if (view === 'table') {
        tablePanel?.classList.remove('hidden');
        dashPanel?.classList.add('hidden');
        tabTable?.classList.add('active');
        tabDash?.classList.remove('active');
        tabTable?.setAttribute('aria-selected', 'true');
        tabDash?.setAttribute('aria-selected', 'false');
    } else {
        tablePanel?.classList.add('hidden');
        dashPanel?.classList.remove('hidden');
        tabTable?.classList.remove('active');
        tabDash?.classList.add('active');
        tabTable?.setAttribute('aria-selected', 'false');
        tabDash?.setAttribute('aria-selected', 'true');
        renderDashboard(_allTracks);
    }
}

/* ============================================================
   DASHBOARD
   ============================================================ */

let _dashRendered = false;

function renderDashboard(tracks) {
    if (_dashRendered) return;
    _dashRendered = true;

    // 1. Genre distribution
    const genreCounts = {};
    tracks.forEach(t => { if (t.genre) genreCounts[t.genre] = (genreCounts[t.genre] || 0) + 1; });
    const genreEntries = Object.entries(genreCounts).sort((a, b) => b[1] - a[1]);
    drawBarChart(
        'genre-chart',
        genreEntries.map(([k]) => displayGenre(k)),
        genreEntries.map(([, v]) => v),
        '#0EA5E9'
    );
    fillChartTable('genre-chart-data-table', genreEntries.map(([k, v]) => [displayGenre(k), v]));

    // 2. Energy spread
    const energyCounts = { Low: 0, Mid: 0, High: 0 };
    tracks.forEach(t => { if (t.energy in energyCounts) energyCounts[t.energy]++; });
    drawBarChart(
        'energy-chart',
        Object.keys(energyCounts),
        Object.values(energyCounts),
        ['#60A5FA', '#34D399', '#F87171']
    );
    fillChartTable('energy-chart-data-table', Object.entries(energyCounts).map(([k, v]) => [k, v]));

    // 3. Year timeline
    const yearCounts = {};
    const currentYear = new Date().getFullYear();
    tracks.forEach(t => {
        const yr = Number(t.year);
        if (yr && yr > 1950 && yr <= currentYear + 1) {
            yearCounts[yr] = (yearCounts[yr] || 0) + 1;
        }
    });
    const yearEntries = Object.entries(yearCounts).sort((a, b) => Number(a[0]) - Number(b[0]));
    drawBarChart(
        'year-chart',
        yearEntries.map(([k]) => k),
        yearEntries.map(([, v]) => v),
        '#FBBF24'
    );
    fillChartTable('year-chart-data-table', yearEntries.map(([k, v]) => [k, v]));

    // 4. Gap alerts
    renderGapAlerts(tracks, genreCounts);
}

function drawBarChart(canvasId, labels, values, colors) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr  = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    const W    = Math.max(rect.width || 340, 200);
    const H    = 200;

    canvas.width  = W * dpr;
    canvas.height = H * dpr;
    canvas.style.width  = W + 'px';
    canvas.style.height = H + 'px';
    ctx.scale(dpr, dpr);

    const pad   = { top: 20, right: 12, bottom: 40, left: 36 };
    const cW    = W - pad.left - pad.right;
    const cH    = H - pad.top  - pad.bottom;
    const n     = labels.length;
    const maxV  = Math.max(...values, 1);

    ctx.clearRect(0, 0, W, H);

    // Gridlines + Y labels
    ctx.lineWidth = 1;
    const ticks = 4;
    for (let i = 0; i <= ticks; i++) {
        const y   = pad.top + cH - (i / ticks) * cH;
        const val = Math.round((i / ticks) * maxV);
        ctx.strokeStyle = 'rgba(51,65,85,0.7)';
        ctx.beginPath();
        ctx.moveTo(pad.left, y);
        ctx.lineTo(pad.left + cW, y);
        ctx.stroke();

        ctx.fillStyle  = '#94A3B8';
        ctx.font       = '10px "Space Grotesk", system-ui, sans-serif';
        ctx.textAlign  = 'right';
        ctx.textBaseline = 'middle';
        ctx.fillText(String(val), pad.left - 4, y);
    }

    // Bars
    const gapW = cW / Math.max(n, 1);
    const barW = Math.min(gapW - 4, 48);

    labels.forEach((label, i) => {
        const v    = values[i] || 0;
        const barH = (v / maxV) * cH;
        const x    = pad.left + i * gapW + (gapW - barW) / 2;
        const y    = pad.top + cH - barH;

        const color = Array.isArray(colors) ? colors[i % colors.length] : colors;
        ctx.fillStyle = color;

        const r = Math.min(4, barH / 2, barW / 2);
        if (barH > 0) {
            ctx.beginPath();
            ctx.moveTo(x + r, y);
            ctx.lineTo(x + barW - r, y);
            ctx.quadraticCurveTo(x + barW, y, x + barW, y + r);
            ctx.lineTo(x + barW, y + barH);
            ctx.lineTo(x, y + barH);
            ctx.lineTo(x, y + r);
            ctx.quadraticCurveTo(x, y, x + r, y);
            ctx.closePath();
            ctx.fill();
        }

        // Value label above bar
        if (v > 0) {
            ctx.fillStyle    = '#E2E8F0';
            ctx.font         = '10px "Space Grotesk", system-ui, sans-serif';
            ctx.textAlign    = 'center';
            ctx.textBaseline = 'bottom';
            ctx.fillText(String(v), x + barW / 2, Math.max(y - 2, pad.top + 10));
        }

        // X axis label (safe — displayGenre() returns only ASCII/known strings)
        const rawLabel = String(label);
        const xLabel   = rawLabel.length > 8 ? rawLabel.substring(0, 7) + '\u2026' : rawLabel;
        ctx.fillStyle    = '#94A3B8';
        ctx.font         = '9px "Space Grotesk", system-ui, sans-serif';
        ctx.textAlign    = 'center';
        ctx.textBaseline = 'top';
        ctx.fillText(xLabel, x + barW / 2, H - pad.bottom + 6);
    });
}

/**
 * fillChartTable — populate a data table with [label, value] pairs.
 * Uses DOM methods only — no innerHTML on user data.
 */
function fillChartTable(tableId, rows) {
    const tbody = document.querySelector(`#${tableId} tbody`);
    if (!tbody) return;
    tbody.innerHTML = '';
    const frag = document.createDocumentFragment();
    rows.forEach(([k, v]) => {
        const tr = document.createElement('tr');
        const td1 = document.createElement('td');
        const td2 = document.createElement('td');
        td1.textContent = k;
        td2.textContent = v;
        tr.appendChild(td1);
        tr.appendChild(td2);
        frag.appendChild(tr);
    });
    tbody.appendChild(frag);
}

function renderGapAlerts(tracks, genreCounts) {
    const area = document.getElementById('gap-alerts-area');
    if (!area) return;

    const alerts  = [];
    const total   = tracks.length || 1;
    const unclass = (genreCounts['inbox'] || 0) + tracks.filter(t => !t.genre).length;

    if (unclass > 0) {
        const pct = Math.round((unclass / total) * 100);
        alerts.push(`${unclass} track${unclass !== 1 ? 's' : ''} (${pct}%) could not be classified — they landed in INBOX.`);
    }

    const highCount = tracks.filter(t => t.energy === 'High').length;
    if (total >= 10 && highCount / total > 0.6) {
        alerts.push('Over 60% of your tracks are High energy. Consider adding Low/Mid tracks for versatile sets.');
    }

    const noBpm = tracks.filter(t => !t.bpm).length;
    if (total >= 10 && noBpm > total * 0.3) {
        alerts.push(`${noBpm} tracks have no BPM data — mixing accuracy may be affected.`);
    }

    const usedGenres = Object.keys(genreCounts).length;
    if (usedGenres === 1 && total > 20) {
        alerts.push('All tracks are in one genre. Consider adding variety for more flexible sets.');
    }

    area.innerHTML = '';
    if (alerts.length === 0) {
        const div = el('div', {
            className: 'no-gaps',
            role: 'status',
            'aria-live': 'polite',
        });
        div.textContent = '\u2705 No gaps detected \u2014 your library looks well-balanced.';
        area.appendChild(div);
    } else {
        alerts.forEach(msg => {
            const wrapper = el('div', { className: 'gap-alert', role: 'note' });
            const icon    = el('span', { className: 'gap-alert-icon', 'aria-hidden': 'true' }, '\u26A0\uFE0F');
            const p       = el('p', {}, msg); // msg is generated from safe numeric/counted strings
            wrapper.appendChild(icon);
            wrapper.appendChild(p);
            area.appendChild(wrapper);
        });
    }
}

/**
 * showChartAsTable — toggle chart canvas ↔ data table for accessibility.
 */
function showChartAsTable(chartId) {
    const canvas    = document.getElementById(chartId);
    const tableDiv  = document.getElementById(chartId + '-table');
    const toggleBtn = document.getElementById(chartId + '-toggle');
    if (!canvas || !tableDiv) return;

    const isTableNowVisible = !tableDiv.hidden;
    tableDiv.hidden = isTableNowVisible;
    canvas.hidden   = !isTableNowVisible;

    if (toggleBtn) {
        toggleBtn.textContent = isTableNowVisible ? 'Show as table' : 'Show as chart';
        toggleBtn.setAttribute('aria-pressed', String(!isTableNowVisible));
    }
}

/* ============================================================
   API ACTIONS
   ============================================================ */

function sortFiles() {
    const tracks = _allTracks.length ? _allTracks : (() => {
        try { return JSON.parse(sessionStorage.getItem('dj_tracks') || '[]'); } catch { return []; }
    })();

    const sourcePath = sessionStorage.getItem('dj_source_path') || '';
    const outInput   = document.getElementById('output-path-input');
    const copySelect = document.getElementById('copy-mode-select');
    const outputPath = (outInput?.value?.trim()) || sourcePath;
    const copyMode   = copySelect ? copySelect.value === 'true' : true;
    const suffixSel  = document.getElementById('cfg-suffix');
    const filenameSuffix = suffixSel ? suffixSel.value === 'true' : false;

    if (!outputPath) {
        alert('Please enter an output folder path before sorting.');
        outInput?.focus();
        return;
    }

    const sortBtn = document.getElementById('sort-btn');
    if (sortBtn) { sortBtn.disabled = true; sortBtn.textContent = 'Sorting\u2026'; }

    fetch('/api/sort', {
        method: 'POST',
        headers: csrfHeaders(),
        body: csrfBody({ tracks, output_path: outputPath, copy_mode: copyMode, filename_suffix: filenameSuffix }),
    })
    .then(r => r.json())
    .then(data => {
        if (data.error) throw new Error(data.error);
        try {
            sessionStorage.setItem('dj_results', JSON.stringify({
                moved:       data.moved,
                errors:      data.errors || [],
                copy_mode:   data.copy_mode,
                output_path: outputPath,
                tracks,
            }));
        } catch (_) {}
        window.location.href = '/results';
    })
    .catch(err => {
        if (sortBtn) { sortBtn.disabled = false; sortBtn.textContent = 'Sort Files'; }
        alert('Sort failed: ' + err.message);
    });
}

function exportCSV() {
    const tracks     = _allTracks.length ? _allTracks : (() => {
        try { return JSON.parse(sessionStorage.getItem('dj_tracks') || '[]'); } catch { return []; }
    })();
    const sourcePath = sessionStorage.getItem('dj_source_path') || '';

    fetch('/api/export-csv', {
        method: 'POST',
        headers: csrfHeaders(),
        body: csrfBody({ tracks, source_path: sourcePath }),
    })
    .then(r => r.json())
    .then(data => {
        if (data.error) throw new Error(data.error);
        const toast = el('div', {
            role: 'status',
            'aria-live': 'polite',
            style: 'position:fixed;bottom:1rem;right:1rem;background:var(--navy-light);border:1px solid var(--navy-border);border-radius:8px;padding:0.75rem 1rem;font-size:0.85rem;z-index:300;max-width:320px',
        });
        const strong = el('strong', { style: 'color:var(--success)' }, 'CSV exported');
        const path   = el('span', { style: 'color:var(--text-muted);font-size:0.78rem;display:block' });
        path.textContent = data.csv_path || '';
        toast.appendChild(strong);
        toast.appendChild(path);
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 4000);
    })
    .catch(err => alert('Export failed: ' + err.message));
}

function undoSort() {
    if (!confirm('This will undo the last sort and restore files to their original locations. Continue?')) return;

    fetch('/api/undo', {
        method: 'POST',
        headers: csrfHeaders(),
        body: csrfBody({}),
    })
    .then(r => r.json())
    .then(data => {
        if (data.error) throw new Error(data.error);
        const skippedMsg = data.skipped ? `, ${data.skipped} skipped` : '';
        alert(`Undo complete \u2014 ${data.reverted} file${data.reverted !== 1 ? 's' : ''} restored${skippedMsg}.`);
        if (window.location.pathname === '/results') {
            window.location.href = '/';
        } else {
            // Remove undo button section from welcome screen
            const undoBtn = document.querySelector('[onclick="undoSort()"]');
            undoBtn?.closest('div')?.remove();
        }
    })
    .catch(err => alert('Undo failed: ' + err.message));
}

/* ============================================================
   RESULTS SCREEN
   ============================================================ */

function initResults() {
    let results = null;
    try { results = JSON.parse(sessionStorage.getItem('dj_results') || 'null'); } catch (_) {}

    if (!results) {
        document.querySelector('.results-hero')?.setAttribute('hidden', '');
        document.querySelector('.stats-row')?.setAttribute('hidden', '');
        document.getElementById('copy-mode-notice')?.setAttribute('hidden', '');
        document.querySelector('.action-row')?.setAttribute('hidden', '');
        document.querySelector('.divider')?.setAttribute('hidden', '');
        document.getElementById('no-results-state')?.removeAttribute('hidden');
        return;
    }

    const moved        = results.moved || 0;
    const tracks       = results.tracks || [];
    const genresUsed   = new Set(tracks.filter(t => t.genre && t.genre !== 'inbox').map(t => t.genre)).size;
    const unclassified = tracks.filter(t => !t.genre || t.genre === 'inbox').length;
    const errCount     = (results.errors || []).length;

    const iconEl   = document.getElementById('results-icon');
    const headline = document.getElementById('results-headline');
    const sub      = document.getElementById('results-sub');

    if (iconEl)   iconEl.textContent   = errCount > 0 ? '\u26A0\uFE0F' : '\u2705';
    if (headline) headline.textContent = errCount > 0
        ? `Sort done \u2014 ${errCount} error${errCount !== 1 ? 's' : ''}`
        : 'Sort complete!';
    if (sub) sub.textContent = `${moved} file${moved !== 1 ? 's' : ''} sorted into ${genresUsed} genre folder${genresUsed !== 1 ? 's' : ''}.`;

    setStatText('stat-total',        moved);
    setStatText('stat-genres',       genresUsed);
    setStatText('stat-unclassified', unclassified);
    setStatText('stat-errors',       errCount);

    // Copy/move notice
    const notice = document.getElementById('copy-mode-notice');
    const text   = document.getElementById('copy-mode-text');
    if (notice && text) {
        if (results.copy_mode) {
            notice.className = 'copy-mode-notice copy';
            text.textContent = 'Files were copied \u2014 originals are preserved in their original location.';
        } else {
            notice.className = 'copy-mode-notice move';
            text.textContent = 'Files were moved \u2014 originals have been relocated to the genre folders.';
        }
    }

    // Error list
    if (errCount > 0) {
        const section = document.getElementById('error-section');
        const label   = document.getElementById('error-summary-label');
        const list    = document.getElementById('error-list');

        if (section) section.removeAttribute('hidden');
        if (label)   label.textContent = `${errCount} error${errCount !== 1 ? 's' : ''} during sort`;

        if (list) {
            list.innerHTML = '';
            const frag = document.createDocumentFragment();
            (results.errors || []).forEach(e => {
                const item     = el('div', { className: 'error-item', role: 'listitem' });
                const fileName = String(e.file || '').split('/').pop() || e.file || '';
                const fname    = el('div', { className: 'error-filename' });
                const emsg     = el('div', { className: 'error-msg' });
                fname.textContent = fileName;
                emsg.textContent  = e.error || 'Unknown error';
                item.appendChild(fname);
                item.appendChild(emsg);
                frag.appendChild(item);
            });
            list.appendChild(frag);
        }
    }
}

function setStatText(id, val) {
    const statEl = document.getElementById(id);
    if (statEl) statEl.textContent = String(val);
}

/* ============================================================
   CONFIG MODAL
   ============================================================ */

function openConfig() {
    _configModalTrigger = document.activeElement;
    const overlay = document.getElementById('config-modal');
    if (!overlay) return;

    fetch('/api/config')
        .then(r => r.json())
        .then(cfg => {
            const genre  = document.getElementById('cfg-genres');
            const locale = document.getElementById('cfg-locale');
            const copy   = document.getElementById('cfg-copy-mode');
            const suffix = document.getElementById('cfg-suffix');
            if (genre  && cfg.genres_enabled)  genre.value  = cfg.genres_enabled === 'all' ? 'all' : 'custom';
            if (locale && cfg.locale_genres)   locale.value = cfg.locale_genres;
            if (copy   && cfg.copy_mode)       copy.value   = cfg.copy_mode;
            if (suffix && cfg.filename_suffix) suffix.value = cfg.filename_suffix;
        })
        .catch(() => {});

    overlay.style.display = 'flex';
    requestAnimationFrame(() => overlay.classList.add('open'));

    const focusable = getFocusableElements();
    if (focusable.length > 0) focusable[0].focus();

    overlay.addEventListener('keydown', handleModalKeydown);
    overlay.addEventListener('click',   handleModalOverlayClick);
    document.body.style.overflow = 'hidden';
}

function closeConfig() {
    const overlay = document.getElementById('config-modal');
    if (!overlay) return;

    overlay.classList.remove('open');
    overlay.removeEventListener('keydown', handleModalKeydown);
    overlay.removeEventListener('click',   handleModalOverlayClick);

    setTimeout(() => {
        overlay.style.display = 'none';
        document.body.style.overflow = '';
        if (_configModalTrigger && typeof _configModalTrigger.focus === 'function') {
            _configModalTrigger.focus();
        }
        _configModalTrigger = null;
    }, 200);
}

function handleModalOverlayClick(e) {
    if (e.target === document.getElementById('config-modal')) closeConfig();
}

function getFocusableElements() {
    const modal = document.getElementById('config-modal-inner');
    if (!modal) return [];
    return Array.from(
        modal.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])')
    ).filter(el => !el.disabled && el.offsetParent !== null);
}

/**
 * handleModalKeydown — focus trap + Escape-to-close.
 */
function handleModalKeydown(e) {
    if (e.key === 'Escape') {
        e.preventDefault();
        closeConfig();
        return;
    }
    if (e.key !== 'Tab') return;

    const focusable = getFocusableElements();
    if (focusable.length === 0) { e.preventDefault(); return; }

    const first = focusable[0];
    const last  = focusable[focusable.length - 1];

    if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
    }
}

function saveConfig() {
    const config = {
        genres_enabled:  document.getElementById('cfg-genres')?.value    || 'all',
        locale_genres:   document.getElementById('cfg-locale')?.value    || 'auto',
        copy_mode:       document.getElementById('cfg-copy-mode')?.value || 'true',
        filename_suffix: document.getElementById('cfg-suffix')?.value    || 'false',
    };

    fetch('/api/config', {
        method: 'POST',
        headers: csrfHeaders(),
        body: csrfBody(config),
    })
    .then(r => r.json())
    .then(data => {
        if (data.error) throw new Error(data.error);
        closeConfig();
        const toast = el('div', {
            role: 'status',
            'aria-live': 'polite',
            style: 'position:fixed;bottom:1rem;right:1rem;background:var(--navy-light);border:1px solid var(--navy-border);border-radius:8px;padding:0.65rem 1rem;font-size:0.85rem;z-index:300;color:var(--success)',
        }, '\u2713 Settings saved');
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 2500);
    })
    .catch(err => alert('Failed to save settings: ' + err.message));
}
