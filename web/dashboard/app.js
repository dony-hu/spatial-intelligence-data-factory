const STORAGE_KEY = 'governance_manual_decisions_v1';

const el = {
  meta: document.getElementById('meta'),
  refresh: document.getElementById('refresh'),
  interval: document.getElementById('interval'),
  heroHealth: document.getElementById('heroHealth'),
  kpis: document.getElementById('kpis'),
  reviewQueue: document.getElementById('reviewQueue'),
  decisionFeed: document.getElementById('decisionFeed'),
  onlyPending: document.getElementById('onlyPending'),
  exportDecisions: document.getElementById('exportDecisions'),
};

let timer = null;
let intervalSec = 30;
let currentItems = [];

const ACTION_OPTIONS = [
  { value: 'approve', label: '确认通过' },
  { value: 'reject', label: '驳回并回流' },
  { value: 'need_evidence', label: '要求补证据' },
];

const ROUTE_OPTIONS = [
  { value: 'downstream', label: '进入下游发布' },
  { value: 'rule_fix', label: '回流规则修订' },
  { value: 'manual_replay', label: '回放复核后再决策' },
  { value: 'on_hold', label: '挂起等待条件满足' },
];

const fmt = (t) => {
  if (!t || t === '-') return '-';
  const d = new Date(t);
  return Number.isNaN(d.getTime()) ? t : d.toLocaleString();
};

const val = (v) => (v === undefined || v === null || v === '' ? '-' : v);

function esc(s) {
  return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function readDecisions() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch (error) {
    return {};
  }
}

function writeDecisions(map) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(map));
}

async function readManifest() {
  const res = await fetch('/data/dashboard_manifest.json', { cache: 'no-store' });
  if (!res.ok) throw new Error('manifest load failed');
  return res.json();
}

async function readJson(file) {
  const res = await fetch(`/data/${file}`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`load failed: ${file}`);
  return res.json();
}

function riskScore(item) {
  if (item.risk === 'high') return 3;
  if (item.risk === 'medium') return 2;
  return 1;
}

function riskLabel(risk) {
  if (risk === 'high') return '<span class="risk risk-high">高</span>';
  if (risk === 'medium') return '<span class="risk risk-medium">中</span>';
  return '<span class="risk risk-low">低</span>';
}

function buildReviewQueue(project, workpackages, tests) {
  const items = [];
  const packages = Array.isArray(workpackages?.packages) ? workpackages.packages : [];
  const regressions = Array.isArray(tests?.regressions) ? tests.regressions : [];

  const releaseDecision = String(project?.release_decision || '').toUpperCase();
  if (releaseDecision === 'HOLD' || releaseDecision === 'NO_GO') {
    items.push({
      id: 'project_release_gate',
      stage: '项目发布门禁',
      summary: `项目发布决策为 ${releaseDecision}，需人工确认是否调整到下一阶段。`,
      risk: releaseDecision === 'NO_GO' ? 'high' : 'medium',
      evidenceRef: '/data/project_overview.json',
      gate: releaseDecision,
      updatedAt: project?.as_of || '',
      source: 'project',
    });
  }

  for (const row of packages) {
    const release = String(row?.release_decision || '').toUpperCase();
    const status = String(row?.status || '').toLowerCase();
    const needsManual = release === 'HOLD' || release === 'NO_GO' || status.includes('block') || status.includes('fail');
    if (!needsManual) continue;

    const stage = status === 'done' ? '阶段成果验收' : '执行前/执行中确认';
    const risk = release === 'NO_GO' ? 'high' : (status.includes('fail') ? 'high' : 'medium');
    const summary = `${val(row?.title)}（状态 ${val(row?.status)}，进度 ${val(row?.progress)}%）`;

    items.push({
      id: String(row?.workpackage_id || 'unknown_package'),
      stage,
      summary,
      risk,
      evidenceRef: String(row?.test_report_ref || '/data/workpackages_live.json'),
      gate: release || '-',
      updatedAt: row?.updated_at || '',
      source: 'workpackage',
    });
  }

  for (const row of regressions) {
    const status = String(row?.current_status || '').toLowerCase();
    if (status !== 'open') continue;
    const suite = String(row?.suite_id || 'unknown_suite');
    const caseId = String(row?.case_id || 'unknown_case');

    items.push({
      id: `${suite}:${caseId}`,
      stage: '测试回归处置',
      summary: `回归未关闭（suite=${suite}, case=${caseId}），需确认是否阻断流转。`,
      risk: 'high',
      evidenceRef: '/data/test_status_board.json',
      gate: 'REGRESSION_OPEN',
      updatedAt: row?.first_failed_at || tests?.as_of || '',
      source: 'regression',
    });
  }

  items.sort((a, b) => {
    const riskDiff = riskScore(b) - riskScore(a);
    if (riskDiff !== 0) return riskDiff;
    return String(b.updatedAt || '').localeCompare(String(a.updatedAt || ''));
  });

  return items;
}

