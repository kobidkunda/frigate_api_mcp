(function() {
    'use strict';

    const state = {
        page: 1,
        pageSize: 20,
        total: 0,
        photoIndex: {},
        filters: {
            dateFrom: null,
            dateTo: null,
            days: [],
            timeFrom: 0,
            timeTo: 23,
            cameras: [],
            groups: [],
            labels: []
        },
        isLoading: false
    };

    const elements = {
        photoGrid: document.getElementById('photoGrid'),
        emptyState: document.getElementById('emptyState'),
        loadingState: document.getElementById('loadingState'),
        totalCount: document.getElementById('totalCount'),
        showingCount: document.getElementById('showingCount'),
        pageStart: document.getElementById('pageStart'),
        pageEnd: document.getElementById('pageEnd'),
        pageTotal: document.getElementById('pageTotal'),
        currentPage: document.getElementById('currentPage'),
        prevPage: document.getElementById('prevPage'),
        nextPage: document.getElementById('nextPage'),
        photoModal: document.getElementById('photoModal'),
        modalTitle: document.getElementById('modalTitle'),
        modalImage: document.getElementById('modalImage'),
        modalSegmentId: document.getElementById('modalSegmentId'),
        modalFrames: document.getElementById('modalFrames'),
        modalStatus: document.getElementById('modalStatus'),
        modalCamera: document.getElementById('modalCamera'),
        modalGroups: document.getElementById('modalGroups'),
        modalTemporal: document.getElementById('modalTemporal'),
        modalDuration: document.getElementById('modalDuration'),
        modalModel: document.getElementById('modalModel'),
        modalConfidence: document.getElementById('modalConfidence'),
        modalNotes: document.getElementById('modalNotes'),
        modalDetailsLink: document.getElementById('modalDetailsLink'),
        modalClose: document.getElementById('modalClose'),
        toggleFilters: document.getElementById('toggleFilters'),
        filtersContent: document.getElementById('filtersContent'),
        filterArrow: document.getElementById('filterArrow'),
        clearFilters: document.getElementById('clearFilters'),
        applyFilters: document.getElementById('applyFilters'),
        dateFrom: document.getElementById('dateFrom'),
        dateTo: document.getElementById('dateTo'),
        cameraFilter: document.getElementById('cameraFilter'),
        groupFilter: document.getElementById('groupFilter'),
        statusFilter: document.getElementById('statusFilter'),
        timeFrom: document.getElementById('timeFrom'),
        timeTo: document.getElementById('timeTo'),
        timeFromLabel: document.getElementById('timeFromLabel'),
        timeToLabel: document.getElementById('timeToLabel')
    };

    function getLabelColor(label) {
        const colors = {
            'working': { bg: 'status-working', dot: '#00e475' },
            'not_working': { bg: 'status-not-working', dot: '#909094' },
            'no_person': { bg: 'status-no-person', dot: '#b8c3ff' },
            'uncertain': { bg: 'status-uncertain', dot: '#c8c8c8' }
        };
        return colors[label] || colors['uncertain'];
    }

    function formatTs(ts) {
        if (!ts) return '';
        try {
            return new Intl.DateTimeFormat('en-GB', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                hour12: false
            }).format(new Date(ts));
        } catch (_) {
            return ts;
        }
    }

    function formatDuration(seconds) {
        if (!seconds) return '0m';
        const mins = Math.floor(seconds / 60);
        if (mins < 60) return `${mins}m`;
        const hours = Math.floor(mins / 60);
        const remainMins = mins % 60;
        return remainMins > 0 ? `${hours}h ${remainMins}m` : `${hours}h`;
    }

    function getEvidenceFrames(photo) {
        if (photo.evidence_frames && photo.evidence_frames.length) {
            return photo.evidence_frames.filter(Boolean);
        }
        return [photo.evidence_path].filter(Boolean);
    }

    function renderEvidenceFrames(photo) {
        const frames = getEvidenceFrames(photo);
        return frames.map((path, index) => `
            <button type="button" class="evidence-frame-button rounded-lg overflow-hidden border border-outline-variant/20" data-frame-path="${path}">
                <img src="/${path}" alt="Evidence ${index + 1}" class="w-24 h-16 object-cover" loading="lazy">
            </button>
        `).join('');
    }

    function renderPhotos(photos) {
        if (!elements.photoGrid) return;

        if (!photos || photos.length === 0) {
            elements.photoGrid.innerHTML = '';
            elements.emptyState.classList.remove('hidden');
            return;
        }

        elements.emptyState.classList.add('hidden');

        state.photoIndex = Object.fromEntries((photos || []).map(photo => [String(photo.id), photo]));

        const html = photos.map(p => {
            const displayLabel = p.reviewed_label || p.label;
            const colors = getLabelColor(displayLabel);
            const duration = formatDuration(p.duration_seconds);
            const confidence = Math.round((p.confidence || 0) * 100);
            const frames = getEvidenceFrames(p);
            const primaryImage = frames[0] || '';

            return `
            <div class="photo-card ${colors.bg} rounded-xl overflow-hidden cursor-pointer" data-photo-id="${p.id}">
                <div class="photo-img-container aspect-video bg-surface-container-lowest">
                    <img src="/${primaryImage}" alt="${displayLabel}" class="w-full h-full object-cover" loading="lazy">
                </div>
                <div class="p-4 space-y-2">
                    <div class="flex items-center gap-2">
                        <span class="w-2 h-2 rounded-full" style="background:${colors.dot}"></span>
                        <span class="text-sm font-bold text-on-surface capitalize">${displayLabel}</span>
                        <span class="text-xs text-on-surface-variant ml-auto">#SEG-${p.id}</span>
                    </div>
                    <div class="text-xs text-on-surface-variant">
                        <span class="font-medium text-on-surface">${p.camera_name || 'Unknown'}</span>
                    </div>
                    <div class="text-xs text-on-surface-variant">
                        ${formatTs(p.start_ts)}
                    </div>
                    <div class="flex items-center gap-3 text-xs text-on-surface-variant">
                        <span>Conf: ${confidence}%</span>
                        <span>${duration}</span>
                        <span>Model: ${p.model_used || '-'}</span>
                    </div>
                    ${p.notes ? `<p class="text-xs text-on-surface-variant line-clamp-2 mt-2">${p.notes}</p>` : ''}
                </div>
            </div>`;
        }).join('');

        elements.photoGrid.innerHTML = html;
    }

    function updatePagination() {
        const start = (state.page - 1) * state.pageSize + 1;
        const end = Math.min(state.page * state.pageSize, state.total);

        elements.pageStart.textContent = state.total > 0 ? start : 0;
        elements.pageEnd.textContent = end;
        elements.pageTotal.textContent = state.total;
        elements.currentPage.textContent = state.page;
        elements.totalCount.textContent = state.total;
        elements.showingCount.textContent = state.total > 0 ? `${start}-${end}` : '0';

        elements.prevPage.disabled = state.page <= 1;
        elements.nextPage.disabled = end >= state.total;
    }

    async function loadPhotos() {
        if (state.isLoading) return;
        state.isLoading = true;

        elements.loadingState.classList.remove('hidden');
        elements.emptyState.classList.add('hidden');
        elements.photoGrid.innerHTML = '';

        const params = new URLSearchParams();
        params.append('page', state.page);
        params.append('page_size', state.pageSize);

        if (state.filters.dateFrom) params.append('date_from', state.filters.dateFrom);
        if (state.filters.dateTo) params.append('date_to', state.filters.dateTo);
        if (state.filters.days.length > 0) params.append('days', state.filters.days.join(','));
        params.append('time_from', state.filters.timeFrom);
        params.append('time_to', state.filters.timeTo);
        if (state.filters.cameras.length > 0) params.append('cameras', state.filters.cameras.join(','));
        if (state.filters.groups.length > 0) params.append('groups', state.filters.groups.join(','));
        if (state.filters.labels.length > 0) params.append('labels', state.filters.labels.join(','));

        try {
            const response = await fetch('/api/photos?' + params.toString());
            if (!response.ok) throw new Error('HTTP ' + response.status);

            const data = await response.json();
            state.total = data.total;

            elements.loadingState.classList.add('hidden');
            renderPhotos(data.items);
            updatePagination();

        } catch (error) {
            console.error('loadPhotos: ERROR', error);
            elements.loadingState.classList.add('hidden');
            elements.emptyState.classList.remove('hidden');
        } finally {
            state.isLoading = false;
        }
    }

    async function loadFilterOptions() {
        try {
            const [cameras, groups] = await Promise.all([
                fetch('/api/cameras').then(r => r.json()),
                fetch('/api/groups').then(r => r.json())
            ]);

            cameras.forEach(c => {
                const opt = document.createElement('option');
                opt.value = c.id;
                opt.textContent = c.name || c.frigate_name;
                elements.cameraFilter.appendChild(opt);
            });

            groups.forEach(g => {
                const opt = document.createElement('option');
                opt.value = g.id;
                opt.textContent = g.name;
                elements.groupFilter.appendChild(opt);
            });
        } catch (e) {
            console.error('Failed to load filter options', e);
        }
    }

    function collectFilters() {
        state.filters.dateFrom = elements.dateFrom.value || null;
        state.filters.dateTo = elements.dateTo.value || null;
        state.filters.timeFrom = parseInt(elements.timeFrom.value) || 0;
        state.filters.timeTo = parseInt(elements.timeTo.value) || 23;

        const days = [];
        document.querySelectorAll('.day-filter:checked').forEach(cb => {
            days.push(parseInt(cb.value));
        });
        state.filters.days = days;

        const cameras = [];
        Array.from(elements.cameraFilter.selectedOptions).forEach(opt => {
            cameras.push(parseInt(opt.value));
        });
        state.filters.cameras = cameras;

        const groups = [];
        Array.from(elements.groupFilter.selectedOptions).forEach(opt => {
            groups.push(parseInt(opt.value));
        });
        state.filters.groups = groups;

        const labels = [];
        Array.from(elements.statusFilter.selectedOptions).forEach(opt => {
            labels.push(opt.value);
        });
        state.filters.labels = labels;
    }

    function clearFilters() {
        elements.dateFrom.value = '';
        elements.dateTo.value = '';
        elements.timeFrom.value = 0;
        elements.timeTo.value = 23;
        elements.timeFromLabel.textContent = '00:00';
        elements.timeToLabel.textContent = '23:59';
        elements.cameraFilter.selectedIndex = -1;
        elements.groupFilter.selectedIndex = -1;
        elements.statusFilter.selectedIndex = -1;
        document.querySelectorAll('.day-filter').forEach(cb => cb.checked = false);

        state.filters = {
            dateFrom: null,
            dateTo: null,
            days: [],
            timeFrom: 0,
            timeTo: 23,
            cameras: [],
            groups: [],
            labels: []
        };
        state.page = 1;
        loadPhotos();
    }

    window.openPhotoModal = function(photo) {
        const displayLabel = photo.reviewed_label || photo.label;
        const colors = getLabelColor(displayLabel);
        const frames = getEvidenceFrames(photo);

        elements.modalTitle.textContent = displayLabel.charAt(0).toUpperCase() + displayLabel.slice(1) + ' Evidence';
        elements.modalImage.src = frames[0] ? '/' + frames[0] : '';
        elements.modalImage.alt = displayLabel;
        elements.modalFrames.innerHTML = renderEvidenceFrames({ ...photo, evidence_frames: frames });
        elements.modalSegmentId.textContent = '#SEG-' + photo.id;
        elements.modalStatus.innerHTML = `<span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-bold ${colors.bg}" style="color:${colors.dot}"><span class="w-1.5 h-1.5 rounded-full" style="background:${colors.dot}"></span>${displayLabel}</span>`;
        elements.modalCamera.textContent = photo.camera_name || 'Unknown';
        elements.modalGroups.textContent = photo.group_names || 'None';
        elements.modalTemporal.textContent = formatTs(photo.start_ts) + ' - ' + formatTs(photo.end_ts);
        elements.modalDuration.textContent = formatDuration(photo.duration_seconds);
        elements.modalConfidence.textContent = Math.round((photo.confidence || 0) * 100) + '%';
        elements.modalModel.textContent = photo.model_used || '-';
        elements.modalNotes.textContent = photo.notes || 'No additional notes available.';
        elements.modalDetailsLink.href = '/history?segment=' + photo.id;

        elements.photoModal.classList.remove('hidden');
    };

    function closeModal() {
        elements.photoModal.classList.add('hidden');
    }

    function initEventListeners() {
        elements.prevPage.addEventListener('click', () => {
            if (state.page > 1) {
                state.page--;
                loadPhotos();
            }
        });

        elements.nextPage.addEventListener('click', () => {
            if (state.page * state.pageSize < state.total) {
                state.page++;
                loadPhotos();
            }
        });

        elements.applyFilters.addEventListener('click', () => {
            collectFilters();
            state.page = 1;
            loadPhotos();
        });

        elements.clearFilters.addEventListener('click', clearFilters);

        elements.toggleFilters.addEventListener('click', () => {
            elements.filtersContent.classList.toggle('hidden');
            elements.filterArrow.style.transform = elements.filtersContent.classList.contains('hidden') ? 'rotate(0deg)' : 'rotate(180deg)';
        });

        elements.photoGrid.addEventListener('click', (e) => {
            const card = e.target.closest('[data-photo-id]');
            if (!card) return;
            const photo = state.photoIndex[card.dataset.photoId];
            if (photo) window.openPhotoModal(photo);
        });

        elements.modalFrames.addEventListener('click', (e) => {
            const button = e.target.closest('[data-frame-path]');
            if (!button) return;
            elements.modalImage.src = '/' + button.dataset.framePath;
        });

        elements.timeFrom.addEventListener('input', () => {
            elements.timeFromLabel.textContent = elements.timeFrom.value.padStart(2, '0') + ':00';
        });

        elements.timeTo.addEventListener('input', () => {
            elements.timeToLabel.textContent = elements.timeTo.value.padStart(2, '0') + ':59';
        });

        elements.modalClose.addEventListener('click', closeModal);
        elements.photoModal.addEventListener('click', (e) => {
            if (e.target === elements.photoModal) closeModal();
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') closeModal();
        });
    }

    window.addEventListener('load', function() {
        loadFilterOptions();
        initEventListeners();
        loadPhotos();
    });
})();
