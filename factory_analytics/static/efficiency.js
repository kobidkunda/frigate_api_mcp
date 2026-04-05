/**
 * Worker Efficiency Analytics - Compact Heatmap Grid
 * Daily: Custom grid with small squares per log entry
 * Weekly/Monthly: ApexCharts heatmap
 */
(function() {
  'use strict';

  const state = {
    currentView: 'daily',
    currentDate: new Date(),
    cameras: [],
    groups: [],
    isLoading: false,
    heatmapChart: null,
  };

  const LABEL_COLORS = {
    working: '#00E396',
    not_working: '#FEB019',
    no_person: '#775DD0',
    uncertain: '#6B7280',
    error: '#FF4560',
  };

  const STATUS_LABELS = {
    working: 'Working',
    not_working: 'Not Working',
    no_person: 'No Person',
    uncertain: 'Uncertain',
    error: 'Error',
  };

  function init() {
    setupEventListeners();
    setupDatePicker();
    loadData();
  }

  function setupEventListeners() {
    document.querySelectorAll('.view-toggle').forEach(btn => {
      btn.addEventListener('click', (e) => switchView(e.target.dataset.view));
    });
    const el = (id) => document.getElementById(id);
    el('prevDate').addEventListener('click', () => navigateDate(-1));
    el('nextDate').addEventListener('click', () => navigateDate(1));
    el('todayBtn').addEventListener('click', goToToday);
    el('datePicker').addEventListener('change', handleDatePickerChange);
    el('refreshData').addEventListener('click', () => refreshData());
    el('exportData').addEventListener('click', exportToCSV);
    el('prevPage').addEventListener('click', () => changePage(-1));
    el('nextPage').addEventListener('click', () => changePage(1));
    el('popoverClose').addEventListener('click', hidePopover);
    // Delegated click handler for segment job-action buttons
    el('popoverSegments').addEventListener('click', (e) => {
      const jobBtn = e.target.closest('[data-job-id]');
      if (jobBtn) {
        e.preventDefault();
        window.open(`/jobs?job=${jobBtn.dataset.jobId}`, '_blank');
      }
    });
    el('modalClose').addEventListener('click', hideSegmentModal);
    el('segmentModal').addEventListener('click', (e) => {
      if (e.target === el('segmentModal')) hideSegmentModal();
    });
    document.addEventListener('click', (e) => {
      const popover = el('cellDetailPopover');
      if (popover && !popover.contains(e.target) && !e.target.closest('.hm-sq') && !e.target.closest('.hm-cell')) {
        hidePopover();
      }
    });
  }

  function setupDatePicker() {
    document.getElementById('datePicker').valueAsDate = state.currentDate;
  }

  async function loadData() {
    try {
      const [camerasRes, groupsRes] = await Promise.all([
        fetch('/api/cameras').then(r => r.json()),
        fetch('/api/groups').then(r => r.json()),
      ]);
      state.cameras = camerasRes;
      state.groups = groupsRes;
      await refreshData();
    } catch (err) {
      console.error('Load error:', err);
    }
  }

  async function getGroupCameras() {
    const groupCameras = [];
    for (const g of state.groups) {
      const cameras = await fetch(`/api/groups/${g.id}/cameras`).then(r => r.json());
      cameras.filter(c => c.enabled === 1).forEach(c => {
        groupCameras.push({ ...c, group_name: g.name, group_type: g.group_type, group_id: g.id });
      });
    }
    return groupCameras;
  }

  function switchView(view) {
    if (state.currentView === view) return;
    state.currentView = view;
    document.querySelectorAll('.view-toggle').forEach(btn => {
      if (btn.dataset.view === view) {
        btn.classList.remove('text-on-surface-variant');
        btn.classList.add('bg-primary', 'text-on-primary');
      } else {
        btn.classList.remove('bg-primary', 'text-on-primary');
        btn.classList.add('text-on-surface-variant');
      }
    });
    refreshData();
  }

  function navigateDate(direction) {
    const d = new Date(state.currentDate);
    switch (state.currentView) {
      case 'daily': d.setDate(d.getDate() + direction); break;
      case 'weekly': d.setDate(d.getDate() + direction * 7); break;
      case 'monthly': d.setMonth(d.getMonth() + direction); break;
    }
    state.currentDate = d;
    document.getElementById('datePicker').valueAsDate = d;
    refreshData();
  }

  function goToToday() {
    state.currentDate = new Date();
    document.getElementById('datePicker').valueAsDate = state.currentDate;
    refreshData();
  }

  function handleDatePickerChange(e) {
    if (e.target.value) {
      state.currentDate = new Date(e.target.value);
      refreshData();
    }
  }

  async function refreshData() {
    if (state.isLoading) return;
    state.isLoading = true;
    try {
      const groupCameras = await getGroupCameras();
      const dateStr = formatDate(state.currentDate);
      const promises = [fetchSummary(dateStr), fetchTimeline(dateStr, 1)];
      if (state.currentView === 'daily') {
        promises.push(fetchHeatmapMinute(dateStr));
      } else if (state.currentView === 'weekly') {
        const from = formatDate(addDays(state.currentDate, -6));
        promises.push(fetchHeatmapDaily(from, dateStr));
      } else {
        const [y, m] = [state.currentDate.getFullYear(), state.currentDate.getMonth()];
        const from = formatDate(new Date(y, m, 1));
        const to = formatDate(new Date(y, m + 1, 0));
        promises.push(fetchHeatmapDaily(from, to));
      }
      const [summary, timeline, heatmapData] = await Promise.all(promises);
      updateSummaryCards(summary);
      updateShiftPerformance(summary);
      updateTopPerformers(summary);
      updateActivityLog(timeline);
      if (state.currentView === 'daily') {
        buildDailyGrid(heatmapData, groupCameras);
      } else {
        buildApexHeatmap(heatmapData, groupCameras);
      }
      updateSubtitle();
    } catch (err) {
      console.error('Refresh error:', err);
    } finally {
      state.isLoading = false;
    }
  }

  async function fetchSummary(date) {
    return fetch(`/api/efficiency/summary?from_date=${date}&to_date=${date}`).then(r => r.json());
  }

  async function fetchTimeline(date, page) {
    return fetch(`/api/efficiency/timeline?date=${date}&page=${page}&page_size=50`).then(r => r.json());
  }

  async function fetchHeatmapMinute(date) {
    return fetch(`/api/efficiency/heatmap-minute?date=${date}`).then(r => r.json());
  }

  async function fetchHeatmapDaily(from, to) {
    return fetch(`/api/efficiency/heatmap-daily?from_date=${from}&to_date=${to}`).then(r => r.json());
  }

  function updateSummaryCards(summary) {
    const s = summary.summary || {};
    const total = s.total_segments || 0;
    const working = s.working_count || 0;
    const efficiency = total > 0 ? Math.round((working / total) * 100) : 0;
    document.getElementById('totalEfficiency').textContent = `${efficiency}%`;
    document.getElementById('workingTime').textContent = formatMinutesToHM(s.total_working_minutes || 0);
    document.getElementById('idleTime').textContent = formatMinutesToHM(s.total_idle_minutes || 0);
    document.getElementById('activeWorkers').textContent = s.active_cameras || 0;
  }

  function updateShiftPerformance(summary) {
    const shifts = summary.shift_breakdown || [];
    let dayEff = 0, nightEff = 0, dayTotal = 0, nightTotal = 0;
    shifts.forEach(s => {
      const eff = s.total_segments > 0 ? Math.round((s.working_count / s.total_segments) * 100) : 0;
      if (s.shift === 'day') { dayEff = eff; dayTotal = s.total_segments; }
      else { nightEff = eff; nightTotal = s.total_segments; }
    });
    document.getElementById('dayShiftBar').style.width = `${dayEff}%`;
    document.getElementById('nightShiftBar').style.width = `${nightEff}%`;
    document.getElementById('dayShiftPct').textContent = `${dayEff}%`;
    document.getElementById('nightShiftPct').textContent = `${nightEff}%`;
    document.getElementById('dayShiftStats').textContent = `${dayTotal} segments`;
    document.getElementById('nightShiftStats').textContent = `${nightTotal} segments`;
  }

  function updateTopPerformers(summary) {
    const breakdown = summary.camera_breakdown || [];
    const container = document.getElementById('topPerformersList');
    if (breakdown.length === 0) {
      container.innerHTML = '<div class="text-sm text-on-surface-variant text-center py-4">No data</div>';
      return;
    }
    const sorted = [...breakdown].sort((a, b) => (b.efficiency_pct || 0) - (a.efficiency_pct || 0)).slice(0, 5);
    container.innerHTML = sorted.map((c, i) => {
      const eff = c.efficiency_pct || 0;
      const color = eff >= 80 ? 'text-emerald-500' : eff >= 60 ? 'text-amber-500' : 'text-red-500';
      return `<div class="flex items-center gap-3 p-2 rounded-lg hover:bg-surface-container-high/50 transition-colors"><div class="w-5 h-5 rounded-full bg-primary/10 text-primary flex items-center justify-center text-[10px] font-bold">${i+1}</div><div class="flex-1 min-w-0"><div class="text-xs font-medium text-on-surface truncate">${c.camera_name}</div><div class="text-[10px] text-on-surface-variant">${c.working_count||0}/${c.total_segments||0} working</div></div><div class="text-sm font-bold ${color}">${eff}%</div></div>`;
    }).join('');
  }

  function updateActivityLog(timeline) {
    const items = timeline.items || [];
    const total = timeline.total || 0;
    const page = timeline.page || 1;
    const pageSize = timeline.page_size || 50;
    const tbody = document.getElementById('activityLogBody');
    if (items.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" class="py-6 text-center text-xs text-on-surface-variant">No activity</td></tr>';
    } else {
      tbody.innerHTML = items.map(item => {
        const color = LABEL_COLORS[item.label] || LABEL_COLORS.uncertain;
        const name = STATUS_LABELS[item.label] || item.label;
        const conf = Math.round((item.confidence || 0) * 100);
        return `<tr class="hover:bg-surface-container-high/50 transition-colors"><td class="py-2 px-3 text-xs text-on-surface">${new Date(item.start_ts).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})}</td><td class="py-2 px-3 text-xs text-on-surface">${item.camera_name}</td><td class="py-2 px-3"><span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium" style="background:${color}18;color:${color}"><span class="w-1 h-1 rounded-full" style="background:${color}"></span>${name}</span></td><td class="py-2 px-3 text-xs text-on-surface">${item.duration_minutes||0}m</td><td class="py-2 px-3 text-xs text-on-surface-variant">${conf}%</td></tr>`;
      }).join('');
    }
    const start = (page-1)*pageSize+1, end = Math.min(page*pageSize, total);
    document.getElementById('showingStart').textContent = items.length > 0 ? start : 0;
    document.getElementById('showingEnd').textContent = items.length > 0 ? end : 0;
    document.getElementById('totalRecords').textContent = total;
    document.getElementById('currentPage').textContent = page;
    document.getElementById('prevPage').disabled = page <= 1;
    document.getElementById('nextPage').disabled = end >= total;
  }

  async function changePage(direction) {
    const newPage = parseInt(document.getElementById('currentPage').textContent) + direction;
    if (newPage < 1) return;
    const timeline = await fetchTimeline(formatDate(state.currentDate), newPage);
    updateActivityLog(timeline);
  }

  // ============ DAILY GRID ============
  let _cellSegmentsMap = {};
  function buildDailyGrid(data, groupCameras) {
    const container = document.getElementById('dailyGrid');
    document.getElementById('dailyGridView').classList.remove('hidden');
    document.getElementById('chartView').classList.add('hidden');
    if (state.heatmapChart) { state.heatmapChart.destroy(); state.heatmapChart = null; }

    const rows = data.rows || [];
    if (rows.length === 0) {
      container.innerHTML = '<div class="text-center py-12 text-sm text-on-surface-variant">No activity data for this date</div>';
      return;
    }

    // Group by camera -> hour
    const cameraData = {};
    _cellSegmentsMap = {};
    rows.forEach(r => {
      if (!cameraData[r.camera_id]) {
        const gc = groupCameras.find(c => c.id === r.camera_id);
        cameraData[r.camera_id] = {
          label: gc ? gc.name : r.camera_name,
          group: gc ? gc.group_name : '',
          hours: {},
        };
      }
      const h = parseInt(r.hour);
      if (!cameraData[r.camera_id].hours[h]) cameraData[r.camera_id].hours[h] = [];
      cameraData[r.camera_id].hours[h].push(r);
    });

    const camIds = Object.keys(cameraData).sort((a, b) => cameraData[a].label.localeCompare(cameraData[b].label));
    if (camIds.length === 0) {
      container.innerHTML = '<div class="text-center py-12 text-sm text-on-surface-variant">No group camera data</div>';
      return;
    }

    const SQ = 18;
    const GP = 2;
    const COL_W = 42;
    const LABEL_W = 80;

    // Use a proper <table> for perfect column alignment
    let html = '<table style="width:100%;border-collapse:collapse;table-layout:fixed"><colgroup><col style="width:' + LABEL_W + 'px"><col span="24" style="width:' + COL_W + 'px"></colgroup>';

    // Header row
    html += '<thead><tr>';
    html += '<th style="padding:0;height:22px;text-align:left;font-size:9px;color:rgba(148,163,184,0.5);text-transform:uppercase;letter-spacing:0.5px;font-weight:400">Camera</th>';
    for (let h = 0; h < 24; h++) {
      const isEdge = h === 9 || h === 21;
      const bg = isEdge ? 'background:rgba(245,158,11,0.15)' : '';
      html += `<th style="padding:0;height:22px;text-align:center;font-size:9px;font-weight:400;color:${isEdge ? '#F59E0B' : 'rgba(148,163,184,0.4)'};${bg}">${String(h).padStart(2,'0')}</th>`;
    }
    html += '</tr></thead><tbody>';

    // Data rows
    camIds.forEach(camId => {
      const cam = cameraData[camId];
      html += '<tr>';
      html += `<td style="padding:0;padding-right:4px;vertical-align:top;font-size:10px;color:rgba(148,163,184,0.7);white-space:nowrap;overflow:hidden;text-overflow:ellipsis" title="${cam.label} (${cam.group})">${cam.label}</td>`;
      for (let h = 0; h < 24; h++) {
        const segments = cam.hours[h] || [];
        const isEdge = h === 9 || h === 21;
        const cellBg = isEdge ? 'rgba(245,158,11,0.08)' : (h % 2 === 0 ? 'rgba(255,255,255,0.02)' : 'transparent');
        const borderStyle = isEdge ? 'border-left:2px solid rgba(245,158,11,0.3)' : '';

        if (segments.length === 0) {
          html += `<td style="padding:0;background:${cellBg};${borderStyle}"></td>`;
        } else {
          const cellKey = `${camId}-${h}`;
          _cellSegmentsMap[cellKey] = segments;
          html += `<td style="padding:2px;background:${cellBg};${borderStyle};vertical-align:top">`;
          html += `<div class="hm-cell" data-cell-key="${cellKey}" style="display:flex;flex-wrap:wrap;gap:${GP}px;cursor:pointer">`;
          segments.forEach(seg => {
            const color = LABEL_COLORS[seg.label] || LABEL_COLORS.uncertain;
            const conf = Math.round((seg.confidence || 0) * 100);
            const name = STATUS_LABELS[seg.label] || seg.label;
            const segId = seg.segment_id || seg.id || '';
            html += `<div class="hm-sq" style="width:${SQ}px;height:${SQ}px;border-radius:2px;background:${color};transition:transform 0.1s,box-shadow 0.1s" data-cam="${cam.label}" data-label="${seg.label}" data-confidence="${conf}" data-start="${seg.start_ts}" data-end="${seg.end_ts}" data-duration="${seg.duration_minutes}" data-seg-id="${segId}" title="${name} ${conf}%"></div>`;
          });
          html += '</div></td>';
        }
      }
      html += '</tr>';
    });

    html += '</tbody></table>';

    // Shift labels below
    html += `<div style="display:grid;grid-template-columns:${LABEL_W}px repeat(24,${COL_W}px);gap:0;margin-top:4px">`;
    html += '<div></div>';
    html += '<div style="grid-column:span 9;text-align:center;font-size:8px;color:rgba(148,163,184,0.3);text-transform:uppercase;letter-spacing:1px">Night</div>';
    html += '<div style="grid-column:span 12;text-align:center;font-size:8px;color:rgba(245,158,11,0.3);text-transform:uppercase;letter-spacing:1px">Day Shift (09:00-21:00)</div>';
    html += '<div style="grid-column:span 3;text-align:center;font-size:8px;color:rgba(99,102,241,0.3);text-transform:uppercase;letter-spacing:1px">Night</div>';
    html += '</div>';

    container.innerHTML = html;

    // Click handlers — pass the entire cell segments list
    container.querySelectorAll('.hm-cell').forEach(cell => {
      cell.addEventListener('click', (e) => {
        e.stopPropagation();
        const segs = _cellSegmentsMap[cell.dataset.cellKey];
        const segCamId = segs && segs.length > 0 ? segs[0].camera_id : '';
        showPopover(e, {
          camera: segCamId in cameraData ? cameraData[segCamId].label : '',
          segments: segs || [],
        });
      });
    });
  }

  // ============ APEXCHARTS (Weekly/Monthly) ============
  function buildApexHeatmap(data, groupCameras) {
    document.getElementById('dailyGridView').classList.add('hidden');
    document.getElementById('chartView').classList.remove('hidden');
    if (state.heatmapChart) { state.heatmapChart.destroy(); state.heatmapChart = null; }

    const rows = data.rows || [];
    const container = document.getElementById('heatmapChart');
    if (rows.length === 0) {
      container.innerHTML = '<div class="text-center py-12 text-sm text-on-surface-variant">No data</div>';
      return;
    }

    const cameraMap = {};
    groupCameras.forEach(c => { cameraMap[c.id] = { ...c, label: c.name }; });

    let dayLabels, daysCount;
    if (state.currentView === 'weekly') {
      const startOfWeek = getStartOfWeek(state.currentDate);
      daysCount = 7;
      dayLabels = Array.from({length: 7}, (_, i) => addDays(startOfWeek, i).toLocaleDateString('en-US', { weekday: 'short', day: 'numeric' }));
    } else {
      const [y, m] = [state.currentDate.getFullYear(), state.currentDate.getMonth()];
      daysCount = new Date(y, m + 1, 0).getDate();
      dayLabels = Array.from({length: daysCount}, (_, i) => String(i + 1));
    }

    const seriesMap = {};
    const allCamIds = new Set();
    rows.forEach(r => allCamIds.add(r.camera_id));
    allCamIds.forEach(id => {
      const cam = cameraMap[id] || { label: `Camera ${id}` };
      seriesMap[cam.label] = new Array(daysCount).fill(null).map(() => ({ segments: [], total: 0 }));
    });

    rows.forEach(r => {
      const cam = cameraMap[r.camera_id];
      if (!cam) return;
      let dayIdx = -1;
      if (state.currentView === 'weekly') {
        const startOfWeek = getStartOfWeek(state.currentDate);
        for (let i = 0; i < 7; i++) { if (formatDate(addDays(startOfWeek, i)) === r.date) { dayIdx = i; break; } }
      } else {
        dayIdx = parseInt(r.date.split('-')[2]) - 1;
      }
      if (dayIdx < 0 || dayIdx >= daysCount) return;
      seriesMap[cam.label][dayIdx].segments.push(r);
      seriesMap[cam.label][dayIdx].total += (r.total_minutes || 0);
    });

    const labelScores = { working: 5, not_working: 3, no_person: 2, uncertain: 0, error: 0 };
    const series = Object.entries(seriesMap).map(([name, days]) => ({
      name,
      data: days.map((cell, i) => {
        const labelCounts = {};
        cell.segments.forEach(s => { labelCounts[s.label] = (labelCounts[s.label] || 0) + (s.count || 1); });
        let dominant = 'uncertain', bestCount = 0;
        Object.entries(labelCounts).forEach(([l, c]) => { if (c > bestCount) { bestCount = c; dominant = l; } });
        const score = labelScores[dominant] || 0;
        const avgConf = cell.segments.length > 0 ? cell.segments.reduce((a, s) => a + (s.avg_confidence || 0), 0) / cell.segments.length : 0;
        return { x: dayLabels[i], y: score + (avgConf / 200), meta: { label: dominant, confidence: Math.round(avgConf * 100), minutes: Math.round(cell.total), count: cell.segments.reduce((a, s) => a + (s.count || 0), 0), camera: name, time: dayLabels[i] } };
      }),
    }));

    const isDark = true;
    state.heatmapChart = new ApexCharts(container, {
      series,
      chart: { type: 'heatmap', height: Math.max(200, series.length * 40 + 80), background: 'transparent', toolbar: { show: false },
        events: { dataPointSelection: function(event, chartContext, config) {
          const point = config.w.config.series[config.seriesIndex].data[config.dataPointIndex];
          if (point && point.meta) showPopover(event, point.meta);
        }}},
      plotOptions: { heatmap: { shadeIntensity: 0.5, radius: 2, colorScale: { ranges: [
        { from: 0, to: 0.01, color: '#1F2937', name: 'No Data' },
        { from: 0.01, to: 1.5, color: '#FF4560' },
        { from: 1.5, to: 2.5, color: '#775DD0' },
        { from: 2.5, to: 3.5, color: '#FEB019' },
        { from: 3.5, to: 5.6, color: '#00E396' },
      ]}}},
      dataLabels: { enabled: false },
      stroke: { width: 1, colors: ['rgba(255,255,255,0.05)'] },
      xaxis: { labels: { style: { colors: '#64748b', fontSize: '10px' } } },
      yaxis: { labels: { style: { colors: '#94a3b8', fontSize: '10px' }, maxWidth: 120 } },
      tooltip: { theme: 'dark', custom: function({ seriesIndex, dataPointIndex, w }) {
        const meta = w.config.series[seriesIndex].data[dataPointIndex].meta || {};
        const color = LABEL_COLORS[meta.label] || '#888';
        const name = STATUS_LABELS[meta.label] || meta.label;
        return `<div style="padding:8px;max-width:200px"><div style="font-weight:600;margin-bottom:4px;font-size:12px">${meta.camera}</div><div style="display:flex;align-items:center;gap:4px;margin-bottom:3px"><span style="width:6px;height:6px;border-radius:1px;background:${color}"></span><span style="font-size:11px">${name}</span></div><div style="font-size:10px;color:#94a3b8">${meta.confidence}% · ${meta.minutes}min · ${meta.count} logs</div></div>`;
      }},
    });
    state.heatmapChart.render();
  }

  // ============ POPOVER ============
  async function showPopover(event, meta) {
    const popover = document.getElementById('cellDetailPopover');
    const color = LABEL_COLORS[meta.label] || '#888';
    const name = STATUS_LABELS[meta.label] || meta.label;
    // Summary area (for ApexCharts or legacy single-segment popovers)
    document.getElementById('popoverSummary').innerHTML = `<div class="flex items-center gap-2">
      <span class="text-xs text-on-surface-variant">${meta.camera || ''}</span>
      <span class="text-[10px] px-1.5 py-0.5 rounded-full" style="background:${color}33;color:${color}">${name}</span>
      <span class="text-xs text-on-surface-variant">${meta.time || ''}</span>
    </div>`;

    // List-based drilldown for daily grid cells
    const segmentsContainer = document.getElementById('popoverSegments');
    segmentsContainer.innerHTML = '<div class="text-xs text-on-surface-variant text-center py-4">Loading segments...</div>';

    if (meta.segments && meta.segments.length > 0) {
      await enrichSegments(segmentsContainer, meta.segments);
    } else {
      segmentsContainer.innerHTML = '<div class="text-xs text-on-surface-variant text-center py-4">No segments to show</div>';
    }

    const rect = event.target.getBoundingClientRect();
    popover.style.left = Math.min(rect.left, window.innerWidth - 340) + 'px';
    popover.style.top = (rect.bottom + 6) + 'px';
    popover.classList.remove('hidden');
  }

  function hidePopover() {
    document.getElementById('cellDetailPopover').classList.add('hidden');
  }

  // Enrich segment list with API details and render compact rows
  async function enrichSegments(container, segments) {
    // Enrich each segment from /api/history/segments/{id}
    const enriched = await Promise.all(segments.map(async (seg) => {
      const segId = seg.segment_id || seg.id || '';
      if (!segId) return { ...seg, model_used: '', evidence: null, job_id: seg.job_id || '' };
      try {
        const [histResp, evResp] = await Promise.all([
          fetch(`/api/history/segments/${segId}`).catch(() => ({ ok: false })),
          fetch(`/api/evidence/${segId}`).catch(() => ({ ok: false })),
        ]);
        const hist = histResp.ok ? await histResp.json() : {};
        const ev = evResp.ok ? await evResp.json() : null;
        return {
          ...seg,
          camera_name: hist.camera_name || seg.camera || '',
          start_ts: hist.start_ts || seg.start_ts || '',
          end_ts: hist.end_ts || seg.end_ts || '',
          model_used: hist.model_used || '',
          evidence: ev,
          job_id: hist.job_id || seg.job_id || '',
        };
      } catch (_) {
        return { ...seg, model_used: '', evidence: null, jobId: seg.job_id || '' };
      }
    }));

    renderSegmentRows(container, enriched);
  }

  function renderSegmentRows(container, segments) {
    if (segments.length === 0) {
      container.innerHTML = '<div class="text-xs text-on-surface-variant text-center py-4">No segments</div>';
      return;
    }

    container.innerHTML = segments.map((seg) => {
      const color = LABEL_COLORS[seg.label] || LABEL_COLORS.uncertain;
      const name = STATUS_LABELS[seg.label] || seg.label;
      const conf = Math.round((seg.confidence || 0) * 100);
      const startStr = seg.start_ts ? new Date(seg.start_ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '--:--';
      const endStr = seg.end_ts ? new Date(seg.end_ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '--:--';

      // Thumbnail: first frame or "No image" placeholder
      const frames = Array.isArray(seg.evidence?.evidence_frames) ? seg.evidence.evidence_frames.filter(Boolean) : [];
      const thumbHtml = frames.length > 0
        ? `<img src="/${frames[0]}" alt="Frame" class="w-8 h-8 rounded object-cover flex-shrink-0 border border-outline-variant/20" />`
        : `<span class="w-8 h-8 rounded flex-shrink-0 bg-surface-container-lowest flex items-center justify-center text-[9px] text-on-surface-variant border border-outline-variant/20">No image</span>`;

      const modelHtml = seg.model_used
        ? `<span class="text-[9px] text-on-surface-variant" title="Model: ${seg.model_used}">${seg.model_used.split('/').pop() || seg.model_used}</span>`
        : '';

      const jobBtnHtml = seg.job_id
        ? `<button type="button" class="text-[9px] text-primary hover:underline font-medium flex-shrink-0" data-job-id="${seg.job_id}">Open Job Details</button>`
        : '';

      return `<div class="flex items-center gap-1.5 p-1.5 rounded-lg bg-surface-container-lowest" data-segment-id="${seg.id || ''}">
        ${thumbHtml}
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-1">
            <span class="w-1.5 h-1.5 rounded-full flex-shrink-0" style="background:${color}"></span>
            <span class="text-[10px] font-medium text-on-surface truncate">${seg.camera_name || ''} · ${name}</span>
          </div>
          <div class="flex items-center gap-1 text-[9px] text-on-surface-variant">
            <span>${conf}%</span>
            <span>${startStr}-${endStr}</span>
            ${modelHtml}
          </div>
        </div>
        ${jobBtnHtml}
      </div>`;
    }).join('');
  }

  function hideSegmentModal() {
    document.getElementById('segmentModal').classList.add('hidden');
  }

  async function showSegmentModal(segmentId) {
    const modal = document.getElementById('segmentModal');
    const body = document.getElementById('modalBody');
    const title = document.getElementById('modalTitle');
    hidePopover();
    body.innerHTML = '<div class="text-center py-8 text-on-surface-variant text-sm">Loading...</div>';
    modal.classList.remove('hidden');

    try {
      const resp = await fetch(`/api/history/segments/${segmentId}`);
      if (!resp.ok) {
        body.innerHTML = '<div class="text-center py-8 text-error text-sm">Segment not found</div>';
        return;
      }
      const seg = await resp.json();
      const color = LABEL_COLORS[seg.label] || LABEL_COLORS.uncertain;
      const name = STATUS_LABELS[seg.label] || seg.label || 'Unknown';
      const conf = Math.round((seg.confidence || 0) * 100);
      const startTime = seg.start_ts ? new Date(seg.start_ts).toLocaleString() : '-';
      const endTime = seg.end_ts ? new Date(seg.end_ts).toLocaleString() : '-';
      const durMin = seg.duration_minutes || (seg.start_ts && seg.end_ts ? Math.round((new Date(seg.end_ts) - new Date(seg.start_ts)) / 60000) : 0);
      const reviewed = seg.reviewed_label ? STATUS_LABELS[seg.reviewed_label] || seg.reviewed_label : null;

      title.textContent = `Segment #${seg.id || segmentId} — ${seg.camera_name || 'Camera'}`;

      let evidenceHtml = '<span class="text-on-surface-variant italic text-xs">No evidence image</span>';
      try {
        const evResp = await fetch(`/api/evidence/${segmentId}`);
        if (evResp.ok) {
          const evData = await evResp.json();
          const fps = Array.isArray(evData.evidence_frames) ? evData.evidence_frames.filter(Boolean) : [];
          if (fps.length > 0) {
            evidenceHtml = `<div class="grid grid-cols-2 gap-2">${fps.map(fp => `<img src="/${fp}" alt="Frame" class="w-full rounded-lg border border-outline-variant/20 cursor-pointer hover:opacity-90 transition-opacity" onclick="window.open('/${fp}','_blank')" />`).join('')}</div>`;
          } else if (evData.evidence_path) {
            evidenceHtml = `<img src="/${evData.evidence_path}" alt="Evidence" class="w-full rounded-lg border border-outline-variant/20 cursor-pointer hover:opacity-90 transition-opacity" onclick="window.open('/${evData.evidence_path}','_blank')" />`;
          }
        }
      } catch (_) {}

      body.innerHTML = `

        <div class="space-y-3">
          <div class="flex items-center gap-3 p-3 rounded-xl bg-surface-container-lowest">
            <span class="w-4 h-4 rounded-full flex-shrink-0" style="background:${color}"></span>
            <div class="flex-1">
              <div class="text-sm font-bold text-on-surface capitalize">${name}</div>
              <div class="text-xs text-on-surface-variant">${conf}% confidence${reviewed ? ` · Reviewed as: ${reviewed}` : ''}</div>
            </div>
            <span class="text-xs font-medium px-2 py-1 rounded-full" style="background:${color}22;color:${color}">${name}</span>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div class="p-3 rounded-xl bg-surface-container-lowest">
              <div class="text-[10px] uppercase tracking-wider text-on-surface-variant mb-1">Start</div>
              <div class="text-xs font-medium text-on-surface">${startTime}</div>
            </div>
            <div class="p-3 rounded-xl bg-surface-container-lowest">
              <div class="text-[10px] uppercase tracking-wider text-on-surface-variant mb-1">End</div>
              <div class="text-xs font-medium text-on-surface">${endTime}</div>
            </div>
          </div>
          <div class="p-3 rounded-xl bg-surface-container-lowest">
            <div class="text-[10px] uppercase tracking-wider text-on-surface-variant mb-1">Duration</div>
            <div class="text-sm font-bold text-on-surface">${durMin} minutes</div>
          </div>
          ${seg.notes ? `<div class="p-3 rounded-xl bg-surface-container-lowest">
            <div class="text-[10px] uppercase tracking-wider text-on-surface-variant mb-1">Notes</div>
            <div class="text-xs text-on-surface">${seg.notes}</div>
          </div>` : ''}
          <div class="space-y-2">
            <div class="text-[10px] uppercase tracking-wider text-on-surface-variant">Visual Evidence</div>
            ${evidenceHtml}
          </div>
        </div>`;
    } catch (e) {
      body.innerHTML = `<div class="text-center py-8 text-error text-sm">Error: ${e.message}</div>`;
    }
  }

  function updateSubtitle() {
    const d = state.currentDate;
    let s = '';
    if (state.currentView === 'daily') s = d.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
    else if (state.currentView === 'weekly') {
      const start = getStartOfWeek(d);
      s = `${start.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${addDays(start, 6).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`;
    } else s = d.toLocaleDateString('en-US', { year: 'numeric', month: 'long' });
    document.getElementById('heatmapSubtitle').textContent = s;
  }

  function exportToCSV() {
    // placeholder
  }

  function formatDate(date) { return date.toISOString().split('T')[0]; }
  function formatMinutesToHM(m) { return `${Math.floor(m/60)}:${String(Math.floor(m%60)).padStart(2,'0')}`; }
  function addDays(d, n) { const r = new Date(d); r.setDate(r.getDate() + n); return r; }
  function getStartOfWeek(d) { const r = new Date(d); const day = r.getDay(); r.setDate(r.getDate() - day + (day === 0 ? -6 : 1)); return r; }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