function computeKpis(items, decisions) {
  const pending = items.filter((item) => !decisions[item.id]).length;
  const decided = items.length - pending;
  const highRisk = items.filter((item) => item.risk === 'high').length;
  const blocked = items.filter((item) => String(item.gate).toUpperCase() === 'NO_GO' || String(item.gate).toUpperCase() === 'REGRESSION_OPEN').length;

  let pressure = 100;
  pressure -= highRisk * 18;
  pressure -= pending * 5;
  pressure -= blocked * 8;
  pressure = Math.max(0, Math.min(100, pressure));

  const pressureLabel = pressure >= 80 ? '可控' : (pressure >= 60 ? '偏高' : '高压');

  return {
    pending,
    decided,
    highRisk,
    blocked,
    pressure,
    pressureLabel,
  };
}

function renderKpis(kpi) {
  const cards = [
    ['待人工确认', String(kpi.pending), '需做下一步流转决策'],
    ['已完成人工决策', String(kpi.decided), '本地已留痕'],
    ['高风险事项', String(kpi.highRisk), 'NO_GO/回归未关闭优先'],
    ['阻断流转项', String(kpi.blocked), '当前不能直接下游'],
  ];

  if (el.kpis) {
    el.kpis.innerHTML = cards
      .map(([label, value, note]) => `<article class="kpi-card"><div class="kpi-label">${label}</div><div class="kpi-value">${value}</div><div class="kpi-note">${note}</div></article>`)
      .join('');
  }

  if (el.heroHealth) {
    const cls = kpi.pressure >= 80 ? 'health-good' : (kpi.pressure >= 60 ? 'health-warn' : 'health-bad');
    el.heroHealth.className = `health-badge ${cls}`;
    el.heroHealth.textContent = `决策压力：${kpi.pressureLabel} (${kpi.pressure})`;
  }
}

function decisionEditor(rowId, decisions) {
  const existing = decisions[rowId] || {};
  const actionOptions = ACTION_OPTIONS
    .map((item) => `<option value="${item.value}" ${item.value === existing.action ? 'selected' : ''}>${item.label}</option>`)
    .join('');
  const routeOptions = ROUTE_OPTIONS
    .map((item) => `<option value="${item.value}" ${item.value === existing.route ? 'selected' : ''}>${item.label}</option>`)
    .join('');

  return `
    <select class="decision-action" data-id="${esc(rowId)}">
      <option value="">请选择</option>
      ${actionOptions}
    </select>
    <select class="decision-route" data-id="${esc(rowId)}">
      <option value="">请选择</option>
      ${routeOptions}
    </select>
    <input class="decision-note" data-id="${esc(rowId)}" type="text" placeholder="补充说明（选填）" value="${esc(existing.note || '')}" />
    <button type="button" class="save-decision" data-id="${esc(rowId)}">保存</button>
  `;
}

function renderQueue(items, decisions) {
  const onlyPending = Boolean(el.onlyPending?.checked);
  const rows = onlyPending ? items.filter((item) => !decisions[item.id]) : items;

  if (!rows.length) {
    el.reviewQueue.innerHTML = '<tr><td colspan="10" class="empty">当前无待展示事项</td></tr>';
    return;
  }

  el.reviewQueue.innerHTML = rows
    .map((item) => {
      const decision = decisions[item.id];
      const decisionCell = decision
        ? `<div class="saved-tag">已决策</div><div class="saved-note">${esc(decision.action)} / ${esc(decision.route)}<br>${esc(decision.note || '-')}</div>`
        : decisionEditor(item.id, decisions);

      const evidenceHref = item.evidenceRef.startsWith('/data/') || item.evidenceRef.startsWith('/artifacts/')
        ? item.evidenceRef
        : `/artifacts/${item.evidenceRef}`;

      return `
        <tr>
          <td><strong>${esc(item.id)}</strong><br><small>${esc(item.source)}</small></td>
          <td>${esc(item.stage)}</td>
          <td>${esc(item.summary)}</td>
          <td>${riskLabel(item.risk)}</td>
          <td><a href="${esc(evidenceHref)}" target="_blank" rel="noopener noreferrer">查看</a></td>
          <td>${esc(item.gate)}</td>
          <td colspan="4">${decisionCell}</td>
        </tr>
      `;
    })
    .join('');
}

function renderDecisionFeed(decisions) {
  const entries = Object.entries(decisions)
    .map(([id, d]) => ({ id, ...(d || {}) }))
    .sort((a, b) => String(b.decidedAt || '').localeCompare(String(a.decidedAt || '')));

  if (!entries.length) {
    el.decisionFeed.innerHTML = '<div class="empty">暂无人工决策记录</div>';
    return;
  }

  el.decisionFeed.innerHTML = entries
    .map((item) => `
      <article class="decision-item">
        <h3>${esc(item.id)}</h3>
        <p><strong>动作：</strong>${esc(item.action || '-')}</p>
        <p><strong>流转：</strong>${esc(item.route || '-')}</p>
        <p><strong>备注：</strong>${esc(item.note || '-')}</p>
        <p class="muted">决策时间：${fmt(item.decidedAt)}</p>
      </article>
    `)
    .join('');
}

function saveDecision(id) {
  const actionEl = document.querySelector(`.decision-action[data-id="${id}"]`);
  const routeEl = document.querySelector(`.decision-route[data-id="${id}"]`);
  const noteEl = document.querySelector(`.decision-note[data-id="${id}"]`);
  const action = String(actionEl?.value || '');
  const route = String(routeEl?.value || '');
  const note = String(noteEl?.value || '').trim();

  if (!action || !route) {
    window.alert('请先选择决策动作和下一步流转。');
    return;
  }

  const decisions = readDecisions();
  decisions[id] = {
    action,
    route,
    note,
    decidedAt: new Date().toISOString(),
  };
  writeDecisions(decisions);
  rerenderFromLocal();
}

function rerenderFromLocal() {
  const decisions = readDecisions();
  const kpis = computeKpis(currentItems, decisions);
  renderKpis(kpis);
  renderQueue(currentItems, decisions);
  renderDecisionFeed(decisions);
}

async function refreshAll() {
  try {
    const manifest = await readManifest();
    const files = manifest.files || {};
    const [project, workpackages, tests] = await Promise.all([
      readJson(files.project_overview || 'project_overview.json').catch(() => ({})),
      readJson(files.workpackages_live || 'workpackages_live.json').catch(() => ({})),
      readJson(files.test_status_board || 'test_status_board.json').catch(() => ({})),
    ]);

    currentItems = buildReviewQueue(project, workpackages, tests);
    rerenderFromLocal();
    el.meta.textContent = `已更新: ${fmt(manifest.as_of)} | 自动刷新: ${intervalSec}s | 队列项: ${currentItems.length}`;
  } catch (error) {
    el.meta.textContent = `加载失败: ${error.message}`;
  }
}

function resetTimer() {
  if (timer) clearInterval(timer);
  timer = setInterval(refreshAll, intervalSec * 1000);
}

el.reviewQueue.addEventListener('click', (event) => {
  const btn = event.target.closest('.save-decision');
  if (!btn) return;
  saveDecision(btn.getAttribute('data-id') || '');
});

if (el.onlyPending) {
  el.onlyPending.addEventListener('change', rerenderFromLocal);
}

if (el.exportDecisions) {
  el.exportDecisions.addEventListener('click', () => {
    const decisions = readDecisions();
    const payload = {
      exported_at: new Date().toISOString(),
      total_items: Object.keys(decisions).length,
      decisions,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `governance-manual-decisions-${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });
}

el.refresh.addEventListener('click', refreshAll);
el.interval.addEventListener('change', () => {
  intervalSec = Number(el.interval.value || '30');
  resetTimer();
  refreshAll();
});

refreshAll();
resetTimer();
